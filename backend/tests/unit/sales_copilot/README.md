# Sales Copilot tests

- `test_roi.py` checks transparent financial arithmetic.
- `test_mutation_boundary.py` checks that writes default to unconfirmed.
- `test_request_validation.py` checks invalid business inputs.

These are automated unit tests only. Database read/mutation behavior must be exercised separately through live end-to-end validation after migration and seeding. Required checks: account-not-found → `OnyxError`, read tools do not mutate, confirmed task/activity creation persists, and a confirmed stage update persists. `confirmed` is a model-callable guard, not independent HITL approval.
