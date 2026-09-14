"""Executable structural and mutation-boundary invariants for Sales Copilot."""

import ast
import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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
CHAT_SESSION_ID = "00000000-0000-0000-0000-000000000010"
USER_MESSAGE_ID = 10


def test_sales_routes_use_data_access_layer_and_authentication() -> None:
    assert API_PATH is not None
    source = Path(API_PATH).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "onyx.db.sales_copilot"
        for alias in node.names
    }
    assert {
        "create_follow_up_task",
        "update_opportunity_stage",
        "add_customer_activity",
    }.issubset(imports)
    assert "Depends(current_user)" in source
    assert "SalesAccount" not in source
    assert "SalesOpportunity" not in source


def test_unconfirmed_mutations_do_not_touch_database() -> None:
    db_session = MagicMock()
    user = MagicMock(id="00000000-0000-0000-0000-000000000001")
    redis = MagicMock()
    with patch.object(sales_api, "get_redis_client", return_value=redis):
        task = create_sales_follow_up_task(
            FollowUpTaskRequest(
                account_id=1, title="PoC follow-up", due_date=date(2026, 9, 4)
            ),
            user,
            db_session,
            CHAT_SESSION_ID,
            USER_MESSAGE_ID,
        )
        stage = change_sales_opportunity_stage(
            1,
            OpportunityStageRequest(stage="Closed Won"),
            user,
            db_session,
            CHAT_SESSION_ID,
            USER_MESSAGE_ID,
        )
        activity = add_sales_customer_activity(
            CustomerActivityRequest(
                account_id=1, activity_type="call", summary="Follow-up call"
            ),
            user,
            db_session,
            CHAT_SESSION_ID,
            USER_MESSAGE_ID,
        )
    assert (
        task["status"]
        == stage["status"]
        == activity["status"]
        == "confirmation_required"
    )
    db_session.assert_not_called()


def test_confirmed_mutation_requires_token() -> None:
    user = MagicMock(id="00000000-0000-0000-0000-000000000001")
    redis = MagicMock()
    redis.get.return_value = None
    with patch.object(sales_api, "get_redis_client", return_value=redis):
        with pytest.raises(Exception, match="valid confirmation_token"):
            sales_api._consume_confirmation(
                "create_follow_up_task",
                user,
                {},
                None,
                CHAT_SESSION_ID,
                USER_MESSAGE_ID,
                MagicMock(),
            )


def test_same_user_turn_cannot_consume_preview_ticket() -> None:
    user = MagicMock(id="00000000-0000-0000-0000-000000000001")
    values = {
        "account_id": 1,
        "opportunity_id": 1,
        "title": "PoC follow-up",
        "due_date": "2026-09-04",
    }
    redis = MagicMock()
    with (
        patch.object(sales_api, "get_redis_client", return_value=redis),
        patch.object(sales_api, "is_explicit_confirmation_turn", return_value=False),
    ):
        preview = sales_api._preview_confirmation(
            "create_follow_up_task",
            user,
            values,
            CHAT_SESSION_ID,
            USER_MESSAGE_ID,
        )
        redis.get.return_value = redis.set.call_args_list[0].args[1]
        with pytest.raises(Exception, match="subsequent user message"):
            sales_api._consume_confirmation(
                "create_follow_up_task",
                user,
                values,
                str(preview["confirmation_token"]),
                CHAT_SESSION_ID,
                USER_MESSAGE_ID,
                MagicMock(),
            )
    record = json.loads(redis.set.call_args_list[0].args[1])
    assert record["preview_user_message_id"] == USER_MESSAGE_ID
    redis.getdel.assert_not_called()


def test_next_turn_can_resolve_exact_preview_without_exposing_ticket() -> None:
    user = MagicMock(id="00000000-0000-0000-0000-000000000001")
    values = {"account_id": 1, "title": "PoC follow-up", "due_date": "2026-09-04"}
    redis = MagicMock()
    with (
        patch.object(sales_api, "get_redis_client", return_value=redis),
        patch.object(sales_api, "is_explicit_confirmation_turn", return_value=True),
    ):
        preview = sales_api._preview_confirmation(
            "create_follow_up_task", user, values, CHAT_SESSION_ID, USER_MESSAGE_ID
        )
        redis.get.side_effect = [
            preview["confirmation_token"],
            redis.set.call_args_list[0].args[1],
        ]
        redis.getdel.return_value = redis.set.call_args_list[0].args[1]
        sales_api._consume_confirmation(
            "create_follow_up_task",
            user,
            values,
            None,
            CHAT_SESSION_ID,
            USER_MESSAGE_ID + 1,
            MagicMock(),
        )
    redis.delete.assert_called_once()


def test_follow_up_request_accepts_legacy_opportunity_alias() -> None:
    body = FollowUpTaskRequest.model_validate(
        {
            "account_id": 1,
            "related_opportunity_id": 7,
            "title": "PoC follow-up",
            "due_date": "2026-09-04",
        }
    )
    assert body.opportunity_id == 7
