#!/usr/bin/env bash
# 本机定时自动刷新体彩开奖数据 → 提交 → 部署。由 launchd 定时调用（见 scripts/com.zucai.autorefresh.plist）。
# 手动试跑（不落盘只报告）：scripts/auto-refresh.sh --check
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
REPO="$(pwd)"

# launchd 的 PATH 很裸，显式补齐 node/npx/git/python
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

mkdir -p .wrangler
LOG="$REPO/.wrangler/auto-refresh.log"
say(){ echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }

if [ "${1:-}" = "--check" ]; then
  python3 scripts/refresh_data.py --check; exit $?
fi

say "===== 自动刷新开始 ====="
python3 scripts/refresh_data.py >>"$LOG" 2>&1
code=$?
if [ $code -eq 3 ]; then say "已是最新，无改动，跳过部署。"; exit 0; fi
if [ $code -ne 0 ]; then say "刷新失败 (code=$code)，跳过部署。见日志。"; exit 1; fi

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo excel-twin)"
git add index.html public/index.html table.html public/table.html table-zfc.html public/table-zfc.html 2>>"$LOG"
if git commit -m "自动刷新开奖数据 $(date '+%Y-%m-%d %H:%M')" >>"$LOG" 2>&1; then
  say "已提交数据更新到 $BRANCH。"
  git push origin "$BRANCH" >>"$LOG" 2>&1 && say "已推送 GitHub。" || say "push 失败（keychain 锁定？可稍后手动 push），继续部署。"
else
  say "无 git 变更可提交（可能仅 public 镜像差异），继续部署。"
fi

if ./deploy.sh >>"$LOG" 2>&1; then
  say "已部署 → https://zucai.pages.dev"
else
  say "部署失败，见日志（wrangler 可能需重新登录）。"; exit 1
fi
say "===== 完成 ====="
