"""Add Enterprise AI Sales Copilot demo CRM tables.

Revision ID: 9a10b11c12d1
Revises: 28bb08137807
"""

from alembic import op
import sqlalchemy as sa

revision = "9a10b11c12d1"
down_revision = "28bb08137807"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("sales_account", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(255), nullable=False, unique=True), sa.Column("industry", sa.String(100), nullable=False), sa.Column("employee_count", sa.Integer(), nullable=False), sa.Column("region", sa.String(100), nullable=False), sa.Column("notes", sa.Text(), nullable=True))
    op.create_table("sales_product", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(150), nullable=False, unique=True), sa.Column("edition", sa.String(100), nullable=False), sa.Column("description", sa.Text(), nullable=False))
    op.create_table("sales_contact", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("account_id", sa.Integer(), sa.ForeignKey("sales_account.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("title", sa.String(150), nullable=False), sa.Column("email", sa.String(255), nullable=False))
    op.create_table("sales_opportunity", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("account_id", sa.Integer(), sa.ForeignKey("sales_account.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("stage", sa.String(50), nullable=False), sa.Column("expected_revenue_rmb", sa.Numeric(14, 2), nullable=False), sa.Column("product_name", sa.String(150), nullable=False), sa.Column("expected_close_date", sa.Date(), nullable=True))
    op.create_table("sales_activity", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("account_id", sa.Integer(), sa.ForeignKey("sales_account.id", ondelete="CASCADE"), nullable=False), sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("sales_opportunity.id", ondelete="SET NULL"), nullable=True), sa.Column("activity_type", sa.String(50), nullable=False), sa.Column("summary", sa.Text(), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("sales_follow_up_task", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("account_id", sa.Integer(), sa.ForeignKey("sales_account.id", ondelete="CASCADE"), nullable=False), sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("sales_opportunity.id", ondelete="SET NULL"), nullable=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("due_date", sa.Date(), nullable=False), sa.Column("status", sa.String(50), nullable=False, server_default="open"))


def downgrade() -> None:
    for table in ("sales_follow_up_task", "sales_activity", "sales_opportunity", "sales_contact", "sales_product", "sales_account"):
        op.drop_table(table)
