"""create lead_validations table"""

from alembic import op
import sqlalchemy as sa

revision = "20260323_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_validations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("lead_id", sa.String(length=128), nullable=False),
        sa.Column("contact_phone_raw", sa.String(length=128), nullable=False),
        sa.Column("normalized_phone", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="deterministic"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_lead_validations_lead_id", "lead_validations", ["lead_id"])
    op.create_index("ix_lead_validations_status", "lead_validations", ["status"])
    op.create_index("ix_lead_validations_reason", "lead_validations", ["reason"])


def downgrade() -> None:
    op.drop_index("ix_lead_validations_reason", table_name="lead_validations")
    op.drop_index("ix_lead_validations_status", table_name="lead_validations")
    op.drop_index("ix_lead_validations_lead_id", table_name="lead_validations")
    op.drop_table("lead_validations")
