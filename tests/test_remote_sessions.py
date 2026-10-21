from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from codeharbor.conversation import ConversationManager, Message
from codeharbor.memory.session import SessionManager
from codeharbor.remote import RemoteServer
from codeharbor.tools.ask_user import AskUserParams, AskUserTool, QuestionItem


def _server_with_state(tmp_path: Path) -> RemoteServer:
    provider = SimpleNamespace(
        name="deepseek",
        protocol="openai-compat",
        model="deepseek-chat",
        api_key="sk-must-not-leak",
    )
    config = SimpleNamespace(
        permission_mode="default",
        api_key="sk-config-secret",
        raw={"providers": [{"api_key": "sk-raw-secret"}]},
    )
    server = RemoteServer(
        [provider],
        mcp_servers=[SimpleNamespace(name="context7", env={"TOKEN": "secret"})],
        config=config,
    )
    server.session_manager = SessionManager(str(tmp_path))
    server.session = server.session_manager.create()
    server.session_id = server.session.session_id
    server.conversation = ConversationManager()
    server.agent = SimpleNamespace(session_id=server.session_id)
    return server


def _capture_broadcasts(server: RemoteServer) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    async def capture(message: dict[str, Any]) -> None:
        events.append(message)

    server._broadcast = capture  # type: ignore[method-assign]
    return events


@pytest.mark.asyncio
async def test_remote_ask_user_round_trip_returns_browser_answers(
    tmp_path: Path,
) -> None:
    server = _server_with_state(tmp_path)
    events = _capture_broadcasts(server)
    tool = AskUserTool(on_ask=server._handle_ask_user_event)
    params = AskUserParams(
        questions=[
            QuestionItem(
                type="radio",
                name="choice",
                message="选择 A 还是 B？",
                options=["A", "B"],
            )
        ]
    )

    result_task = asyncio.create_task(tool.execute(params))
    await asyncio.sleep(0)

    assert events[0]["type"] == "ask_user"
    assert events[0]["data"]["questions"] == [params.questions[0].model_dump()]
    ask_id = events[0]["data"]["id"]
    server._handle_ask_user_response(
        {"id": ask_id, "answers": {"choice": "A"}}
    )

    result = await result_task
    assert result.is_error is False
    assert result.output == "choice: A"


def test_connected_payload_is_useful_and_contains_no_secrets(tmp_path: Path) -> None:
    server = _server_with_state(tmp_path)

    payload = server._build_connected_payload()
    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["product"] == {
        "name": "CodeHarbor",
        "version": "0.2.0",
        "tagline": "Your code. Guided home.",
    }
    assert payload["provider"] == {
        "name": "deepseek",
        "protocol": "openai-compat",
        "model": "deepseek-chat",
    }
    assert payload["permissionMode"] == "default"
    assert payload["mcpServers"] == [{"name": "context7"}]
    assert payload["bind"] == {
        "host": "127.0.0.1",
        "port": 18888,
        "loopback": True,
    }
    assert payload["session"] == server.session_id
    assert "sk-" not in serialized
    assert "TOKEN" not in serialized


def test_session_list_is_latest_first_and_marks_active(tmp_path: Path) -> None:
    server = _server_with_state(tmp_path)
    assert server.session_manager is not None
    active = server.session
    assert active is not None
    active.append(Message(role="user", content="active question"))

    older = server.session_manager.create()
    older.append(Message(role="user", content="older question"))
    older.meta.last_active = datetime.now(timezone.utc) - timedelta(days=1)
    older.meta.total_tokens = 42
    older.meta.save(server.session_manager._sessions_dir / f"{older.session_id}.meta")
    older.close()

    items = server._build_session_list()

    assert [item["id"] for item in items] == [active.session_id, older.session_id]
    assert items[0]["active"] is True
    assert items[0]["messageCount"] == 1
    assert items[1]["active"] is False
    assert items[1]["tokenCount"] == 42
    assert items[0]["createdAt"]
    assert items[0]["lastActive"]


@pytest.mark.asyncio
async def test_new_session_closes_old_and_resets_conversation(tmp_path: Path) -> None:
    server = _server_with_state(tmp_path)
    events = _capture_broadcasts(server)
    old_session = server.session
    assert old_session is not None
    server.conversation.add_user_message("discard from active view")

    changed = await server._handle_session_new()

    assert changed is True
    assert old_session._file.closed
    assert server.session_id != old_session.session_id
    assert server.agent.session_id == server.session_id
    assert server.conversation.history == []
    assert [event["type"] for event in events] == [
        "clear",
        "session_active",
        "session_list",
    ]


@pytest.mark.asyncio
async def test_resume_session_replays_user_and_assistant_messages(tmp_path: Path) -> None:
    server = _server_with_state(tmp_path)
    assert server.session_manager is not None
    target = server.session_manager.create()
    target.append(Message(role="user", content="hello"))
    target.append(Message(role="assistant", content="welcome home"))
    target_id = target.session_id
    target.close()
    current = server.session
    assert current is not None
    events = _capture_broadcasts(server)

    changed = await server._handle_session_resume(target_id)

    assert changed is True
    assert current._file.closed
    assert server.session_id == target_id
    assert server.agent.session_id == target_id
    assert [message.content for message in server.conversation.history] == [
        "hello",
        "welcome home",
    ]
    assert [
        (event["type"], (event["data"] or {}).get("content"))
        for event in events[:3]
    ] == [
        ("clear", None),
        ("replay_user", "hello"),
        ("replay_assistant", "welcome home"),
    ]
    assert events[-2]["type"] == "session_active"
    assert events[-1]["type"] == "session_list"


@pytest.mark.asyncio
async def test_unknown_session_reports_error_without_closing_current(tmp_path: Path) -> None:
    server = _server_with_state(tmp_path)
    current = server.session
    assert current is not None
    events = _capture_broadcasts(server)

    changed = await server._handle_session_resume("session_missing")

    assert changed is False
    assert not current._file.closed
    assert events == [
        {
            "type": "error",
            "data": {"message": "Session not found: session_missing"},
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["new", "resume"])
async def test_session_switch_is_rejected_while_streaming(
    tmp_path: Path, action: str
) -> None:
    server = _server_with_state(tmp_path)
    server._streaming = True
    events = _capture_broadcasts(server)

    if action == "new":
        changed = await server._handle_session_new()
    else:
        changed = await server._handle_session_resume("anything")

    assert changed is False
    assert events == [
        {
            "type": "error",
            "data": {"message": "Cannot switch sessions while a response is streaming"},
        }
    ]


@pytest.mark.asyncio
async def test_web_conversation_is_persisted_for_later_resume(tmp_path: Path) -> None:
    server = _server_with_state(tmp_path)
    session_id = server.session_id
    events = _capture_broadcasts(server)

    class FakeAgent:
        def __init__(self) -> None:
            self.session_id = session_id

        async def run(self, conversation: ConversationManager):
            conversation.inject_environment(
                "Current working directory: C:/project\n"
                "Operating system: Windows\n"
                "Current time: 2026-10-20 12:00:00"
            )
            conversation.add_system_reminder("internal instructions must stay hidden")
            conversation.add_assistant_message("persisted reply")
            if False:
                yield None

    server.agent = FakeAgent()

    await server._handle_user_message("persisted question")
    assert server.session is not None
    server.session.close()
    assert server.session_manager is not None
    resumed = server.session_manager.resume(session_id)

    assert resumed is not None
    assert [message.content for message in resumed.messages] == [
        "persisted question",
        "persisted reply",
    ]
    assert events[-1]["type"] == "session_list"
    assert events[-1]["data"][0]["title"] == "persisted question"
    resumed.session.close()


@pytest.mark.asyncio
async def test_reconnect_replays_visible_messages_without_internal_reminders(
    tmp_path: Path,
) -> None:
    server = _server_with_state(tmp_path)
    assert server.conversation is not None
    server.conversation.add_user_message("visible question")
    server.conversation.add_system_reminder("hidden instructions")
    server.conversation.add_assistant_message("visible answer")
    events = _capture_broadcasts(server)

    await server._replay_active_conversation()

    assert events == [
        {"type": "clear", "data": None},
        {"type": "replay_user", "data": {"content": "visible question"}},
        {"type": "replay_assistant", "data": {"content": "visible answer"}},
    ]


@pytest.mark.asyncio
async def test_reconnect_skips_tool_only_messages_with_empty_content(
    tmp_path: Path,
) -> None:
    server = _server_with_state(tmp_path)
    assert server.conversation is not None
    server.conversation.history.extend(
        [
            Message(role="assistant", content=""),
            Message(role="user", content=""),
            Message(role="assistant", content="answer after tool"),
        ]
    )
    events = _capture_broadcasts(server)

    await server._replay_active_conversation()

    assert events == [
        {"type": "clear", "data": None},
        {
            "type": "replay_assistant",
            "data": {"content": "answer after tool"},
        },
    ]


@pytest.mark.asyncio
async def test_cancel_interrupts_active_response_before_first_stream_event(
    tmp_path: Path,
) -> None:
    server = _server_with_state(tmp_path)
    server._cancel_event = asyncio.Event()
    server._active_task = asyncio.create_task(asyncio.sleep(60))

    cancelled = server._cancel_active_response()
    await asyncio.sleep(0)

    assert cancelled is True
    assert server._cancel_event.is_set()
    assert server._active_task.cancelled()
