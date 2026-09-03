"""Executable structural and mutation-boundary invariants for Sales Copilot."""

import ast
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from onyx.server.sales_copilot import api as sales_api
from onyx.server.sales_copilot.api import (
    CustomerActivityRequest,
    FollowUpTaskRequest,
    OpportunityStageRequest,
    add_sales_customer_activity,
    change_sales_opportunity_stage,
    create_sales_follow_up_task,
)


API_PATH = sales_api.__file__


def test_sales_routes_use_data_access_layer_and_authentication() -> None:
    assert API_PATH is not None
    source = Path(API_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == "onyx.db.sales_copilot" for alias in node.names}
    assert {"create_follow_up_task", "update_opportunity_stage", "add_customer_activity"}.issubset(imports)
    assert "Depends(current_user)" in source
    assert "SalesAccount" not in source
    assert "SalesOpportunity" not in source


def test_unconfirmed_mutations_do_not_touch_database() -> None:
    db_session = MagicMock()
    task = create_sales_follow_up_task(FollowUpTaskRequest(account_id=1, title="PoC follow-up", due_date=date(2026, 9, 4)), db_session)
    stage = change_sales_opportunity_stage(1, OpportunityStageRequest(stage="Closed Won"), db_session)
    activity = add_sales_customer_activity(CustomerActivityRequest(account_id=1, activity_type="call", summary="Follow-up call"), db_session)
    assert task["status"] == stage["status"] == activity["status"] == "confirmation_required"
    db_session.assert_not_called()
