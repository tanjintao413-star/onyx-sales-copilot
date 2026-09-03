# Sales Copilot Architecture

The Sales Copilot uses Onyx Agent and Search capabilities. This project adds the Sales path below.

```text
LLM → Onyx Agent → Search Tool → OpenSearch → citation metadata
                 └→ Sales Custom Action → FastAPI → Sales data access layer → SQLAlchemy → PostgreSQL
```

Sales routes live in `backend/onyx/server/sales_copilot/api.py`. Database operations live in `backend/onyx/db/sales_copilot.py`.

The CRM tables are isolated as `sales_*` tables. The seed script creates deterministic local demo data.

## Multi-Agent Deal Council V1

```text
User → Deal Council API / Custom Action → Decision Orchestrator
                                      ├→ Sales specialist → CRM reads
                                      ├→ Product specialist → product catalog reads
                                      └→ Technical specialist → documented evidence metadata
                                              ↓
                                  conflict detection → one resolution round maximum
                                              ↓
                              typed decision + action proposals (no execution)
```

The Council is request-scoped in `backend/onyx/sales_copilot/deal_council/`.
It does not replace Onyx Agent, ToolRunner, Search Tool, or Custom Actions.
The existing Custom Action can call `POST /sales-copilot/deal-council`.

Sales can read CRM data only. Product can read product data only. Technical
returns document provenance for technical claims. No specialist imports a CRM
mutation function. The Council only returns action proposals. Existing mutation
endpoints keep the separate `confirmed=true` guard.

The deterministic V1 uses structured product and CRM data. It records document
provenance for technical claims without an OpenSearch dependency. A configured
Onyx Agent can still use its native Search Tool for live RAG and citations.
