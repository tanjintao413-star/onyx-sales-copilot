from datetime import date

import pytest
from pydantic import ValidationError

from onyx.server.sales_copilot.api import FollowUpTaskRequest, RoiRequest


def test_roi_rejects_invalid_automation_rate() -> None:
    with pytest.raises(ValidationError):
        RoiRequest(employee_count=10, average_salary=1, hours_saved_per_employee=1, automation_rate=2, software_cost=1)


def test_follow_up_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        FollowUpTaskRequest(account_id=1, title="", due_date=date(2026, 8, 31))
