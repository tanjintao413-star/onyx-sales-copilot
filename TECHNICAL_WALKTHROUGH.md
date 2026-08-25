# Technical Walkthrough

Read these files in order; do not start by reading all of Onyx.

1. `README_PROJECT.md` — product boundary and setup.
2. `backend/onyx/main.py` — FastAPI router registration.
3. `backend/onyx/server/sales_copilot/api.py` — Sales API schemas, confirmation and ROI formula.
4. `backend/onyx/db/sales_copilot.py` — typed CRM queries/mutations.
5. `backend/onyx/db/models.py` — `Sales*` tables; understand only these six models.
6. `backend/alembic/versions/9a10b11c12d1_add_sales_copilot_demo_tables.py` — database lifecycle.
7. `backend/scripts/seed_sales_copilot_demo.py` — reproducible 星海科技 demo data.
8. `backend/onyx/tools/interface.py` — Tool contract used by Onyx.
9. `backend/onyx/tools/tool_constructor.py` — how agent-attached tools are constructed.
10. `backend/onyx/tools/tool_runner.py` — where tool execution and trace records occur.
11. `backend/onyx/tools/tool_implementations/search/search_tool.py` — native RAG tool.
12. `backend/onyx/chat/llm_loop.py` — Agent tool-call loop.

Call chains: RAG is user → `llm_loop` → SearchTool → document index → citation. CRM is user → Custom Action → `sales_copilot/api.py` → `db/sales_copilot.py` → PostgreSQL → tool result → model. A mutation returns `confirmation_required` for `confirmed=false` and commits for `confirmed=true`; this is a model-callable guard, not an independent HITL approval service.

Validation note: the three call chains were executed in manual live E2E validation on 2026-08-25. RAG returned citations from both knowledge files; CRM calls were persisted in Onyx's native `tool_call` records; and the confirmation flow kept the task count unchanged at one for `confirmed=false`, then created task ID 2 for `confirmed=true`. The separate focused automated unit suite passed (`4 passed`). The CRM data is local deterministic demo data.
