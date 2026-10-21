(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const ui = {
    connectionPill: byId("connection-pill"),
    connectionStatus: byId("connection-status"),
    sessionList: byId("session-list"),
    activeSessionTitle: byId("active-session-title"),
    tokenCount: byId("token-count"),
    stream: byId("message-stream"),
    empty: byId("empty-state"),
    input: byId("message-input"),
    send: byId("send-message"),
    stop: byId("stop-response"),
    composerStatus: byId("composer-status"),
    newSession: byId("new-session"),
    sessionsPanel: byId("sessions-panel"),
    statusPanel: byId("status-panel"),
    toggleSessions: byId("toggle-sessions"),
    toggleStatus: byId("toggle-status"),
    scrim: byId("panel-scrim"),
    provider: byId("provider-name"),
    model: byId("model-name"),
    protocol: byId("protocol-name"),
    permission: byId("permission-mode"),
    mcpList: byId("mcp-list"),
    mcpCount: byId("mcp-count"),
    workspace: byId("workspace-path"),
  };

  const state = {
    socket: null,
    reconnectAttempt: 0,
    reconnectTimer: null,
    pingTimer: null,
    streaming: false,
    streamNode: null,
    streamText: "",
    thinkingNode: null,
    autoScroll: true,
    sessions: [],
    activeSession: "",
    connectedOnce: false,
  };

  function renderMarkdownSafe(text) {
    const ALLOWED_URI_REGEXP = /^(?:(?:https?|mailto):|[/.#])/i;
    const rawHtml = marked.parse(String(text ?? ""));
    return DOMPurify.sanitize(rawHtml, { ALLOWED_URI_REGEXP });
  }

  function hardenLinks(root) {
    root.querySelectorAll("a").forEach((link) => {
      const href = link.getAttribute("href") || "";
      if (!/^(?:https?:|mailto:|[/.#])/i.test(href)) {
        link.removeAttribute("href");
        return;
      }
      if (/^https?:/i.test(href)) {
        link.target = "_blank";
        link.rel = "noopener noreferrer";
      }
    });
  }

  function setConnectionState(connectionState) {
    const labels = {
      connecting: "正在连接",
      connected: "已连接",
      reconnecting: "正在重连",
      disconnected: "已断开",
    };
    ui.connectionPill.dataset.state = connectionState;
    ui.connectionStatus.textContent = labels[connectionState] || connectionState;
    ui.send.disabled = connectionState !== "connected";
  }

  function formatRelativeTime(value) {
    const time = new Date(value).getTime();
    if (!Number.isFinite(time)) return "刚刚";
    const seconds = Math.max(0, Math.floor((Date.now() - time) / 1000));
    if (seconds < 60) return "刚刚";
    if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`;
    return `${Math.floor(seconds / 86400)} 天前`;
  }

  function renderSessionList(items) {
    state.sessions = Array.isArray(items) ? items : [];
    ui.sessionList.replaceChildren();
    if (!state.sessions.length) {
      const placeholder = document.createElement("p");
      placeholder.className = "panel-placeholder";
      placeholder.textContent = "还没有历史会话";
      ui.sessionList.append(placeholder);
      return;
    }
    state.sessions.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `session-item${item.active ? " active" : ""}`;
      button.dataset.sessionId = item.id;
      button.setAttribute("role", "listitem");
      button.setAttribute("aria-label", `恢复会话：${item.title || "未命名会话"}`);
      const title = document.createElement("strong");
      title.textContent = item.title || "未命名会话";
      const meta = document.createElement("span");
      meta.textContent = `${item.messageCount || 0} 条消息 · ${formatRelativeTime(item.lastActive)}`;
      button.append(title, meta);
      button.addEventListener("click", () => {
        send("session_resume", { id: item.id });
        closePanels();
      });
      ui.sessionList.append(button);
      if (item.active) {
        state.activeSession = item.id;
        ui.activeSessionTitle.textContent = item.title || "新会话";
        ui.tokenCount.textContent = Number(item.tokenCount || 0).toLocaleString();
      }
    });
  }

  function updateResponsivePanels() {
    const mobile = window.matchMedia("(max-width: 720px)").matches;
    const compact = window.matchMedia("(max-width: 1100px)").matches;
    if (!mobile) {
      ui.sessionsPanel.classList.remove("open");
      ui.toggleSessions.setAttribute("aria-expanded", "false");
    }
    if (!compact) {
      ui.statusPanel.classList.remove("open");
      ui.toggleStatus.setAttribute("aria-expanded", "false");
    }
    const anyOpen = ui.sessionsPanel.classList.contains("open") || ui.statusPanel.classList.contains("open");
    ui.scrim.hidden = !anyOpen;
  }

  function togglePanel(panel, button) {
    const willOpen = !panel.classList.contains("open");
    closePanels();
    panel.classList.toggle("open", willOpen);
    button.setAttribute("aria-expanded", String(willOpen));
    ui.scrim.hidden = !willOpen;
  }

  function closePanels() {
    ui.sessionsPanel.classList.remove("open");
    ui.statusPanel.classList.remove("open");
    ui.toggleSessions.setAttribute("aria-expanded", "false");
    ui.toggleStatus.setAttribute("aria-expanded", "false");
    ui.scrim.hidden = true;
  }

  function maybeScrollToBottom() {
    if (state.autoScroll) ui.stream.scrollTop = ui.stream.scrollHeight;
  }

  function hideEmptyState() {
    if (ui.empty) ui.empty.hidden = true;
  }

  function clearConversation() {
    [...ui.stream.children].forEach((child) => {
      if (child !== ui.empty) child.remove();
    });
    ui.empty.hidden = false;
    state.streamNode = null;
    state.streamText = "";
    state.thinkingNode = null;
  }

  function addMessage(role, content, markdown = false) {
    hideEmptyState();
    const article = document.createElement("article");
    article.className = `message ${role}`;
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = role === "user" ? "YOU" : "CH";
    const contentWrap = document.createElement("div");
    const meta = document.createElement("div");
    meta.className = "message-meta";
    meta.textContent = role === "user" ? "你" : "CodeHarbor";
    const body = document.createElement("div");
    body.className = "message-body";
    if (markdown) {
      body.innerHTML = renderMarkdownSafe(content);
      hardenLinks(body);
    } else {
      body.textContent = String(content ?? "");
    }
    contentWrap.append(meta, body);
    article.append(avatar, contentWrap);
    ui.stream.append(article);
    maybeScrollToBottom();
    return body;
  }

  function addEventCard(kind, title, content) {
    hideEmptyState();
    const card = document.createElement("section");
    card.className = `event-card ${kind || ""}`.trim();
    const heading = document.createElement("strong");
    heading.textContent = title;
    card.append(heading);
    if (content !== undefined && content !== "") {
      const pre = document.createElement("pre");
      pre.textContent = typeof content === "string" ? content : JSON.stringify(content, null, 2);
      card.append(pre);
    }
    ui.stream.append(card);
    maybeScrollToBottom();
    return card;
  }

  function setStreaming(value) {
    state.streaming = value;
    ui.stop.hidden = !value;
    ui.send.hidden = value;
    ui.input.disabled = value;
    ui.composerStatus.textContent = value ? "CodeHarbor 正在航行…" : "";
    if (!value) {
      state.streamNode = null;
      state.streamText = "";
      state.thinkingNode = null;
      ui.input.focus();
    }
  }

  function updateMetadata(data) {
    const provider = data.provider || {};
    ui.provider.textContent = provider.name || "—";
    ui.model.textContent = provider.model || "—";
    ui.protocol.textContent = provider.protocol || "—";
    ui.permission.textContent = data.permissionMode || "—";
    ui.workspace.textContent = data.cwd || "—";
    state.activeSession = data.session || "";
    const servers = Array.isArray(data.mcpServers) ? data.mcpServers : [];
    ui.mcpCount.textContent = String(servers.length);
    ui.mcpList.replaceChildren();
    if (!servers.length) {
      const empty = document.createElement("li");
      empty.className = "muted";
      empty.textContent = "未配置";
      ui.mcpList.append(empty);
    } else {
      servers.forEach((server) => {
        const item = document.createElement("li");
        item.textContent = server.name || "Unnamed MCP";
        ui.mcpList.append(item);
      });
    }
  }

  function showPermission(data) {
    const card = addEventCard("permission", `权限请求 · ${data.toolName || "Tool"}`, data.description || "");
    const actions = document.createElement("div");
    actions.className = "permission-actions";
    const deny = document.createElement("button");
    deny.type = "button";
    deny.textContent = "拒绝";
    const allow = document.createElement("button");
    allow.type = "button";
    allow.className = "allow";
    allow.textContent = "允许";
    deny.addEventListener("click", () => {
      send("permission_response", { id: data.id, allowed: false });
      card.remove();
    });
    allow.addEventListener("click", () => {
      send("permission_response", { id: data.id, allowed: true });
      card.remove();
    });
    actions.append(deny, allow);
    card.append(actions);
  }

  function handleEvent(message) {
    const data = message.data || {};
    switch (message.type) {
      case "connected":
        updateMetadata(data);
        break;
      case "commands":
        break;
      case "session_list":
        renderSessionList(data);
        break;
      case "session_active":
        state.activeSession = data.id || "";
        break;
      case "clear":
        clearConversation();
        break;
      case "replay_user":
        addMessage("user", data.content, false);
        break;
      case "replay_assistant":
        addMessage("assistant", data.content, true);
        break;
      case "stream_text":
        setStreaming(true);
        state.streamText += data.text || "";
        if (!state.streamNode) state.streamNode = addMessage("assistant", "", false);
        state.streamNode.textContent = state.streamText;
        maybeScrollToBottom();
        break;
      case "stream_end":
        state.streamText = data.text || state.streamText;
        if (!state.streamNode) state.streamNode = addMessage("assistant", "", true);
        state.streamNode.innerHTML = renderMarkdownSafe(state.streamText);
        hardenLinks(state.streamNode);
        break;
      case "thinking_text":
        if (!state.thinkingNode) state.thinkingNode = addEventCard("thinking", "思考中", "").appendChild(document.createElement("pre"));
        state.thinkingNode.textContent += data.text || "";
        maybeScrollToBottom();
        break;
      case "tool_use":
        addEventCard("tool", `运行工具 · ${data.toolName || "Tool"}`, data.args || {});
        break;
      case "tool_result":
        addEventCard(data.isError ? "error" : "tool", `${data.toolName || "Tool"} · ${data.isError ? "失败" : "完成"}`, data.output || "");
        break;
      case "permission_request":
        showPermission(data);
        break;
      case "ask_user":
        addEventCard("permission", "需要你的选择", data.question || data.message || "");
        break;
      case "usage":
        ui.tokenCount.textContent = Number((data.inputTokens || 0) + (data.outputTokens || 0)).toLocaleString();
        break;
      case "turn_complete":
        state.thinkingNode = null;
        break;
      case "loop_complete":
      case "command_done":
        setStreaming(false);
        break;
      case "error":
        addEventCard("error", "出现错误", data.message || "未知错误");
        setStreaming(false);
        break;
      case "compact":
      case "retry":
      case "system":
        addEventCard("system", message.type === "retry" ? "正在重试" : "系统", data.message || data.reason || "");
        break;
      case "pong":
        break;
      default:
        break;
    }
  }

  function send(type, data = null) {
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) return false;
    state.socket.send(JSON.stringify({ type, data }));
    return true;
  }

  function connect() {
    clearTimeout(state.reconnectTimer);
    setConnectionState(state.connectedOnce ? "reconnecting" : "connecting");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);
    state.socket = socket;

    socket.addEventListener("open", () => {
      if (socket !== state.socket) return;
      state.connectedOnce = true;
      state.reconnectAttempt = 0;
      setConnectionState("connected");
      clearInterval(state.pingTimer);
      state.pingTimer = setInterval(() => send("ping"), 25000);
    });
    socket.addEventListener("message", (event) => {
      try {
        handleEvent(JSON.parse(event.data));
      } catch (error) {
        console.warn("Ignored malformed CodeHarbor event", error);
      }
    });
    socket.addEventListener("close", () => {
      if (socket !== state.socket) return;
      clearInterval(state.pingTimer);
      setConnectionState("disconnected");
      setStreaming(false);
      const delay = Math.min(10000, 500 * (2 ** state.reconnectAttempt));
      state.reconnectAttempt += 1;
      state.reconnectTimer = setTimeout(connect, delay);
    });
    socket.addEventListener("error", () => socket.close());
  }

  function submitMessage() {
    const content = ui.input.value.trim();
    if (!content || state.streaming) return;
    if (!send("user_message", { content })) {
      ui.composerStatus.textContent = "连接尚未恢复，草稿已保留";
      return;
    }
    addMessage("user", content, false);
    ui.input.value = "";
    localStorage.removeItem("codeharbor.draft");
    resizeComposer();
    setStreaming(true);
  }

  function resizeComposer() {
    const visualLines = Math.ceil(ui.input.value.length / 78);
    const explicitLines = ui.input.value.split("\n").length;
    ui.input.rows = Math.max(1, Math.min(7, Math.max(visualLines, explicitLines)));
  }

  ui.send.addEventListener("click", submitMessage);
  ui.stop.addEventListener("click", () => send("cancel"));
  ui.newSession.addEventListener("click", () => {
    if (send("session_new")) closePanels();
  });
  ui.input.addEventListener("input", () => {
    localStorage.setItem("codeharbor.draft", ui.input.value);
    resizeComposer();
  });
  ui.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  });
  ui.stream.addEventListener("scroll", () => {
    const remaining = ui.stream.scrollHeight - ui.stream.scrollTop - ui.stream.clientHeight;
    state.autoScroll = remaining < 90;
  }, { passive: true });
  ui.toggleSessions.addEventListener("click", () => togglePanel(ui.sessionsPanel, ui.toggleSessions));
  ui.toggleStatus.addEventListener("click", () => togglePanel(ui.statusPanel, ui.toggleStatus));
  ui.scrim.addEventListener("click", closePanels);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePanels();
  });
  document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
      ui.input.value = button.dataset.prompt || "";
      localStorage.setItem("codeharbor.draft", ui.input.value);
      resizeComposer();
      ui.input.focus();
    });
  });
  window.addEventListener("resize", updateResponsivePanels);

  ui.input.value = localStorage.getItem("codeharbor.draft") || "";
  resizeComposer();
  updateResponsivePanels();
  setConnectionState("connecting");
  connect();

  window.CodeHarborUI = {
    renderMarkdownSafe,
    setConnectionState,
    renderSessionList,
    updateResponsivePanels,
    handleEvent,
  };
})();
