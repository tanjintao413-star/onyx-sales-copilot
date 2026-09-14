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

## 关于上游 Onyx

[Onyx Community Edition](https://github.com/onyx-dot-app/onyx) 是 MIT 许可的开源
企业 AI 平台，提供 Agent、RAG、检索、Citation、连接器和可配置 Action 等基础能力。
本项目在其成熟架构中完成销售业务二次开发，不将上游能力表述为个人原创。

- 上游项目：[onyx-dot-app/onyx](https://github.com/onyx-dot-app/onyx)
- 上游文档：[docs.onyx.app](https://docs.onyx.app/)
- 本项目保留：[MIT License](LICENSE)、上游 Git 历史与版权归属
- 详细改动边界：[CHANGES_FROM_ONYX.md](CHANGES_FROM_ONYX.md)

如需了解 Onyx 的完整通用功能、部署方式和社区资源，请直接访问上游仓库和官方文档。
