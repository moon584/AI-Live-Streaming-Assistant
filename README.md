# AI Live Streaming Assistant

让 AI 为你的直播间提供实时辅助：弹幕理解、智能回复、内容总结、自动化运营与互动增强。

![项目封面图](docs/cover.png)

---

## 📑 目录

- [背景与目标](#背景与目标)
- [核心功能](#核心功能)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
  - [先决条件](#先决条件)
  - [克隆仓库](#克隆仓库)
  - [环境配置](#环境配置)
  - [本地启动](#本地启动)
  - [Docker 运行](#docker-运行)
- [配置说明](#配置说明)
- [使用指南](#使用指南)
- [与直播工具/平台集成](#与直播工具平台集成)
- [常见问题](#常见问题)
- [路线图](#路线图)
- [贡献指南](#贡献指南)
- [许可协议](#许可协议)
- [致谢](#致谢)
- [联系与支持](#联系与支持)

---

## 背景与目标

在直播场景中，主播往往需要同时兼顾内容输出、弹幕互动与运营任务。AI Live Streaming Assistant 旨在通过 AI 技术，为直播间提供「实时理解」「智能响应」「自动化运营」三大能力，帮助主播提升互动质量与运营效率。

---

## 核心功能

- 实时弹幕理解与总结
- 智能关键词触发与自动回复
- 常见问答/商品信息/活动规则的统一答复
- 高亮弹幕提取与台本提醒
- 直播片段关键点标注与事后总结
- 多模型可插拔（大语言模型/语音识别/语音合成等，视项目实际而定）

---

## 目录结构

> 以下为建议结构，实际请以仓库为准

```text
AI-Live-Streaming-Assistant/
├─ docs/
│  └─ images/
│     ├─ cover.png
│     ├─ architecture.png
│     └─ features/
│        ├─ feature-1.png
│        ├─ feature-2.png
│        ├─ feature-3.png
│        └─ feature-4.png
├─ src/                      # 业务源码（后端/服务/适配层）
├─ web/                      # 前端控制台
├─ scripts/                  # 脚本/工具
├─ configs/
│  └─ config.example.yaml
├─ .env.example
├─ docker-compose.yml        # 可选
├─ Dockerfile                # 可选
└─ README.md
```

---

## 快速开始

### 先决条件

- **Git**：最新稳定版
- **操作系统**：macOS / Linux / Windows
- **运行时**（按实际项目选择）：
  - Node.js ≥ 18（前端或 Node 服务）
  - Python ≥ 3.10（Python 服务）
  - 其他：Go / Java / Rust
- **可选依赖**：
  - Docker ≥ 24、Docker Compose ≥ v2
  - ffmpeg（音视频处理）
  - OBS（直播推流/采集）

### 克隆仓库

```bash
git clone https://github.com/moon584/AI-Live-Streaming-Assistant.git
cd AI-Live-Streaming-Assistant
```

### 环境配置

**1. 复制环境变量样例**

```bash
cp .env.example .env
```

**2. 编辑 `.env` 文件**

```dotenv
# LLM & 平台
OPENAI_API_KEY=your_key_here           # 或其他模型提供方 API Key
OPENAI_API_BASE=                       # 可选自定义网关
MODEL_NAME=gpt-4o-mini                 # 示例：根据实际模型调整

# 数据源/平台凭证
PLATFORM=                             # bilibili | douyin | twitch | youtube 等
PLATFORM_API_KEY=
PLATFORM_ROOM_ID=

# Redis / 数据库（可选）
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:pass@localhost:5432/stream_assistant

# 服务器/服务配置
PORT=3000
LOG_LEVEL=info
```

**3. 配置文件（如使用）**

```bash
cp configs/config.example.yaml configs/config.yaml
```

### 本地启动

根据项目技术栈选择相应的启动方式：

**Node 服务**

```bash
cd src
npm install
npm run dev
```

**Python 服务**

```bash
cd src
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py               # 或 uvicorn main.py
```

**前端控制台**

```bash
cd web
npm install
npm run dev
```

### Docker 运行

**单容器启动**

```bash
docker build -t ai-live-assistant .
docker run --env-file .env -p 3000:3000 ai-live-assistant
```

**编排启动**

```bash
docker compose up -d
```

---

## 配置说明

| 模块 | 说明 |
|------|------|
| 规则引擎 | 支持按关键词、正则、阈值或上下文主题触发动作 |
| 弹幕聚合 | 设置聚合窗口与采样策略 |
| 模型网关 | 自定义模型供应商、超时、重试、并发限流 |
| 存储 | Redis 缓存、PostgreSQL/MySQL 持久化 |
| 日志 | `LOG_LEVEL` 可设为 `debug`/`info`/`warn`/`error` |

---

## 使用指南

1. 启动服务后在控制台登录并绑定直播间
2. 按需开启功能：弹幕聚合、自动回复、主播提示卡等
3. 在"规则引擎"中配置关键词与触发动作
4. 打开直播，观察控制台的实时面板与高亮卡片
5. 直播结束后在"回放/总结"中查看主题摘要与要点

---

## 与直播工具/平台集成

- **OBS**：通过浏览器源加载控制台提示卡/覆盖层（Overlay）
- **平台 API**：使用官方/第三方 SDK 获取弹幕与房间事件
- **Webhook**：接收平台事件或将自动回复推送至平台接口

---

## 常见问题

**Q：无法连接到平台**

检查 `PLATFORM_API_KEY`、房间号、网络代理设置

**Q：模型调用失败**

检查 `OPENAI_API_KEY` 或替代模型配置、网络连通性、速率限制

**Q：自动回复未生效**

核实规则匹配条件与优先级，设置 `LOG_LEVEL=debug` 查看运行日志

---

## 路线图

- [ ] 支持更多直播平台适配
- [ ] 规则引擎可视化编辑器
- [ ] 更细粒度的权限与多租户能力
- [ ] 片段自动剪辑与标题/封面生成
- [ ] A/B 实验与效果看板

---

## 贡献指南

欢迎 Issue、Pull Request 与功能建议！

**1. Fork 仓库并创建特性分支**

```bash
git checkout -b feat/your-feature
```

**2. 提交更改并推送**

```bash
git commit -m "feat: your feature"
git push origin feat/your-feature
```

**3. 提交 Pull Request**

描述变更背景、动机与测试方法。

> **建议**：遵循 Conventional Commits、配套单元测试、更新文档/示例

---

## 许可协议

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 致谢

- 开源社区与相关 SDK/模型框架
- 贡献者与使用者

---

## 联系与支持

- **Issues**：[在此提交问题/建议](https://github.com/moon584/AI-Live-Streaming-Assistant/issues)
- **维护者**：@moon584
