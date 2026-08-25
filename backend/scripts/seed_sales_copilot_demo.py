"""Seed deterministic Enterprise AI Sales Copilot demo data.

Run after `uv run alembic upgrade head`:
`uv run python backend/scripts/seed_sales_copilot_demo.py`.
"""

from datetime import date, datetime, timezone

from onyx.db.engine.sql_engine import SqlEngine, get_session_with_current_tenant
from onyx.db.models import SalesAccount, SalesActivity, SalesContact, SalesOpportunity, SalesProduct


ACCOUNTS = [
    ("星海科技", "制造", 3000, "华东", "IT 与 HR 知识咨询量高；正在评估企业 Agent 私有化 PoC。"),
    ("远航云", "SaaS", 850, "华北", "希望减少客户支持重复问答。"),
    ("华泰零售", "零售", 12000, "华东", "门店运营知识分散。"),
    ("瀚海银行", "金融", 18000, "华北", "重视数据隔离、审计和私有化部署。"),
    ("凌云芯片", "芯片/科技", 2200, "华南", "研发文档检索效率低。"),
    ("极光互联", "互联网", 5000, "华东", "客服和运维需要统一知识入口。"),
    ("新程物流", "制造", 4500, "华中", "希望优化一线运维 SOP 查询。"),
    ("青禾医药", "零售", 1600, "华南", "合规知识问答存在人工瓶颈。"),
]


def main() -> None:
    SqlEngine.init_engine(pool_size=5, max_overflow=2)
    with get_session_with_current_tenant() as session:
        if session.query(SalesAccount).count():
            print("Sales Copilot demo data already exists; no changes made.")
            return
        accounts = {}
        for name, industry, employees, region, notes in ACCOUNTS:
            account = SalesAccount(name=name, industry=industry, employee_count=employees, region=region, notes=notes)
            session.add(account)
            session.flush()
            accounts[name] = account
        session.add_all([
            SalesProduct(name="Onyx Enterprise Agent", edition="Enterprise", description="RAG、Agent、Tool Calling、权限和审计能力。"),
            SalesProduct(name="Onyx Private Deployment", edition="Enterprise", description="部署在客户 VPC 或私有基础设施内。"),
        ])
        xinghai = accounts["星海科技"]
        session.add_all([
            SalesContact(account_id=xinghai.id, name="陈航", title="CIO", email="chen.hang@example.demo"),
            SalesContact(account_id=xinghai.id, name="李晨", title="技术负责人", email="li.chen@example.demo"),
            SalesContact(account_id=xinghai.id, name="王敏", title="采购负责人", email="wang.min@example.demo"),
        ])
        opportunities = [
            (xinghai, "企业知识 Agent 项目", "PoC", 500000, "Onyx Enterprise Agent"),
            (accounts["瀚海银行"], "金融知识助手", "Discovery", 1200000, "Onyx Private Deployment"),
            (accounts["极光互联"], "客服 Agent 升级", "Proposal", 800000, "Onyx Enterprise Agent"),
            (accounts["凌云芯片"], "研发知识检索", "Qualification", 380000, "Onyx Enterprise Agent"),
            (accounts["远航云"], "支持中心自动化", "Negotiation", 260000, "Onyx Enterprise Agent"),
        ]
        created = []
        for account, name, stage, amount, product in opportunities:
            opportunity = SalesOpportunity(account_id=account.id, name=name, stage=stage, expected_revenue_rmb=amount, product_name=product, expected_close_date=date(2026, 10, 30))
            session.add(opportunity)
            created.append(opportunity)
        session.flush()
        xinghai_opportunity = created[0]
        session.add_all([
            SalesActivity(account_id=xinghai.id, opportunity_id=xinghai_opportunity.id, activity_type="discovery", summary="确认 IT 和 HR 每日重复知识咨询量大，要求数据不离开客户 VPC。", occurred_at=datetime(2026, 8, 5, tzinfo=timezone.utc)),
            SalesActivity(account_id=xinghai.id, opportunity_id=xinghai_opportunity.id, activity_type="demo", summary="演示 RAG 检索、引用与结构化 Tool Calling；客户要求制造业案例。", occurred_at=datetime(2026, 8, 15, tzinfo=timezone.utc)),
        ])
        session.commit()
        print("Seeded 8 accounts, 5 opportunities, products, contacts and activities.")


if __name__ == "__main__":
    main()
