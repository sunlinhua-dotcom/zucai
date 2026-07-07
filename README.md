# 足彩预约购买 · 选号投注

中国体育彩票（足彩）移动端选号投注小工具。纯前端单文件、离线可用、数据存在本机浏览器（localStorage）。

**线上地址：** https://zucai.pages.dev

## 玩法

- **胜负彩（14场）** — 每场选 胜(3)/平(1)/负(0)，复式注数 = 各场选项数连乘
- **任选九** — 14 场中至少选 9 场，注数 = 9 次基本对称式 e₉（非简单连乘）
- **6场半全场** — 每场选 半场×全场（共 9 种），注数连乘
- **4场进球彩** — 每场选 主队/客队进球数（0/1/2/3+），注数连乘
- **比分表** — 比分 → 胜平负 速查矩阵，按总进球归档
- **复式 / 容错计算器** — 4 场进球专用：按位置（1–4 覆盖）或按容错档位（汉明球 ΣC(8,k)·3ᵏ）估算注数与金额
- **预约购买 → 购买记录 → 开奖核对** 全流程

单注 2 元。理性购彩。

## 部署（Cloudflare Pages）

静态站点，构建输出目录 `public/`，无需构建命令。

- 一键：`./deploy.sh`（内部走 `wrangler pages deploy public`）
- 或连接本仓库到 Cloudflare Pages（原生 Git 集成），推送 `main` 自动部署。

源码：`index.html`（部署副本 `public/index.html`）。

## 实时数据 / 自动刷新

生产环境的 Cloudflare 边缘节点**无法直连**中国体彩 `.cn` 接口（跨境受限），线上以内置快照兜底。要让快照自动跟上最新开奖，在**能直连体彩的本机**上装定时任务：

```bash
# 手动刷新一次（拉体彩→更新快照/走势表→同步 public）
python3 scripts/refresh_data.py            # 加 --check 只预览不落盘

# 装本机定时任务（每天 10:00 / 23:00 自动 刷新+提交+部署）
cp scripts/com.zucai.autorefresh.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.zucai.autorefresh.plist
launchctl start com.zucai.autorefresh      # 可选：立即跑一次
# 卸载：launchctl unload ~/Library/LaunchAgents/com.zucai.autorefresh.plist

# 日志：.wrangler/auto-refresh.log
```

只在本机开机联网时更新。`refresh_data.py` 只改数据（JQC/ZFC 快照、两张走势表 ROWS、Elo 随 latest 一起滚动），不碰算法。
