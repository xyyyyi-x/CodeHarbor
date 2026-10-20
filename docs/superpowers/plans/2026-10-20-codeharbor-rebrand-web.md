# CodeHarbor Rebrand and Web Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully migrate MewCode to CodeHarbor and ship a secure, responsive, pure-Python Web workspace without breaking the existing Agent, LLM, MCP, TUI, session, or WebSocket behaviors.

**Architecture:** Rename the Python distribution and import package to `codeharbor`, centralize brand/data-directory constants, and perform a non-destructive first-run copy from `.mewcode` to `.codeharbor`. Replace the embedded HTML string with package resources served by the existing `websockets` HTTP hook; keep the current WebSocket protocol and add optional metadata/session messages for the new three-column UI.

**Tech Stack:** Python 3.11+, uv, hatchling, Textual, websockets, vanilla HTML/CSS/JavaScript, Marked 18.1.1, DOMPurify 3.4.17, pytest, pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-10-20-codeharbor-rebrand-web-design.md`

## Global Constraints

- Product, CLI, distribution, import package, and new data directory are exactly `CodeHarbor`, `codeharbor`, `codeharbor`, `codeharbor`, and `.codeharbor`.
- Version remains `0.2.0`; tagline is exactly `Your code. Guided home.`
- Do not provide a `mewcode` CLI or Python import compatibility shim.
- Never delete or overwrite `.mewcode`; copy it only when the corresponding `.codeharbor` target does not exist.
- Preserve every existing source-attribution header; do not add or invent a project license.
- Keep Python 3.11+ and the current LLM/MCP/config schema; never print or commit a real API key.
- No React, Vite, Node build step, account system, cloud sync, firewall/proxy/Nginx changes, server deployment, or public listener.
- Default Web bind is `127.0.0.1:18888`; non-loopback binds must emit an unauthenticated-service warning.
- WebSocket legacy event names and core fields remain compatible.
- The final project path is `D:\开发学习\CodeHarbor`; rename it only after all code/tests/browser checks pass in the original path.

## Review Focus

- Existing `.codeharbor` beside `.mewcode`: migration must leave both untouched and load only the new directory; pin in Task 2.
- Partial copy or filesystem permission failure: remove only the incomplete temporary target and preserve `.mewcode`; pin in Task 2.
- Query strings and encoded traversal in static URLs: serve valid assets but reject `..`, encoded traversal, and unknown paths; pin in Task 4.
- WebSocket disconnect during a generated response: retain draft/state, reconnect without duplicate welcome messages, and permit a fresh turn; pin in Task 6 browser checks.
- Model/tool output containing scripts, event attributes, `javascript:` URLs, or hostile SVG: render useful text/Markdown without executing it; pin in Task 6 security fixtures and browser checks.

---

### Task 1: Rename the Distribution, Package, CLI, and Brand Surface

**Files:**
- Create: `tests/test_branding.py`
- Create: `codeharbor/branding.py`
- Rename: `mewcode/` → `codeharbor/`
- Modify: `pyproject.toml`
- Modify: `uv.lock` (through `uv lock`)
- Modify: all Python imports and test patch targets under `codeharbor/` and `tests/`

**Interfaces:**
- Produces: `PRODUCT_NAME`, `PRODUCT_PACKAGE`, `PRODUCT_CLI`, `PRODUCT_TAGLINE`, `PRODUCT_VERSION`, `DATA_DIR_NAME`, and `LEGACY_DATA_DIR_NAME` in `codeharbor.branding`.
- Produces: the sole console entry point `codeharbor = "codeharbor.__main__:main"`.

- [ ] **Step 1: Write failing brand and packaging tests**

Add assertions that `import codeharbor` succeeds, branding constants have the exact spec values, `pyproject.toml` exposes only the `codeharbor` script, and the build target is `codeharbor`.

- [ ] **Step 2: Run the focused tests and verify the pre-rename failure**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_branding.py -v`

Expected: FAIL because `codeharbor` and its branding module do not exist.

- [ ] **Step 3: Rename the package and mechanically update imports**

Use `git mv mewcode codeharbor`, replace import/patch/module references, create `codeharbor/branding.py`, update `pyproject.toml`, and run `uv lock`. Do not replace `.mewcode` path literals yet, except the legacy constant.

- [ ] **Step 4: Verify imports, package metadata, and test collection**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' sync`

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_branding.py --collect-only -q`

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run python -c "import codeharbor; import codeharbor.remote"`

Expected: all commands exit 0, and `git grep -n 'from mewcode\|import mewcode\|mewcode\.' -- '*.py'` returns no product-code matches.

- [ ] **Step 5: Commit the package migration**

```powershell
git add pyproject.toml uv.lock codeharbor tests
git commit -m "refactor: rename package to CodeHarbor"
```

### Task 2: Implement Safe `.mewcode` to `.codeharbor` Migration

**Files:**
- Create: `codeharbor/migration.py`
- Create: `tests/test_data_migration.py`
- Modify: `codeharbor/__main__.py`
- Modify: all tracked `.mewcode` runtime-path consumers under `codeharbor/`
- Modify: affected path assertions under `tests/`
- Modify: `.gitignore`
- Modify: `tests/test_agent.py`

**Interfaces:**
- Produces: `MigrationResult(source: Path, target: Path, status: Literal["copied", "target_exists", "source_missing"])`.
- Produces: `migrate_legacy_directory(source: Path, target: Path) -> MigrationResult`.
- Produces: `migrate_legacy_data_locations(cwd: Path, home: Path) -> list[MigrationResult]`.

- [ ] **Step 1: Write migration failure-first tests**

Cover source missing, successful recursive copy, existing target precedence, file metadata/content preservation, failure cleanup via mocked `shutil.copytree`, no source mutation, no secret-bearing content in logs, and independent home/project migration.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_data_migration.py -v`

Expected: FAIL because migration interfaces do not exist.

- [ ] **Step 3: Implement atomic non-destructive migration and change runtime paths**

Copy into a sibling temporary directory and atomically rename it to `.codeharbor`; on failure remove only that temporary directory. Invoke migration at the start of `main()` before logging/config loading. Replace runtime `.mewcode` paths with `DATA_DIR_NAME`, retaining `.mewcode` only in migration compatibility and explicit legacy tests.

- [ ] **Step 4: Fix the existing Windows `/tmp` test without changing intent**

Change `test_multi_step_autonomous` to use pytest `tmp_path`, and assert the same write/read/autonomous behavior.

- [ ] **Step 5: Verify migration and cross-platform path tests**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_data_migration.py tests/test_agent.py::test_multi_step_autonomous tests/test_memory.py tests/test_permissions.py tests/test_skills.py -q`

Expected: PASS.

- [ ] **Step 6: Commit migration behavior**

```powershell
git add .gitignore codeharbor tests
git commit -m "feat: migrate CodeHarbor data safely"
```

### Task 3: Add Testable Host/Port CLI Security

**Files:**
- Create: `tests/test_cli.py`
- Modify: `codeharbor/__main__.py`
- Modify: `codeharbor/remote.py`

**Interfaces:**
- Produces: `build_parser() -> argparse.ArgumentParser`.
- Produces: `parse_port(value: str) -> int`, accepting only 1–65535.
- Produces: `is_loopback_host(host: str) -> bool`, true for `localhost`, `127.0.0.0/8`, and `::1`.
- `RemoteServer(..., addr: str = "127.0.0.1", port: int = 18888)` receives parsed CLI values.

- [ ] **Step 1: Write CLI tests**

Assert `prog="codeharbor"`, default host/port, explicit overrides, invalid ports, loopback recognition, `--remote` construction, and exactly one warning for a non-loopback bind without including config data.

- [ ] **Step 2: Run tests and verify failure**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_cli.py -v`

Expected: FAIL on missing parser helpers/defaults.

- [ ] **Step 3: Implement parser helpers and secure defaults**

Pass `--host` and `--port` into `RemoteServer`; print the unauthenticated-service warning before starting any non-loopback listener.

- [ ] **Step 4: Verify CLI help and tests**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_cli.py -q`

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run codeharbor --help`

Expected: PASS; help contains `CodeHarbor`, `--host`, and `--port`.

- [ ] **Step 5: Commit CLI security**

```powershell
git add codeharbor/__main__.py codeharbor/remote.py tests/test_cli.py
git commit -m "feat: secure CodeHarbor remote binding"
```

### Task 4: Replace Embedded HTML with Packaged Static Resources

**Files:**
- Create: `codeharbor/web/__init__.py`
- Create: `codeharbor/web/index.html`
- Create: `codeharbor/web/styles.css`
- Create: `codeharbor/web/app.js`
- Create: `codeharbor/web/assets/codeharbor-beacon.svg`
- Create: `codeharbor/web/assets/favicon.svg`
- Create: `codeharbor/web_assets.py`
- Create: `tests/test_remote_web.py`
- Modify: `codeharbor/remote.py`
- Delete: `codeharbor/web_content.py`

**Interfaces:**
- Produces: `WebAsset(body: bytes, content_type: str, cache_control: str)`.
- Produces: `load_web_asset(request_path: str) -> WebAsset | None`.
- `RemoteServer._process_http_request()` serves `/`, `/assets/*`, and `/vendor/*`; only `/ws` continues WebSocket upgrade.

- [ ] **Step 1: Write static-resource tests**

Test `/`, CSS, JS, both SVGs, UTF-8 MIME types, query strings, missing files, `../`, percent-encoded traversal, backslashes, and that `/ws` returns `None` for upgrade.

- [ ] **Step 2: Run tests and verify failure**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_remote_web.py -v`

Expected: FAIL because package resources and loader do not exist.

- [ ] **Step 3: Implement the resource loader and minimal HTML shell**

Normalize with `urllib.parse.urlsplit`/`unquote`, allow only an explicit asset root, use `importlib.resources.files("codeharbor.web")`, and set `nosniff`, CSP, cache, and content-type headers. Do not implement final visuals in this task.

- [ ] **Step 4: Verify wheel inclusion and HTTP behavior**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' build`

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_remote_web.py -q`

Expected: PASS and the wheel contains `codeharbor/web/*`.

- [ ] **Step 5: Commit static architecture**

```powershell
git add codeharbor tests/test_remote_web.py
git commit -m "refactor: serve packaged CodeHarbor web assets"
```

### Task 5: Add Web Metadata and Real Session Controls

**Files:**
- Create: `tests/test_remote_sessions.py`
- Modify: `codeharbor/remote.py`
- Modify: `codeharbor/memory/session.py` only if a small serialization helper is needed

**Interfaces:**
- Produces: `RemoteServer._build_connected_payload() -> dict[str, Any]` with non-secret product/provider/model/permission/MCP/bind metadata.
- Produces: `RemoteServer._build_session_list() -> list[dict[str, Any]]` containing id, title, message count, token count, created time, last-active time, and active state.
- Accepts new client messages `session_new` and `session_resume`.
- Emits optional events `session_list`, `session_active`, `replay_user`, and `replay_assistant` while preserving legacy events.

- [ ] **Step 1: Write metadata/session tests**

Assert payload shape, API-key absence by recursive value scan, latest-first session order, new-session close/create/reset behavior, valid resume/replay, unknown-session error, and rejection while streaming.

- [ ] **Step 2: Run tests and verify failure**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_remote_sessions.py -v`

Expected: FAIL on missing metadata and session handlers.

- [ ] **Step 3: Implement optional metadata and session events**

Reuse `SessionManager.list/create/resume`; close the old file handle before switching, replace the active conversation with resumed messages, and update `agent.session_id`. Never serialize `api_key`, MCP env, headers, or raw config.

- [ ] **Step 4: Verify protocol compatibility**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_remote_sessions.py tests/test_remote_web.py tests/test_memory.py -q`

Expected: PASS.

- [ ] **Step 5: Commit remote workspace data**

```powershell
git add codeharbor/remote.py codeharbor/memory/session.py tests/test_remote_sessions.py
git commit -m "feat: expose safe CodeHarbor workspace state"
```

### Task 6: Build the Deep Ocean Browser Workspace and Safe Markdown Pipeline

**Files:**
- Modify: `codeharbor/web/index.html`
- Modify: `codeharbor/web/styles.css`
- Modify: `codeharbor/web/app.js`
- Create: `codeharbor/web/vendor/marked.umd.js` (Marked 18.1.1 official distribution)
- Create: `codeharbor/web/vendor/purify.min.js` (DOMPurify 3.4.17 official distribution)
- Create: `codeharbor/web/vendor/LICENSES.md`
- Create: `tests/test_web_frontend_contract.py`

**Interfaces:**
- Frontend consumes all legacy events plus `session_list` and `session_active`.
- Frontend sends legacy messages plus `session_new` and `session_resume`.
- Produces browser helpers `renderMarkdownSafe(text)`, `setConnectionState(state)`, `renderSessionList(items)`, and `updateResponsivePanels()` in `app.js`.

- [ ] **Step 1: Write frontend contract/security tests**

Assert there are no CDN URLs or inline event handlers; local vendor versions/licenses exist; CSP-compatible external scripts are used; `renderMarkdownSafe` calls Marked then DOMPurify; dangerous scheme/attribute fixtures are present; interactive controls have accessible names; and all required event names appear.

- [ ] **Step 2: Run tests and verify failure**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_web_frontend_contract.py -v`

Expected: FAIL against the minimal shell.

- [ ] **Step 3: Implement the confirmed Deep Ocean layout**

Build the Harbor Beacon top bar, real session sidebar, central chat, right status rail, tool/thinking/permission/AskUser blocks, composer/stop states, reconnect indicator, empty state, and responsive drawers using CSS variables and `prefers-reduced-motion`.

- [ ] **Step 4: Implement safe rendering and resilient connection state**

Sanitize every Markdown render with DOMPurify; use `textContent` for tool/system/error content; constrain external links; preserve unsent drafts across disconnect; use bounded exponential backoff; avoid duplicate welcome messages after reconnect; and pause auto-scroll after manual upward scrolling.

- [ ] **Step 5: Run automated frontend contract checks**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_web_frontend_contract.py tests/test_remote_web.py tests/test_remote_sessions.py -q`

Expected: PASS.

- [ ] **Step 6: Run browser security and responsive checks**

Start CodeHarbor on loopback, then use browser automation to inject Markdown containing `<script>`, `onerror`, `javascript:`, and hostile SVG through a controlled mocked event; verify no dialog/navigation/script execution and readable sanitized output. Check desktop, tablet, and phone widths; disconnect/reconnect during streaming; keyboard navigation; focus visibility; session new/resume; cancel; and console errors.

- [ ] **Step 7: Commit Web UI**

```powershell
git add codeharbor/web tests/test_web_frontend_contract.py
git commit -m "feat: build CodeHarbor Deep Ocean workspace"
```

### Task 7: Rebrand TUI, Prompts, Commands, and Documentation

**Files:**
- Modify: `codeharbor/app.py`
- Modify: `codeharbor/styles.tcss`
- Modify: product-facing strings under `codeharbor/agents/`, `codeharbor/commands/`, `codeharbor/prompts.py`, and related tests
- Rename: `MEWCODE.md` → `CODEHARBOR.md`
- Create: `README.md`
- Modify: `tests/test_agent.py`
- Modify: `tests/test_commands.py`
- Modify: `tests/test_hello_world.py`

**Interfaces:**
- TUI imports branding constants and displays CodeHarbor 0.2.0 with the simplified beacon symbol.
- README commands use only `codeharbor` and `.codeharbor`.

- [ ] **Step 1: Write failing product-copy assertions**

Assert TUI banner/title, CLI description, status output, system prompt, built-in general Agent text, and README use CodeHarbor; assert tracked product UI/docs contain no stale MewCode branding except explicit attribution/legacy migration/legal passages.

- [ ] **Step 2: Run focused tests and verify current failures**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_branding.py tests/test_agent.py tests/test_commands.py tests/test_hello_world.py -q`

Expected: FAIL on stale product copy.

- [ ] **Step 3: Rebrand the TUI and write the README**

Apply Deep Ocean colors without changing keybindings or widget behavior. Document install, placeholder-only config, LLM/MCP, TUI, `-p`, Web, SSH tunnel, host/port security, migration, testing, architecture, known issues, upstream derivation, and missing-license caution.

- [ ] **Step 4: Verify copy, attribution, and secret safety**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest tests/test_branding.py tests/test_agent.py tests/test_commands.py tests/test_hello_world.py -q`

Run a filename-only secret scan over tracked files; expected: no real key-pattern match. Confirm all original Python source-attribution headers remain.

- [ ] **Step 5: Commit TUI and documentation**

```powershell
git add codeharbor CODEHARBOR.md README.md tests
git commit -m "docs: complete CodeHarbor product rebrand"
```

### Task 8: Full Regression and Local End-to-End Verification

**Files:**
- Modify: only code/tests directly required by verified failures
- Create: no ad-hoc tracked credential or debug files

**Interfaces:**
- Consumes: all prior tasks.
- Produces: reproducible verification evidence and a clean branch.

- [ ] **Step 1: Synchronize and run the complete suite**

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' sync`

Run: `& 'C:\Users\DELL\.local\bin\uv.exe' run pytest -q`

Expected: no new failures; the Windows `/tmp` baseline failure is fixed. Investigate rather than mask any failure.

- [ ] **Step 2: Run TUI and non-interactive smoke checks**

Verify `codeharbor --help`, TUI startup/config loading, and a real non-interactive prompt returning exactly `CodeHarbor LLM OK`. Do not print the API key.

- [ ] **Step 3: Run local browser/MCP end-to-end checks**

Start `codeharbor --remote --host 127.0.0.1 --port 18888`; verify HTTP 200, `Connected`, real session list, DeepSeek real reply, Context7 recognition/tool call, tool rendering, permission/AskUser behavior, refresh/reconnect, cancel, responsive widths, and zero relevant console errors.

- [ ] **Step 4: Verify package and repository safety**

Build the wheel, inspect its file list, install it into a temporary uv environment, and run `codeharbor --help`. Confirm `.mewcode`, `.codeharbor`, `.venv`, `.superpowers`, API keys, debug logs, and sessions are not tracked.

- [ ] **Step 5: Commit only evidence-driven fixes**

Stage only the exact files changed to resolve verified regressions and commit them with `test: verify CodeHarbor end to end`; omit this commit if no files changed.

### Task 9: Migrate Local Data and Rename the Project Directory

**Files:**
- Runtime copy: `D:\开发学习\mewcode-python\.mewcode` → `D:\开发学习\mewcode-python\.codeharbor`
- Rename directory: `D:\开发学习\mewcode-python` → `D:\开发学习\CodeHarbor`

**Interfaces:**
- Consumes: `migrate_legacy_data_locations()` and the fully verified branch.
- Produces: the final local project path and a preserved `.mewcode` backup.

- [ ] **Step 1: Stop only project-owned local processes**

Identify exact CodeHarbor/MewCode and visual-companion PIDs whose command lines reference `D:\开发学习\mewcode-python`; stop those processes without touching unrelated Python, Node, SSH, or server processes.

- [ ] **Step 2: Run the migration through CodeHarbor**

Start a read-only help/config validation path that invokes migration. Verify `.codeharbor/config.yaml` exists, permissions are no broader than the source, key values are not printed, and `.mewcode` still exists unchanged.

- [ ] **Step 3: Verify the rename target and move the directory**

Confirm the resolved source is exactly `D:\开发学习\mewcode-python` and the target `D:\开发学习\CodeHarbor` does not exist. Rename with a single native PowerShell `Move-Item -LiteralPath` operation.

- [ ] **Step 4: Re-run critical checks from the final path**

From `D:\开发学习\CodeHarbor`, run `git status`, the branding/migration/CLI/Web focused tests, `codeharbor --help`, and an HTTP loopback smoke test. Expected: clean branch and all checks pass.

- [ ] **Step 5: Final verification report**

Report the final path, commits, Python/uv versions, test counts, real LLM/MCP/browser evidence, configuration migration status, preserved backup, security posture, launch commands, and the explicit fact that the server deployment was not changed.

