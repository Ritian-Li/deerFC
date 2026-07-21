#!/usr/bin/env bash
# git 部署：本地 push → 服务器 bare repo → checkout → 按变更重装/重构建 → 重启
# 说明：服务器连不上 GitHub，故用服务器上的 bare repo(/opt/deerflow.git) 作中转。
#   本地需要一个指向它的 remote：git remote add production 111.229.65.16:/opt/deerflow.git
#   GitHub(origin) 仅作代码托管，两边都 push 保持一致。
# 用法: bash scripts/deploy.sh  （在仓库根目录、main 分支、已 commit 的状态下执行）
set -euo pipefail

SERVER="${DEPLOY_SERVER:-111.229.65.16}"
APP_DIR="/opt/deerflow"
BRANCH="${DEPLOY_BRANCH:-main}"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "⚠️  有未提交的改动，先 commit 再部署"; exit 1
fi

echo "==> push 到 GitHub (origin/$BRANCH)"
git push origin "$BRANCH" || echo "（origin push 失败，继续部署）"

echo "==> push 到服务器 bare repo"
git push production "$BRANCH"

echo "==> 服务器拉取并部署"
ssh "$SERVER" bash -s <<REMOTE
set -euo pipefail
cd $APP_DIR
OLD=\$(git rev-parse HEAD 2>/dev/null || echo none)
git fetch origin $BRANCH
git reset --hard origin/$BRANCH
NEW=\$(git rev-parse HEAD)
echo "  \$OLD -> \$NEW"

if [[ "\$OLD" == none ]] || ! git diff --quiet "\$OLD" "\$NEW" -- requirements-platform.txt; then
  echo "==> python 依赖变更，重装"
  .venv/bin/pip install -q -i https://mirrors.cloud.tencent.com/pypi/simple -r requirements-platform.txt
fi

if [[ "\$OLD" == none ]] || ! git diff --quiet "\$OLD" "\$NEW" -- web/; then
  echo "==> 前端变更，重新构建"
  cd web
  pnpm install --silent
  NEXT_PUBLIC_API_URL=\$(grep ^NEXT_PUBLIC_API_URL $APP_DIR/.env | cut -d= -f2) pnpm build
  cd ..
  systemctl restart deerflow-frontend
fi

systemctl restart deerflow-backend
sleep 3
systemctl is-active deerflow-backend deerflow-frontend
curl -s -o /dev/null -w "health: %{http_code}\n" http://127.0.0.1:7000/api/auth/me
REMOTE
echo "==> 部署完成"
