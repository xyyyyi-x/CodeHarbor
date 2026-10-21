# CodeHarbor

> Your code. Guided home.

CodeHarbor 是一个以 Python 构建的 AI Coding Agent，可在终端 TUI、非交互命令行和浏览器工作台中使用。它支持多种 LLM 协议、MCP 工具、权限控制、会话恢复、记忆、Skills、团队协作与 Git worktree。

当前版本：`0.2.0`

## 界面预览

浏览器工作台采用 Deep Ocean 三栏布局：左侧管理会话，中间进行对话和查看工具调用，右侧显示 Provider、Model、MCP 与工作区状态。项目截图建议放在 `docs/images/codeharbor-web.png`。

## 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js 与 `npx`（仅在使用基于 Node.js 的 MCP Server 时需要）

## 安装

```powershell
git clone <your-codeharbor-repository-url>
cd CodeHarbor
uv sync
```

## 配置 LLM 与 MCP

在项目根目录创建 `.codeharbor/config.yaml`：

```yaml
providers:
  - name: my-provider
    protocol: openai-compat
    base_url: https://your-api-provider.example/v1
    api_key: "your-api-key-here"
    model: your-model-name
    thinking: false

mcp_servers:
  - name: context7
    command: npx
    args: ["-y", "@upstash/context7-mcp"]

enable_coordinator_mode: false
```

支持的协议：

- `anthropic`：Anthropic Messages API
- `openai`：OpenAI Responses API
- `openai-compat`：OpenAI Chat Completions 兼容接口

配置加载顺序为用户目录、项目目录、项目本地覆盖文件。不要把真实 API Key 提交到 Git；`.codeharbor/` 已被忽略。

## 使用方式

启动终端 TUI：

```powershell
uv run codeharbor
```

执行单次任务：

```powershell
uv run codeharbor -p "解释这个项目的架构"
```

启动浏览器工作台（默认仅监听本机）：

```powershell
uv run codeharbor --remote --host 127.0.0.1 --port 18888
```

然后访问 `http://127.0.0.1:18888/`。

### 从远程服务器安全访问

Web 工作台当前没有身份认证。推荐让服务端只监听回环地址，再通过 SSH 隧道访问：

```powershell
ssh -L 18888:127.0.0.1:18888 user@your-server
```

不要把 `--host 0.0.0.0` 直接暴露到公网。如果必须绑定非回环地址，请在受控网络内使用，并另行配置认证、TLS 和防火墙。

## 数据迁移

首次启动时，如果新的 `.codeharbor` 数据目录不存在而旧的 `.mewcode` 目录存在，CodeHarbor 会非破坏性复制旧数据。旧目录不会自动删除；如果新目录已存在，也不会覆盖其中内容。

## 测试与构建

```powershell
uv sync
uv run pytest
uv build
```

## 架构概览

- `codeharbor/agent.py`：Agent 事件循环与工具执行
- `codeharbor/client.py`：LLM Provider 客户端
- `codeharbor/app.py`：Textual TUI
- `codeharbor/remote.py`：浏览器服务与 WebSocket 桥接
- `codeharbor/web/`：无构建链的浏览器静态资源
- `codeharbor/mcp/`：MCP Server 管理
- `codeharbor/memory/`：指令、会话和长期记忆
- `codeharbor/tools/`：内置工具

## 已知限制

- Web 工作台不提供账户、登录或访问令牌。
- 浏览器前端采用原生 HTML/CSS/JavaScript，没有 React/Vite 构建链。
- 单个 MCP Server 失败会显示为不可用，但不会阻止其他能力启动。
- 远程公网部署需要用户自行提供反向代理、TLS 和认证。

## 来源与授权说明

CodeHarbor 基于 MewCode 源码进行二次开发，保留了原始 Python 源文件中的来源声明。本项目收到的源码压缩包未包含明确的 `LICENSE` 或 `NOTICE` 文件，因此当前授权状态不明确；在公开发布、再分发或商业使用前，请先向上游作者确认许可。本文不对上游代码主张原创权，也不替代正式法律意见。
