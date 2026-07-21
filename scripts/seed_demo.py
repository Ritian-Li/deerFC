# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""初始化演示数据：一个模型、两个套餐、各两张卡密。

用法: .venv/bin/python scripts/seed_demo.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.platform.db import SessionLocal, init_db  # noqa: E402
from src.platform.models import (  # noqa: E402
    ActivationCode,
    ModelEntry,
    Plan,
    generate_card_code,
)


async def main():
    await init_db()
    async with SessionLocal() as session:
        model = ModelEntry(
            display_name="DeepSeek-V3（火山方舟）",
            model_name="deepseek-v3-250324",
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key_env="VOLCENGINE_ARK_API_KEY",
            provider="火山方舟",
        )
        session.add(model)
        trial = Plan(name="体验卡 3次/7天", total_uses=3, valid_days=7)
        standard = Plan(name="标准卡 20次/30天", total_uses=20, valid_days=30)
        session.add_all([trial, standard])
        await session.flush()

        codes = []
        for plan in (trial, standard):
            for _ in range(2):
                code = generate_card_code()
                session.add(
                    ActivationCode(
                        code=code,
                        plan_id=plan.id,
                        model_id=model.id,
                        order_ref="seed-demo",
                    )
                )
                codes.append((plan.name, code))
        await session.commit()

    print("演示数据已创建：")
    for plan_name, code in codes:
        print(f"  [{plan_name}] {code}")


if __name__ == "__main__":
    asyncio.run(main())
