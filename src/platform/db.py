# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def get_database_url() -> str:
    return os.getenv(
        "PLATFORM_DATABASE_URL", "sqlite+aiosqlite:///./deerflow_platform.db"
    )


def is_postgres() -> bool:
    return get_database_url().startswith("postgresql")


engine = create_async_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from src.platform.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
