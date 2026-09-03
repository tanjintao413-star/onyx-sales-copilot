# Sales Copilot Architecture

The Sales Copilot uses Onyx Agent and Search capabilities. This project adds the Sales path below.

```text
LLM → Onyx Agent → Search Tool → OpenSearch → citation metadata
                 └→ Sales Custom Action → FastAPI → Sales data access layer → SQLAlchemy → PostgreSQL
```

Sales routes live in `backend/onyx/server/sales_copilot/api.py`. Database operations live in `backend/onyx/db/sales_copilot.py`.

The CRM tables are isolated as `sales_*` tables. The seed script creates deterministic local demo data.
