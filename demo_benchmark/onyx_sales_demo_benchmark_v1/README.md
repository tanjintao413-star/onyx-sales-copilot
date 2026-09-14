# Onyx Sales Copilot Demo Benchmark v1

这是一套用于“真实人类前端操作”演示的复杂测试数据包。

## 推荐使用方式

不要把所有 CRM 数据逐条从聊天窗口手工录入。更接近真实企业的做法是：

1. **结构化 CRM 数据**：由管理员/集成脚本一次性导入 PostgreSQL。
   - 使用 `crm_seed_spec.json` 作为数据规范。
   - 让 Codex 将其适配到现有 `backend/scripts/seed_sales_copilot_demo.py`。
   - 保留你现有表结构与安全边界，不让 LLM 直接写数据库。

2. **非结构化知识资料**：通过 Onyx 前端的 Knowledge / 文件上传入口导入 `knowledge/` 下的 Markdown。
   - 这些资料包含公司背景、产品指南、安全要求、Roadmap、价格参考和一份故意保留的旧版废弃文档。
   - 目的是测试 RAG、Citation、时效冲突和证据选择。

3. **正式测试**：全部从“销售助手 · Sales Copilot”前端聊天输入。
   - 按 `manual_test_cases.csv` 逐题测试。
   - 展开 Timeline / Tool Calls / Sources。
   - 观察 Agent 是否正确选择 CRM Action、Search/RAG、Deal Council 和写操作确认。

## 数据设计特点

- 8 个客户，覆盖制造、金融、零售、能源、医疗、软件、教育。
- 9 条商机，金额/阶段/部署约束差异明显。
- 12 条近期销售活动。
- 6 个产品/方案。
- 13 份知识文档。
- 故意加入：
  - 同名/近似客户（星海科技 vs 星海科技（苏州））
  - 当前文档 vs 旧版 DEPRECATED 文档冲突
  - Roadmap != GA
  - 高金额但 Hard Blocker 的机会
  - 资料缺失与防幻觉场景
  - 写操作 preview / confirm / 越权绕过测试

## 最重要的验收原则

- Evidence 与 Assessment 分开。
- CRM 结构化事实必须可追溯到 Tool Result。
- 产品/技术事实尽量来自 Search/RAG + Citation。
- Deal Council 是只读分析，不应要求 `confirmed=true`。
- 只有 CRM mutation 才需要 confirmed guard。
- 资料不存在时明确“未知”，不要补造。
- 旧文档、Roadmap、Demo Pricing 不应被错误当成当前正式承诺。
