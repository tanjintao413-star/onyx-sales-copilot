# Sales Copilot Invariants

- **INV-001:** A Sales mutation with `confirmed=false` does not modify the database.
- **INV-002:** A Sales read request does not modify Sales tables.
- **INV-003:** Sales routes use the existing `current_user` authentication boundary.
- **INV-004:** Sales route business operations use the Sales data access layer.
- **INV-005:** Citation checks use structured source metadata.
- **INV-006:** The Sales seed produces deterministic CRM expectations.

The confirmation field and ticket are model-callable. The server accepts the
ticket only from the next explicit user-confirmation message in the same chat
branch. A model cannot preview and consume a ticket in one user turn. This is a
Sales mutation guard, not a general approval-workflow system.

## Multi-Agent Deal Council

- **MA-INV-001:** Specialists are read-only.
- **MA-INV-002:** Routing selects only required specialists.
- **MA-INV-003:** A hard blocker prevents unconditional `go`.
- **MA-INV-004:** Evidence has a source and source type.
- **MA-INV-005:** Conflict resolution has one round at most.
- **MA-INV-006:** The Council returns proposals. It cannot execute CRM mutations.
- **MA-INV-007:** Final synthesis uses typed assessments, not concatenated essays.
- **MA-INV-008:** Sales Harness V1 remains part of the deterministic Harness.
