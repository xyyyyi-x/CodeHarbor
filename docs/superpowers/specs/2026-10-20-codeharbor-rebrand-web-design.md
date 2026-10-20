# CodeHarbor 全量品牌迁移与 Web 工作台设计

**日期：** 2026-10-20  
**状态：** 已由用户确认  
**目标版本：** 0.2.0  
**标语：** Your code. Guided home.

## 1. 目标与边界

本项目把 MewCode 全量迁移为 CodeHarbor，并将现有嵌入式浏览器页面重构为可维护、响应式且安全的 AI Coding Agent 工作台。迁移包括产品显示名称、CLI、Python 包、配置目录、测试、文档和项目目录；不保留 `mewcode` CLI 或 `mewcode.*` Python 导入兼容层。

本阶段保留现有 Agent、LLM、MCP、权限、Memory、Skill、团队协作、Worktree、TUI 和 WebSocket 业务能力，不引入账户系统、云同步、项目管理平台、React/Vite 或新的远程部署架构。服务器上的现有 MewCode 本轮不覆盖。

## 2. 品牌设计

- 产品名：`CodeHarbor`
- CLI：`codeharbor`
- Python 分发包：`codeharbor`
- Python 导入包：`codeharbor`
- 配置与运行数据目录：`.codeharbor`
- 最终本地项目目录：`D:\开发学习\CodeHarbor`
- Logo：Harbor Beacon（灯塔信标）
- 视觉主题：Deep Ocean
- 主背景：深海蓝
- 强调色：信标青
- 点缀色：暖金，仅用于灯塔、关键状态和少量品牌强调
- 界面语言：中文为主；Provider、Model、MCP、Token 等技术词保留英文

产品界面全部使用 CodeHarbor。源码中已有的来源声明必须保留，不得伪造许可证或宣称完全原创。README 必须说明这是基于 MewCode 代码的二次开发，并提示当前压缩包未提供明确许可证；该说明不出现在产品主标题、Logo 或日常聊天界面中。

## 3. 代码与数据迁移

### 3.1 Python 包迁移

将 `mewcode/` 整体重命名为 `codeharbor/`，并更新：

- 全部 `mewcode.*` 导入
- `python -m mewcode` 形式的内部调用
- `pyproject.toml` 的项目名、构建包和脚本入口
- 测试中的 patch 路径、导入和品牌断言
- 内置 Agent、Skill、Prompt 和帮助文本中的产品名称

不提供旧 `mewcode` 命令或旧导入包 shim。版本保持 `0.2.0`。

### 3.2 配置迁移

所有新路径统一使用 `.codeharbor`。启动时执行幂等迁移：

1. 如果目标 `.codeharbor` 已存在，不覆盖任何内容。
2. 如果目标不存在且同级旧 `.mewcode` 存在，则完整复制旧目录到 `.codeharbor`。
3. 复制成功后继续从 `.codeharbor` 加载。
4. 旧 `.mewcode` 永不自动删除、移动或改写，作为用户备份保留。
5. 迁移日志不得输出 API Key、Header、环境变量值或配置文件正文。
6. 用户主目录和项目目录分别迁移，各自遵循相同规则。

配置查找顺序保持原语义，但路径改为：

1. `~/.codeharbor/config.yaml`
2. `<cwd>/.codeharbor/config.yaml`
3. `<cwd>/.codeharbor/config.local.yaml`

## 4. 品牌常量

新增单一品牌模块，集中定义：

- `PRODUCT_NAME = "CodeHarbor"`
- `PRODUCT_PACKAGE = "codeharbor"`
- `PRODUCT_CLI = "codeharbor"`
- `PRODUCT_TAGLINE = "Your code. Guided home."`
- `PRODUCT_VERSION = "0.2.0"`
- `DATA_DIR_NAME = ".codeharbor"`
- `LEGACY_DATA_DIR_NAME = ".mewcode"`

TUI、CLI、Web 元数据和文档生成逻辑引用这些常量，避免新的品牌硬编码散落。

## 5. Web 架构

采用纯 Python 模块化静态资源方案，不增加 Node 构建链：

```text
codeharbor/web/
  __init__.py
  index.html
  styles.css
  app.js
  assets/
    codeharbor-beacon.svg
    favicon.svg
  vendor/
    marked.min.js
    purify.min.js
    LICENSES.md
```

Python 使用 `importlib.resources` 读取包内资源。HTTP 服务提供：

- `/`：HTML 入口
- `/assets/*`：品牌与样式资源
- `/vendor/*`：本地化 Markdown 与清理依赖
- `/ws`：原 WebSocket 入口

静态资源路径必须阻止目录穿越，并返回准确的 Content-Type。删除旧的巨大 `INDEX_HTML` 内联实现，不保留双份前端来源。

## 6. Web 工作台布局

### 6.1 顶栏

展示 Harbor Beacon、CodeHarbor、标语、当前 Model、Token 使用量和连接状态。断线、重连和忙碌状态必须同时使用文字与颜色表达，不能只依赖颜色。

### 6.2 左侧栏

包含：

- 新建会话
- 从现有 SessionManager 真实读取的会话列表
- MCP 服务状态摘要
- 设置入口

不展示不可用的虚假会话或占位功能。新建会话必须走现有清空或会话创建语义，并在后端成功后更新 UI。

### 6.3 主聊天区

保持并改进：

- 用户与 Assistant 消息
- 流式文本
- 思考过程折叠
- 工具调用、参数、输出与耗时
- Permission 请求
- AskUser 交互
- 重试、错误、压缩和完成状态
- 斜杠命令补全
- 自动滚动，但用户主动上滚后暂停跟随

输入区支持 Enter 发送、Shift+Enter 换行。生成过程中发送按钮变为停止按钮并发送 `cancel`，输入框保持明确禁用状态。

### 6.4 右侧状态栏

展示当前 Provider、Model、Permission Mode、工作目录、MCP 连接和 Web 绑定地址。API Key 只能展示“已配置/未配置”，后端不得向浏览器发送密钥或配置正文。

### 6.5 响应式

- 宽屏：三栏布局
- 中等宽度：隐藏右侧栏，其内容放入状态抽屉
- 小屏：左侧栏改为抽屉，只保留聊天与输入区
- 输入区、Permission 和 AskUser 在窄屏不得溢出
- 支持 `prefers-reduced-motion`
- 键盘焦点必须清晰可见

## 7. WebSocket 数据流

保留现有消息名称和核心字段。

浏览器发送：`user_message`、`permission_response`、`ask_user_response`、`cancel`、`ping`。

服务端发送：`connected`、`commands`、`system`、`clear`、`command_done`、`replay_user`、`replay_assistant`、`stream_text`、`stream_end`、`thinking_text`、`tool_use`、`tool_result`、`permission_request`、`ask_user`、`turn_complete`、`loop_complete`、`usage`、`error`、`compact`、`retry`、`pong`。

`connected` 可以增加向后兼容的可选元数据：产品名、版本、Provider 名称、Model、Permission Mode、MCP 状态和绑定地址。新增会话列表事件时必须是可选扩展，旧客户端忽略后仍可聊天。

## 8. Markdown 与浏览器安全

- `marked` 和 DOMPurify 本地化，不依赖 CDN。
- 保留第三方许可证文本和版本信息。
- Markdown 渲染结果在写入 DOM 前必须经过 DOMPurify。
- 禁止事件处理器、脚本、危险 URL scheme 和任意 iframe。
- 工具参数、工具输出、错误文本和系统信息默认使用 `textContent`。
- 外部链接使用安全的 `rel="noopener noreferrer"`。
- 不向前端暴露 API Key、环境变量或完整配置。
- WebSocket 单条消息继续受大小限制。

## 9. CLI 与监听安全

CLI 仅提供 `codeharbor`。保留 TUI、`-p` 和 `--remote` 模式，并增加：

- `--host`，默认 `127.0.0.1`
- `--port`，默认 `18888`，范围 1–65535

`--host 0.0.0.0` 或其他非回环地址时，在启动前打印明显警告，说明 Web UI 没有身份认证，不应直接暴露公网。不得自动修改防火墙、代理、Nginx、域名或 TLS。

## 10. 错误处理

- 静态资源缺失：返回 404，并记录不含敏感信息的资源名。
- 端口占用：CLI 明确显示 host、port 和操作建议，非零退出。
- WebSocket 断线：指数退避重连并显示状态；恢复后不重复追加连接欢迎消息。
- 用户发送期间断线：保留输入草稿，明确提示消息是否未发送。
- Markdown 依赖异常：安全降级为纯文本，不直接插入原始 HTML。
- 数据迁移失败：保留旧目录不变，输出目标路径与错误类型，不输出文件正文；停止启动以避免使用半迁移状态。
- MCP 单服务失败：显示该服务失败，不拖垮整个 CodeHarbor。

## 11. TUI

TUI 使用 CodeHarbor 名称、0.2.0 版本、Harbor Beacon 的简化文本符号和 Deep Ocean 对应配色。功能与按键行为保持不变。标题、Banner、状态命令、帮助文本和系统 Prompt 不再显示 MewCode 品牌。

## 12. 文档

新增 `README.md`，包含：

- CodeHarbor 介绍与标语
- 功能、截图位置和架构
- Python 3.11+ 与 uv 安装
- `.codeharbor/config.yaml` 示例，只使用占位 API Key
- LLM、MCP、TUI、非交互和 Web 启动方式
- `--host`、`--port` 与 SSH 隧道示例
- 安全、兼容性、数据迁移和已知问题
- 基于 MewCode 二次开发及授权状态说明

原 `MEWCODE.md` 的项目指令内容迁移为 `CODEHARBOR.md`。源码来源声明保留。

## 13. 测试与验收

自动化测试覆盖：

- 品牌常量与包元数据
- `codeharbor` CLI 入口，且不再安装 `mewcode` 命令
- `.mewcode` 到 `.codeharbor` 的首次复制、目标已存在、失败回滚和不泄密日志
- Windows、Linux 路径
- `--host`、`--port` 默认值、合法范围与公网警告
- `/`、静态资源、Content-Type、404 和目录穿越
- WebSocket 旧协议事件兼容与新增可选元数据
- Markdown XSS 样例、工具输出转义和纯文本降级
- 会话列表、新建会话、取消和断线恢复

完整验收包括：

1. `uv sync`
2. `uv run pytest`
3. TUI 冒烟测试
4. `codeharbor --remote --host 127.0.0.1 --port 18888`
5. 浏览器验证连接、会话、真实 LLM 流式回复、工具调用、MCP、权限交互、刷新重连和控制台错误
6. 密钥扫描与 Git 状态检查

现有 Windows 基线为 584 passed、3 skipped、1 failed；已知失败来自测试写死 `/tmp`。允许用 `tmp_path` 修复其跨平台性，但不得改变测试意图。改造完成后不得新增失败。

## 14. Git 与目录收尾

- 基线提交位于 `main`
- 开发分支：`codex/rebrand-web-ui`
- `.mewcode/`、`.codeharbor/`、`.venv/`、`.superpowers/` 均不得进入 Git
- 完成全部测试和浏览器验证后，停止使用旧路径的本地进程，再将根目录改为 `D:\开发学习\CodeHarbor`
- 改名后重新执行关键启动与配置读取检查
- 不推送远程，不部署服务器，除非用户另行授权

