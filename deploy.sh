#!/usr/bin/env bash
# 一键重新部署到 Cloudflare Pages（https://zucai.pages.dev）
# 用法：./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
cp index.html public/index.html
npx wrangler pages deploy public --project-name=zucai --branch=main --commit-dirty=true
echo "✅ 已部署 → https://zucai.pages.dev"
