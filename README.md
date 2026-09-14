# Sales Copilot

**面向企业销售与售前的 AI 助手：把客户记录、产品知识和下一步行动放进同一次对话。**

本项目基于 [Onyx Community Edition](https://github.com/onyx-dot-app/onyx) 二次开发。
Onyx 提供 Agent、文档检索和引用；这里接入了可运行的 CRM 业务 API、
PostgreSQL 演示数据、ROI 计算和商机决策流程。

## 从问题到行动

销售人员可以询问“星海科技的商机还值得推进吗？”。Sales Copilot 会读取客户与商机记录，
检索相关产品和安全文档，并在回答中标出引用。复杂的 PoC 决策会交给
Sales、Product、Technical 三个只读角色分析，再汇总冲突和阻碍。

需要写入 CRM 时，助手先返回变更预览。只有下一轮用户明确确认相同变更，
服务端才接受写入。这个机制是应用级确认保护，不是独立的人工审批系统。

```text
用户 → Onyx Agent
       ├─ Search Tool → RAG / OpenSearch → 引用来源
       └─ Sales Custom Action → FastAPI → SQLAlchemy → PostgreSQL
```

## 演示与验证

真实 Onyx Agent 演示已覆盖带引用的知识问答、CRM 查询、知识与 CRM 联合分析、
ROI 估算，以及任务预览、明确确认和 PostgreSQL 落库。
[查看 5 个演示场景](SALES_DEMO_GUIDE.md)。

CRM 客户、商机和产品均为**本地确定性模拟数据**。演示前可运行 Benchmark Reset
恢复基准状态；[运行步骤与测试结果](README_PROJECT.md)记录在项目说明中。

## 继续阅读

- [架构与实现](TECHNICAL_WALKTHROUGH.md)
- [相对原始 Onyx 的改动](CHANGES_FROM_ONYX.md)
- [Benchmark 数据与知识材料](demo_benchmark/onyx_sales_demo_benchmark_v1/README.md)

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
