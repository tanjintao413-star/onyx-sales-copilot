# 企业级 Sales Copilot｜基于 Onyx 的 AI 销售助手

这是一个面向 ToB 销售与售前场景的全栈 AI Agent 二次开发项目。我基于
**Onyx Community Edition** 增加了可运行的 Sales Copilot 业务工作流；并非从零
重写 Onyx。原始 Onyx 代码、Git 历史、归属说明和 [MIT License](LICENSE) 均保留。

## 30 秒了解项目

- **解决的问题：** 让销售人员在一个对话中完成客户查询、会前 Brief、产品知识检索、
  PoC 决策、ROI 估算和受保护的 CRM 写入。
- **我新增的能力：** Sales CRM API、PostgreSQL 演示数据、ROI Tool、Deal Council、
  Agent Custom Action，以及“预览 → 用户明确确认 → 单次写入”的变更保护。
- **真实验证：** 已完成真实 Onyx Agent 的 RAG + Citation、CRM 查询、RAG + CRM、
  ROI、写入确认与 PostgreSQL 落库 Demo；同时通过确定性 Harness 测试。
- **数据边界：** CRM 和业务资料均为本地、确定性的演示数据，不是生产客户数据。

## 我负责的技术实现

| 能力 | 实现方式 |
| --- | --- |
| 知识问答 | 复用 Onyx Search Tool、RAG、OpenSearch 与 Citation |
| CRM 业务能力 | FastAPI + SQLAlchemy + PostgreSQL 的类型化 Sales API |
| Agent 工具调用 | Onyx 原生 Custom Action 调用 Sales API |
| 商机决策 | Sales / Product / Technical 三角色 Deal Council |
| ROI 分析 | 可解释的本地 ROI 计算 Tool |
| 写操作保护 | `confirmed=true` 预览与下一轮明确确认校验 |
| 演示可重复性 | 幂等 Seed、Benchmark Reset、PostgreSQL 集成 Harness |

```text
销售人员
  → Onyx Agent
    ├─ Search Tool → RAG / OpenSearch → 引用（Citation）
    └─ Sales Custom Action → FastAPI → SQLAlchemy → PostgreSQL CRM
```

## 快速查看

- [项目说明与本地运行方式](README_PROJECT.md)
- [5 个 Sales Copilot 演示场景](SALES_DEMO_GUIDE.md)
- [技术实现说明](TECHNICAL_WALKTHROUGH.md)
- [相对于原始 Onyx 的改动边界](CHANGES_FROM_ONYX.md)

> 写操作保护是应用级确认边界，不应被描述为独立的人工审批或 HITL 系统。

---

## Upstream Onyx Community Edition

<a name="readme-top"></a>

<h2 align="center">
    <a href="https://www.onyx.app/?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme"> <img width="50%" src="https://github.com/onyx-dot-app/onyx/blob/logo/OnyxLogoCropped.jpg?raw=true" /></a>
</h2>

<p align="center">
    <a href="https://discord.gg/TDJ59cGV2X" target="_blank">
        <img src="https://img.shields.io/badge/discord-join-blue.svg?logo=discord&logoColor=white" alt="Discord" />
    </a>
    <a href="https://docs.onyx.app/?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme" target="_blank">
        <img src="https://img.shields.io/badge/docs-view-blue" alt="Documentation" />
    </a>
    <a href="https://www.onyx.app/?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme" target="_blank">
        <img src="https://img.shields.io/website?url=https://www.onyx.app&up_message=visit&up_color=blue" alt="Documentation" />
    </a>
    <a href="https://github.com/onyx-dot-app/onyx/blob/main/LICENSE" target="_blank">
        <img src="https://img.shields.io/static/v1?label=license&message=MIT&color=blue" alt="License" />
    </a>
</p>

<p align="center">
  <a href="https://trendshift.io/repositories/12516" target="_blank">
    <img src="https://trendshift.io/api/badge/repositories/12516" alt="onyx-dot-app/onyx | Trendshift" style="width: 250px; height: 55px;" />
  </a>
</p>

# Onyx - The Open Source AI Platform

**[Onyx](https://www.onyx.app/?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme)** is the application layer for LLMs - bringing a feature-rich interface that can be easily hosted by anyone.
Onyx enables LLMs through advanced capabilities like RAG, web search, code execution, file creation, deep research and more.

Connect your applications with over 50+ indexing based connectors provided out of the box or via MCP.

> [!TIP]
> Deploy with a single command:
> ```
> curl -fsSL https://onyx.app/install_onyx.sh | bash
> ```

![Onyx Chat Silent Demo](https://github.com/onyx-dot-app/onyx/releases/download/v3.0.0/Onyx.gif)

---

## ⭐ Features

- **🔍 Agentic RAG:** Get best in class search and answer quality based on hybrid index + AI Agents for information retrieval
  - Benchmark to release soon!
- **🔬 Deep Research:** Get in depth reports with a multi-step research flow.
  - Top of [leaderboard](https://github.com/onyx-dot-app/onyx_deep_research_bench) as of Feb 2026.
- **🤖 Custom Agents:** Build AI Agents with unique instructions, knowledge, and actions.
- **🌍 Web Search:** Browse the web to get up to date information.
  - Supports Serper, Google PSE, Brave, SearXNG, and others.
  - Comes with an in house web crawler and support for Firecrawl/Exa.
- **📄 Artifacts:** Generate documents, graphics, and other downloadable artifacts.
- **▶️ Actions & MCP:** Let Onyx agents interact with external applications, comes with flexible Auth options.
- **💻 Code Execution:** Execute code in a sandbox to analyze data, render graphs, or modify files.
- **🎙️ Voice Mode:** Chat with Onyx via text-to-speech and speech-to-text.
- **🎨 Image Generation:** Generate images based on user prompts.

Onyx supports all major LLM providers, both self-hosted (like Ollama, LiteLLM, vLLM, etc.) and proprietary (like Anthropic, OpenAI, Gemini, etc.).

To learn more - check out our [docs](https://docs.onyx.app/welcome?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme)!

---

## 🚀 Deployment Modes

> Onyx supports deployments in Docker, Kubernetes, Helm/Terraform and provides guides for major cloud providers.
> Detailed deployment guides found [here](https://docs.onyx.app/deployment/overview).

Onyx supports two separate deployment options: standard and lite.

#### Onyx Lite

The Lite mode can be thought of as a lightweight Chat UI. It requires less resources (under 1GB memory) and runs a less complex stack.
It is great for users who want to test out Onyx quickly or for teams who are only interested in the Chat UI and Agents functionalities.

#### Standard Onyx

The complete feature set of Onyx which is recommended for serious users and larger teams. Additional components not included in Lite mode:
- Vector + Keyword index for RAG.
- Background containers to run job queues and workers for syncing knowledge from connectors.
- AI model inference servers to run deep learning models used during indexing and inference.
- Performance optimizations for large scale use via in memory cache (Redis) and blob store (MinIO).

> [!TIP]  
> **To try Onyx for free without deploying, visit [Onyx Cloud](https://cloud.onyx.app/signup?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme)**.

---

## 🏢 Onyx for Enterprise

Onyx is built for teams of all sizes, from individual users to the largest global enterprises:
- 👥 Collaboration: Share chats and agents with other members of your organization.
- 🔐 Single Sign On: SSO via Google OAuth, OIDC, or SAML. Group syncing and user provisioning via SCIM.
- 🛡️ Role Based Access Control: RBAC for sensitive resources like access to agents, actions, etc.
- 📊 Analytics: Usage graphs broken down by teams, LLMs, or agents.
- 🕵️ Query History: Audit usage to ensure safe adoption of AI in your organization.
- 💻 Custom code: Run custom code to remove PII, reject sensitive queries, or to run custom analysis.
- 🎨 Whitelabeling: Customize the look and feel of Onyx with custom naming, icons, banners, and more.

## 📚 Licensing

There are two editions of Onyx:

- Onyx Community Edition (CE) is available freely under the MIT license and covers all of the core features for Chat, RAG, Agents, and Actions.
- Onyx Enterprise Edition (EE) includes extra features that are primarily useful for larger organizations.

For feature details, check out [our website](https://www.onyx.app/pricing?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme).

## 👪 Community

Join our open source community on **[Discord](https://discord.gg/TDJ59cGV2X)**!

## 💡 Contributing

Looking to contribute? Please check out the [Contribution Guide](CONTRIBUTING.md) for more details.
