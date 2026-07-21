# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""卡密生成 CLI：指定模型 + 时长/次数/token，一键出卡（走 admin API）。

用法:
  python scripts/gen_card.py <模型> [时长] [选项]

示例:
  python scripts/gen_card.py qwen_plus 24h              # 24小时, 20次, 1张
  python scripts/gen_card.py deepseek 7d -n 50          # 7天, 50次
  python scripts/gen_card.py qwen_plus 12h -n 5 -t 300k # 12小时5次, token封顶30万
  python scripts/gen_card.py doubao 30d -c 100 --ref 批次A  # 批量100张

时长单位: m(分) h(时) d(天) w(周)；裸数字按天。默认 1d。
配置(环境变量或 .env): PLATFORM_API_BASE(默认 http://127.0.0.1:7000/api), ADMIN_TOKEN
"""

import argparse
import os
import sys
import urllib.request
import json
from pathlib import Path


def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def parse_token(text: str) -> int:
    """'300k'/'2m'/'500000' → 整数。"""
    if not text:
        return 0
    text = text.strip().lower()
    mult = {"k": 1000, "m": 1000000}.get(text[-1])
    return int(float(text[:-1]) * mult) if mult else int(text)


def main():
    load_env()
    parser = argparse.ArgumentParser(
        description="生成卡密（模型 + 时长/次数/token）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例: python scripts/gen_card.py qwen_plus 24h -n 20",
    )
    parser.add_argument("model", help="模型 model_name 或 display_name（模糊匹配）")
    parser.add_argument(
        "duration", nargs="?", default="1d", help="有效期，如 24h/7d/12h，默认 1d"
    )
    parser.add_argument("-n", "--uses", type=int, default=20, help="使用次数，默认 20")
    parser.add_argument(
        "-t", "--token", default="0", help="token 上限，如 300k/2m，默认不限"
    )
    parser.add_argument("-c", "--count", type=int, default=1, help="生成数量，默认 1")
    parser.add_argument("--ref", default="", help="订单备注（闲鱼订单号/旺旺名）")
    parser.add_argument(
        "--api", default=os.getenv("PLATFORM_API_BASE", "http://127.0.0.1:7000/api")
    )
    parser.add_argument("--token-admin", default=os.getenv("ADMIN_TOKEN", ""))
    args = parser.parse_args()

    if not args.token_admin:
        sys.exit("错误：未设置 ADMIN_TOKEN（在 .env 或环境变量里配置）")

    payload = json.dumps(
        {
            "model": args.model,
            "duration": args.duration,
            "uses": args.uses,
            "token_reserve": parse_token(args.token),
            "count": args.count,
            "order_ref": args.ref,
        }
    ).encode()

    req = urllib.request.Request(
        f"{args.api.rstrip('/')}/admin/codes/quick",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Admin-Token": args.token_admin,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        detail = json.load(e).get("detail", e.reason)
        sys.exit(f"发卡失败 [{e.code}]: {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"连接失败: {e.reason}（检查 PLATFORM_API_BASE 与服务是否在跑）")

    tk = data["token_reserve"]
    print(
        f"\n✅ 已生成 {len(data['codes'])} 张卡密"
        f"  模型={data['model']}({data['model_name']})"
        f"  {data['uses']}次 / {data['duration']}"
        f"  token={'不限' if not tk else f'{tk:,}'}\n"
    )
    for c in data["codes"]:
        print(f"  {c}")
    print()


if __name__ == "__main__":
    main()
