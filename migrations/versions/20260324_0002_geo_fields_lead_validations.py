"""add geo / IP context columns to lead_validations"""

import sqlalchemy as sa
from alembic import op

revision = "20260324_0002"
down_revision = "20260323_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lead_validations", sa.Column("client_ip", sa.String(length=45), nullable=True))
    op.add_column("lead_validations", sa.Column("ip_country", sa.String(length=2), nullable=True))
    op.add_column("lead_validations", sa.Column("assumed_dial_cc", sa.String(length=8), nullable=True))
    op.add_column(
        "lead_validations",
        sa.Column("geo_mismatch", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "lead_validations",
        sa.Column(
            "validation_confidence",
            sa.String(length=32),
            nullable=False,
            server_default="deterministic",
        ),
    )
    op.add_column(
        "lead_validations",
        sa.Column("default_cc_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("lead_validations", "default_cc_applied")
    op.drop_column("lead_validations", "validation_confidence")
    op.drop_column("lead_validations", "geo_mismatch")
    op.drop_column("lead_validations", "assumed_dial_cc")
    op.drop_column("lead_validations", "ip_country")
    op.drop_column("lead_validations", "client_ip")
