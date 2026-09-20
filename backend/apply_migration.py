"""Apply migration directly without alembic config loading issues"""

import os

# Set DATABASE_URL BEFORE importing anything else
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://carloslott:fc100711@localhost:5433/med_appointment"
)

# Now import after setting env var
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def apply_migration():
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=True)
    async with engine.begin() as conn:
        # Create table
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS visual_indicator_config (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) NOT NULL UNIQUE,
                label VARCHAR(100) NOT NULL,
                hex_color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            );
            CREATE UNIQUE INDEX IF NOT EXISTS ix_visual_indicator_config_code
            ON visual_indicator_config (code);
        """)
        )
        # Seed data
        await conn.execute(
            text("""
            INSERT INTO visual_indicator_config (code, label, hex_color, sort_order, is_active)
            VALUES
                ('proximity_rank_1', 'Próxima cita (1er puesto)', '#10B981', 1, TRUE),
                ('proximity_rank_2', 'Próxima cita (2do puesto)', '#3B82F6', 2, TRUE),
                ('proximity_rank_3', 'Próxima cita (3er puesto)', '#F59E0B', 3, TRUE),
                ('delayed', 'Demorada', '#EF4444', 0, TRUE),
                ('pending', 'Pendiente', '#6B7280', 10, TRUE),
                ('confirmed', 'Confirmada', '#3B82F6', 5, TRUE),
                ('completed', 'Completada', '#10B981', 20, TRUE),
                ('cancelled', 'Cancelada', '#EF4444', 30, TRUE),
                ('rescheduled', 'Reagendada', '#F59E0B', 15, TRUE)
            ON CONFLICT (code) DO NOTHING;
        """)
        )

        # Verify
        result = await conn.execute(
            text(
                "SELECT code, label, hex_color, sort_order FROM visual_indicator_config ORDER BY sort_order"
            )
        )
        rows = result.fetchall()
        print("✅ Table created and seeded:")
        for row in rows:
            print(
                f"  {row.code}: {row.label} - {row.hex_color} (order: {row.sort_order})"
            )

    await conn.close()
    print("✅ Migration applied successfully!")


if __name__ == "__main__":
    asyncio.run(apply_migration())
