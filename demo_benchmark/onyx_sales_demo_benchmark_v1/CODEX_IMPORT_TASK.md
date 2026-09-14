请把 `crm_seed_spec.json` 适配进当前 Onyx Sales Copilot Demo 数据，但不要改变现有数据库 schema。

要求：
1. 先阅读当前 `backend/scripts/seed_sales_copilot_demo.py` 和 Sales Copilot SQLAlchemy models。
2. 将 accounts / opportunities / activities / products 以 idempotent 方式 seed。
3. 如果现有字段不完全一致，按当前项目模型做最小映射，不要新增无必要字段。
4. 不删除用户现有数据；只更新/创建本 Demo 标识的数据。
5. 保留现有 admin bootstrap、Agent、Action、Knowledge、confirmed guard。
6. 不自动把 `knowledge/` 文档直接写入数据库；这些文件留给我从 Onyx 前端 Knowledge 上传，以模拟真实管理员操作。
7. seed 后运行 `make sales-harness-fast`；如本次改动涉及 integration 数据，再运行相关 integration。
8. 输出：变更文件、seed数量、测试结果、`git diff --stat`。不要自动 push。
