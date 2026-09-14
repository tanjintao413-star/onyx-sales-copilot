# Enterprise AI Sales Copilot

一个基于 Onyx Community Edition 的二次开发 PoC，面向 ToB 销售、售前与 FDE。它把 Onyx 原生 RAG 和 Agent Tool Calling 连接到一套可复现的销售 CRM 演示数据。

## Why Onyx

Onyx 原生提供聊天、Agent、RAG、文档索引、引用、权限、Tool Runner 和可配置的 OpenAPI/MCP Actions。本项目只增加销售领域的类型安全 API、CRM 数据、写操作确认边界和 ROI 计算；不重写 RAG 或 Agent loop。

```mermaid
flowchart TD
  U[Sales user] --> A[Onyx Agent]
  A --> R[Native RAG / citations]
  A --> T[Sales Copilot OpenAPI tools]
  T --> C[(PostgreSQL CRM demo tables)]
  A --> ROI[ROI calculator]
  T --> H[Mutation confirmation boundary]
```

## Features

- Accounts, contacts, opportunities, products, activities and follow-up tasks.
- Read endpoints for account, opportunity, activity and pipeline analysis.
- Write endpoints guarded by an explicit `confirmed` field for tasks and opportunity stages.
- Transparent ROI calculation.
- Demo knowledge files in `docs/sales_copilot_knowledge/`, ingested through the normal Onyx document flow.

## Setup

1. Follow the root `CONTRIBUTING.md` prerequisites: Python 3.13, uv, Docker and Bun.
2. Start standard Onyx services, then run `uv run alembic upgrade head` from `backend/`.
3. Register the local demo user and ingest the two markdown knowledge files through
   an Onyx file or connector flow. This preserves native retrieval and citations.
4. Create the Sales Custom Action from the live server OpenAPI schema; the API
   prefix is `/sales-copilot`.
5. Run `uv run python backend/scripts/seed_sales_copilot_demo.py --admin-email <local-user-email>`
   from the repository root. The idempotent bootstrap uses Onyx's native Admin
   group helper, refreshes the existing Sales Action schema, and configures the
   Chinese-first `销售助手 · Sales Copilot` Persona with Search, Action and knowledge.

This CE checkout ships UI locales for English, Spanish, Portuguese, French and
German, but not Simplified Chinese. The bootstrap therefore keeps the stored UI
locale valid and makes the Sales-specific Agent name, description, instructions,
starters and responses Chinese-first; it does not claim to translate upstream UI.

For mutating tools, the intended UX is preview followed by user approval before `confirmed=true`. This is an application-level confirmation guard, not an independent HITL approval system: a model that is permitted to call the Action can itself supply `confirmed=true`.

## Demo Reset

Before an interview or demo:

1. Start the documented Onyx Docker services.
2. Run `uv run python backend/scripts/seed_sales_copilot_demo.py --reset-benchmark-state`.
3. Open `http://localhost:3000`.
4. Select `销售助手 · Sales Copilot`.

The reset restores CRM rows managed by `crm_seed_spec.json`, including benchmark
activities, opportunity fields and follow-up tasks. It does not upload, delete or
reindex knowledge files. It does not change Persona, Action, permission or user data.

## Demo prompts

1. 我们的企业 Agent 对私有化部署和数据安全提供哪些能力？
2. 当前 Pipeline 中金额最大的三个 AI Agent 商机是什么？
3. 下午要见星海科技，给我准备完整会前 Brief。
4. 星海科技有 3000 名员工，大量内部 IT 和 HR 问题依赖人工处理，给他们设计一个 AI Agent PoC。
5. 为星海科技创建一个下周的 PoC 跟进任务。

## Test status

Live validation was refreshed on 2026-09-11 with the official backend image and
standard PostgreSQL, Redis, OpenSearch, MinIO and model-server services. Persona 1
used Search Tool 1, Custom Action 12 and the indexed knowledge files with a real
`deepseek-v4-flash` OpenAI-compatible provider. Five live, manual end-to-end demos
passed: Agent discovery, CRM reads, RAG with native citations, the read-only
Sales/Product/Technical Deal Council, and preview → explicit confirmation flag →
exactly-once PostgreSQL mutation. The separate deterministic Harness passed 22
Sales unit tests, 13 eval definitions, 8 PostgreSQL API integration tests and 2
Deal Council integration tests. All CRM records are local deterministic demo data,
not a production CRM.

The local frontend was served with the repository's documented Bun development command because a production Next.js build exceeded the available Docker Desktop resources. This did not change application source, the Dockerfile, the Compose dependency graph or locked dependencies.
