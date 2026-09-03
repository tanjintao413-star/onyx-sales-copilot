# Sales Copilot Evals

`evals/sales_copilot/cases.yaml` defines RAG citation, CRM pipeline, account brief, ROI, mutation preview, and confirmed mutation scenarios.

The graders are deterministic. They inspect normalized tool names, structured citations, Sales table snapshots, and required facts. They do not compare full natural-language answers.

Run `make sales-harness-fast` for static and unit checks. Run `make sales-harness-integration` with the official PostgreSQL-backed test environment. Run `make sales-harness-live` only when a configured provider and Agent trace are available. The live result is optional and reports `SKIPPED_EXTERNAL` when unavailable.

Add a case by adding a stable id, category, required tool groups, expected facts, and expected database effects. Do not make live LLM wording the only oracle.

The Deal Council checks routing, common assessment schema, provenance, hard
blockers, one-round conflict handling, and PostgreSQL mutation safety. Run
`make sales-harness-multi-agent` for the focused deterministic Council suite.
The ordinary Harness targets include these checks and retain all V1 checks.
