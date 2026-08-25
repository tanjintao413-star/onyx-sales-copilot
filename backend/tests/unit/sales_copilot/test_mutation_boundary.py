from datetime import date

from onyx.server.sales_copilot.api import FollowUpTaskRequest


def test_follow_up_request_defaults_to_unconfirmed() -> None:
    request = FollowUpTaskRequest(account_id=1, title="PoC follow-up", due_date=date(2026, 8, 31))
    assert request.confirmed is False
