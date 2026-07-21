# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""清理过期产物文件：删除 N 天前的 run 文件并置空 file_path。

crontab 示例（每天 5 点，保留 30 天）: 0 5 * * * /path/.venv/bin/python scripts/cleanup_files.py 30
"""

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from src.platform.db import SessionLocal  # noqa: E402
from src.platform.models import Run, utcnow  # noqa: E402


async def main(keep_days: int):
    cutoff = utcnow() - timedelta(days=keep_days)
    removed = 0
    async with SessionLocal() as session:
        result = await session.execute(
            select(Run).where(Run.file_path != "", Run.created_at < cutoff)
        )
        for run in result.scalars():
            if run.file_path and os.path.exists(run.file_path):
                os.remove(run.file_path)
                removed += 1
            run.file_path = ""
        await session.commit()
    print(f"cleaned {removed} files older than {keep_days} days")


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    asyncio.run(main(days))
