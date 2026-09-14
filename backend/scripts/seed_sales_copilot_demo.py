"""Bootstrap the deterministic local Enterprise AI Sales Copilot demo.

Run after `uv run alembic upgrade head`:
`uv run python backend/scripts/seed_sales_copilot_demo.py`.

Besides CRM fixtures, this idempotently configures the requested local user through
Onyx's native Admin group, language preference, Persona, knowledge, and tool models.
"""

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from urllib.request import urlopen

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from onyx.db.engine.sql_engine import SqlEngine, get_session_with_current_tenant
from onyx.db.enums import SupportedLanguage
from onyx.db.models import (
    Document,
    Persona,
    SalesAccount,
    SalesActivity,
    SalesFollowUpTask,
    SalesOpportunity,
    SalesProduct,
    StarterMessage,
    Tool,
    UserFile,
)
from onyx.db.persona import upsert_persona
from onyx.db.tools import update_tool
from onyx.db.user_preferences import update_user_language
from onyx.db.users import get_user_by_email, set_user_admin_access
from onyx.server.features.tool.models import Header
from onyx.tools.models import CHAT_SESSION_ID_PLACEHOLDER, MESSAGE_ID_PLACEHOLDER
from onyx.tools.tool_implementations.custom.openapi_parsing import (
    validate_openapi_schema,
)

DEMO_ADMIN_EMAIL = "admin_user@example.com"
AGENT_NAME = "销售助手 · Sales Copilot"
AGENT_DESCRIPTION = (
    "面向企业销售与售前场景的 AI 助手，可结合 CRM 结构化数据与企业知识库分析客户、"
    "商机和销售活动，并给出有证据支持的下一步建议。"
)
AGENT_INSTRUCTIONS = """你是企业销售与售前助手。默认给出简洁、可执行的回答。

- CRM 客户、商机、活动和 Pipeline 查询只调用必要的 CRM 读工具。相互独立的读取放在同一轮并行调用。
- 纯 ROI 计算只调用 ROI 工具。除非问题还要求客户事实或文档证据，否则不调用 CRM 或 Search。
- 产品、部署、安全、Roadmap 或价格问题使用 Search，并为关键结论提供 Citation；需要客户背景时再并行调用 CRM。
- 仅当用户要求 Go/No-Go、PoC 去留、多部门冲突、Hard Blocker 或复杂 deal 决策时调用 Deal Council。普通 CRM 查询不得调用。
- 不得编造事实。分开写 Evidence（证据）与 Assessment（判断）；信息不足时明确说明。
- CRM 写操作必须先用 confirmed=false 获取服务端预览。只有用户在下一条消息中明确确认同一变更，才可提交 token 和 confirmed=true。
- 模型不得自行确认、在同一用户回合消费 token，或跨操作复用 token。Specialist 只能只读分析。
- 建议与已执行操作必须明确区分。Deal Council 需展示实际参与的 Sales、Product、Technical 和 Orchestrator 结论。
"""
STARTER_MESSAGES = [
    StarterMessage(
        name="商机分析",
        message="分析星海科技目前的商机情况，并给出下一步建议。",
    ),
    StarterMessage(
        name="优先跟进",
        message="帮我找出目前最值得优先跟进的客户和商机。",
    ),
    StarterMessage(
        name="会前 Brief",
        message="根据 CRM 数据和产品知识，为星海科技准备一份会前 Brief。",
    ),
    StarterMessage(
        name="PoC 评估",
        message="评估星海科技当前 PoC 是否值得继续推进。",
    ),
]
DEMO_KNOWLEDGE_TITLES = {
    "manufacturing_agent_case.md",
    "enterprise_agent_security.md",
}
BENCHMARK_KNOWLEDGE_TITLES = {
    "enterprise_agent_product_guide.md",
    "farvoyage_retail_pilot_notes.md",
    "huabei_energy_rfp_excerpt.md",
    "legacy_private_deployment_2025_DEPRECATED.md",
    "pricing_reference_2026.md",
    "private_deployment_guide.md",
    "roadmap_2026q4.md",
    "security_audit_pack.md",
    "sso_rbac_guide.md",
    "xinghai_suzhou_brief.md",
    "xinghai_tech_account_brief.md",
    "yunqiao_finance_security_requirements.md",
    "zhiyuan_medical_requirements.md",
}
DEFAULT_OPENAPI_URL = "http://localhost:8080/openapi.json"
CRM_SEED_SPEC_PATH = (
    Path(__file__).resolve().parents[2]
    / "demo_benchmark"
    / "onyx_sales_demo_benchmark_v1"
    / "crm_seed_spec.json"
)


def _load_crm_seed_spec() -> dict[str, list[dict[str, object]]]:
    with CRM_SEED_SPEC_PATH.open(encoding="utf-8") as spec_file:
        return json.load(spec_file)


def _seed_crm_data(session: Session) -> dict[str, int]:
    """Upsert benchmark CRM rows without using its illustrative database IDs."""
    spec = _load_crm_seed_spec()
    created = {
        name: 0 for name in ("accounts", "opportunities", "activities", "products")
    }

    accounts_by_spec_id: dict[int, SalesAccount] = {}
    seen_account_names: set[str] = set()
    for row in spec["accounts"]:
        spec_id = int(row["id"])
        name = str(row["name"])
        if name in seen_account_names or spec_id in accounts_by_spec_id:
            raise ValueError("CRM seed spec contains duplicate account keys.")
        seen_account_names.add(name)
        account = session.scalar(select(SalesAccount).where(SalesAccount.name == name))
        if account is None:
            account = SalesAccount(
                name=name,
                industry=str(row["industry"]),
                employee_count=int(row["employee_count"]),
                region=str(row["region"]),
                notes=str(row["notes"]),
            )
            session.add(account)
            session.flush()
            created["accounts"] += 1
        else:
            account.industry = str(row["industry"])
            account.employee_count = int(row["employee_count"])
            account.region = str(row["region"])
            account.notes = str(row["notes"])
        accounts_by_spec_id[spec_id] = account

    opportunities_by_spec_id: dict[int, SalesOpportunity] = {}
    seen_opportunity_keys: set[tuple[int, str]] = set()
    for row in spec["opportunities"]:
        spec_id = int(row["id"])
        account = accounts_by_spec_id[int(row["account_id"])]
        name = str(row["name"])
        key = (account.id, name)
        if key in seen_opportunity_keys or spec_id in opportunities_by_spec_id:
            raise ValueError("CRM seed spec contains duplicate opportunity keys.")
        seen_opportunity_keys.add(key)
        opportunity = session.scalar(
            select(SalesOpportunity).where(
                SalesOpportunity.account_id == account.id,
                SalesOpportunity.name == name,
            )
        )
        if opportunity is None:
            opportunity = SalesOpportunity(account_id=account.id, name=name)
            session.add(opportunity)
            created["opportunities"] += 1
        opportunity.stage = str(row["stage"])
        opportunity.expected_revenue_rmb = float(row["expected_revenue_rmb"])
        opportunity.product_name = str(row["product_name"])
        opportunity.expected_close_date = date.fromisoformat(
            str(row["expected_close_date"])
        )
        session.flush()
        opportunities_by_spec_id[spec_id] = opportunity

    seen_activity_keys: set[tuple[int, int, str, str, datetime]] = set()
    for row in spec["activities"]:
        account = accounts_by_spec_id[int(row["account_id"])]
        opportunity = opportunities_by_spec_id[int(row["opportunity_id"])]
        occurred_at = datetime.fromisoformat(str(row["occurred_at"]))
        activity_type = str(row["activity_type"])
        summary = str(row["summary"])
        key = (account.id, opportunity.id, activity_type, summary, occurred_at)
        if key in seen_activity_keys:
            raise ValueError("CRM seed spec contains duplicate activity keys.")
        seen_activity_keys.add(key)
        activity = session.scalar(
            select(SalesActivity).where(
                SalesActivity.account_id == account.id,
                SalesActivity.opportunity_id == opportunity.id,
                SalesActivity.activity_type == activity_type,
                SalesActivity.summary == summary,
                SalesActivity.occurred_at == occurred_at,
            )
        )
        if activity is None:
            session.add(
                SalesActivity(
                    account_id=account.id,
                    opportunity_id=opportunity.id,
                    activity_type=activity_type,
                    summary=summary,
                    occurred_at=occurred_at,
                )
            )
            created["activities"] += 1

    seen_product_names: set[str] = set()
    for row in spec["products"]:
        name = str(row["name"])
        if name in seen_product_names:
            raise ValueError("CRM seed spec contains duplicate product keys.")
        seen_product_names.add(name)
        product = session.scalar(select(SalesProduct).where(SalesProduct.name == name))
        if product is None:
            product = SalesProduct(name=name)
            session.add(product)
            created["products"] += 1
        product.edition = str(row["edition"])
        product.description = str(row["description"])

    session.commit()
    return created


def _reset_benchmark_state(session: Session) -> dict[str, int]:
    """Remove mutable demo rows for accounts managed by the CRM seed spec."""
    spec = _load_crm_seed_spec()
    account_names = {str(row["name"]) for row in spec["accounts"]}
    benchmark_account_ids = list(
        session.scalars(
            select(SalesAccount.id).where(SalesAccount.name.in_(account_names))
        )
    )
    if not benchmark_account_ids:
        return {"activities": 0, "follow_up_tasks": 0}

    activities = session.execute(
        delete(SalesActivity).where(
            SalesActivity.account_id.in_(benchmark_account_ids)
        )
    )
    tasks = session.execute(
        delete(SalesFollowUpTask).where(
            SalesFollowUpTask.account_id.in_(benchmark_account_ids)
        )
    )
    session.commit()
    return {
        "activities": activities.rowcount or 0,
        "follow_up_tasks": tasks.rowcount or 0,
    }


def _refresh_sales_action_schema(
    session: Session, tool: Tool, openapi_url: str
) -> None:
    """Refresh only Sales paths while preserving the Action's auth/server config."""
    if tool.openapi_schema is None:
        raise RuntimeError("Sales Custom Action 12 has no OpenAPI definition.")

    with urlopen(openapi_url, timeout=10) as response:  # noqa: S310 - local CLI input
        live_schema = json.load(response)

    live_sales_paths = {
        path: definition
        for path, definition in live_schema.get("paths", {}).items()
        if path.startswith("/sales-copilot")
    }
    if "/sales-copilot/deal-council" not in live_sales_paths:
        raise RuntimeError("The live Sales API does not expose Deal Council.")

    refreshed_schema = dict(tool.openapi_schema)
    refreshed_schema["paths"] = live_sales_paths
    refreshed_components = dict(refreshed_schema.get("components", {}))
    refreshed_components["schemas"] = live_schema.get("components", {}).get(
        "schemas", {}
    )
    refreshed_schema["components"] = refreshed_components
    validate_openapi_schema(refreshed_schema)
    update_tool(
        tool_id=tool.id,
        name=tool.name,
        description=tool.description,
        openapi_schema=refreshed_schema,
        custom_headers=[
            Header(
                key="X-Onyx-Chat-Session-ID",
                value=CHAT_SESSION_ID_PLACEHOLDER,
            ),
            Header(
                key="X-Onyx-User-Message-ID",
                value=MESSAGE_ID_PLACEHOLDER,
            ),
        ],
        user_id=tool.user_id,
        db_session=session,
        passthrough_auth=None,
    )


def _configure_demo_user_and_agent(
    session: Session, admin_email: str, openapi_url: str
) -> int:
    user = get_user_by_email(admin_email, session)
    if user is None:
        raise RuntimeError(
            f"Local demo user {admin_email!r} does not exist; register it first."
        )

    # This is the same native group-membership path used by the admin management API.
    set_user_admin_access(session, actor=user, target=user, is_admin=True)
    session.refresh(user)
    # This CE checkout only supports en/es/pt/fr/de as UI locales. Keep the
    # stored preference valid; the Sales-specific Agent experience is Chinese.
    update_user_language(user.id, SupportedLanguage.EN.value, session)

    persona = (
        session.query(Persona)
        .filter(or_(Persona.name == AGENT_NAME, Persona.name == "Sales Copilot"))
        .order_by(Persona.id)
        .first()
    )
    tools = session.query(Tool).filter(Tool.id.in_([1, 12])).all()
    tool_ids = {tool.id for tool in tools}
    if tool_ids != {1, 12}:
        raise RuntimeError("Expected Search Tool 1 and Sales Custom Action 12.")
    sales_action = next(tool for tool in tools if tool.id == 12)
    _refresh_sales_action_schema(session, sales_action, openapi_url)

    knowledge_documents = (
        session.query(Document)
        .filter(Document.semantic_id.in_(DEMO_KNOWLEDGE_TITLES))
        .all()
    )
    if {
        document.semantic_id for document in knowledge_documents
    } != DEMO_KNOWLEDGE_TITLES:
        raise RuntimeError("Expected indexed Sales Copilot knowledge documents.")

    benchmark_files = (
        session.query(UserFile)
        .filter(
            UserFile.user_id == user.id,
            UserFile.name.in_(BENCHMARK_KNOWLEDGE_TITLES),
        )
        .all()
    )
    benchmark_titles = {user_file.name for user_file in benchmark_files}
    use_benchmark_scope = benchmark_titles == BENCHMARK_KNOWLEDGE_TITLES

    configured = upsert_persona(
        persona_id=persona.id if persona else None,
        user=user,
        db_session=session,
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        starter_messages=STARTER_MESSAGES,
        system_prompt=AGENT_INSTRUCTIONS,
        task_prompt="",
        datetime_aware=True,
        is_public=True,
        default_model_configuration_id=(
            persona.default_model_configuration_id if persona else None
        ),
        document_set_ids=[],
        tool_ids=sorted(tool_ids),
        user_file_ids=(
            [user_file.id for user_file in benchmark_files]
            if use_benchmark_scope
            else []
        ),
        document_ids=(
            []
            if use_benchmark_scope
            else [document.id for document in knowledge_documents]
        ),
        commit=True,
    )
    return configured.id


def main(
    *,
    configure_onyx: bool = False,
    reset_benchmark_state: bool = False,
    admin_email: str = DEMO_ADMIN_EMAIL,
    openapi_url: str = DEFAULT_OPENAPI_URL,
) -> None:
    """Seed deterministic CRM data and optionally configure the local Onyx demo.

    Integration fixtures import this function and intentionally seed only CRM data.
    Direct script execution performs the complete local demo bootstrap.
    """
    SqlEngine.set_app_name("seed_sales_copilot_demo")
    SqlEngine.init_engine(pool_size=5, max_overflow=2)
    with get_session_with_current_tenant() as session:
        reset = (
            _reset_benchmark_state(session) if reset_benchmark_state else None
        )
        crm_created = _seed_crm_data(session)
        if reset is not None:
            print(f"Benchmark state reset: removed={reset}, seeded={crm_created}.")
        if not configure_onyx:
            return

        persona_id = _configure_demo_user_and_agent(session, admin_email, openapi_url)
        print(
            f"Sales Copilot demo ready: created={crm_created}, persona_id={persona_id}."
        )


def _run_cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", default=DEMO_ADMIN_EMAIL)
    parser.add_argument("--openapi-url", default=DEFAULT_OPENAPI_URL)
    parser.add_argument(
        "--crm-only",
        action="store_true",
        help="Import only benchmark CRM rows; leave Onyx user/Agent configuration unchanged.",
    )
    parser.add_argument(
        "--reset-benchmark-state",
        action="store_true",
        help="Restore only CRM rows managed by crm_seed_spec.json; do not configure Onyx.",
    )
    args = parser.parse_args()
    main(
        configure_onyx=not args.crm_only and not args.reset_benchmark_state,
        reset_benchmark_state=args.reset_benchmark_state,
        admin_email=args.admin_email,
        openapi_url=args.openapi_url,
    )


if __name__ == "__main__":
    _run_cli()
