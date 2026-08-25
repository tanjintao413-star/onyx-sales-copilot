# 5–10 minute demo

1. **RAG (1 min).** Ask Demo 1. Show citations from ingested knowledge and explain that Onyx performs retrieval.
2. **CRM analysis (1 min).** Ask Demo 2. Open the tool-call trace and show the read-only opportunity/pipeline request.
3. **Account intelligence (3 min).** Ask Demo 3. Explain the sequence: account → opportunity → activities → RAG case/security material → brief.
4. **Solution design and ROI (2 min).** Ask Demo 4, then use `POST /sales-copilot/roi`. Connect saved labor, deployment and PoC success metrics to a business decision.
5. **Action safety (2 min).** Ask Demo 5. Demonstrate a preview with `confirmed=false`, then ask for approval before sending `confirmed=true`. This is a UX convention backed by an API flag, not an independent HITL approval workflow.

Before the demo: run migration and seed; ingest `docs/sales_copilot_knowledge`; attach Search Tool 1 plus Custom Action 12 to Persona 1; configure a tool-capable LLM provider. The validated local setup uses `deepseek-v4-flash` through Onyx's OpenAI-compatible provider configuration.

For Demo 4, the ROI schema fields are `employee_count`, `average_salary`, `hours_saved_per_employee`, `automation_rate` and `software_cost`. `roi` is a multiple: a result of `107` means `107x` (10,700%), not 107%. For Demo 5, first call with `confirmed=false`, verify that no row was created, then approve and call the same operation with `confirmed=true`. The 2026-08-25 live run created follow-up task ID 2 only after approval. The CRM records are local deterministic demo data.
