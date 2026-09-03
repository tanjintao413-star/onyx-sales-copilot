# Sales Copilot Invariants

- **INV-001:** A Sales mutation with `confirmed=false` does not modify the database.
- **INV-002:** A Sales read request does not modify Sales tables.
- **INV-003:** Sales routes use the existing `current_user` authentication boundary.
- **INV-004:** Sales route business operations use the Sales data access layer.
- **INV-005:** Citation checks use structured source metadata.
- **INV-006:** The Sales seed produces deterministic CRM expectations.

The confirmation field is model-callable. It is not an independent human-in-the-loop approval system.
