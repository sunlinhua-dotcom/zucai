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

生产环境的 Cloudflare 边缘节点**无法直连**中国体彩 `.cn` 接口（跨境受限），线上以内置快照兜底。要让快照跟上最新开奖，在**能直连体彩的本机**上刷新——两种用法：

**① 手动一行（零门槛，推荐日常用）** —— 开奖后跑一次，自动 刷新→提交→push→部署：

```bash
bash scripts/auto-refresh.sh              # 全自动：拉体彩→更新快照/走势表/Elo→提交→部署
bash scripts/auto-refresh.sh --check      # 只预览会改什么，不落盘不部署
python3 scripts/refresh_data.py           # 只刷数据、不提交不部署（更细）
```

**② launchd 无人值守（每天 10:00 / 23:00 自动跑）** —— ⚠️ 本仓库在 `/Volumes` 外置卷上，macOS **TCC 会拒绝后台任务访问外置卷**（实测读/写/执行全 `Operation not permitted`）。所以必须先给 `/bin/bash` 授「完全磁盘访问权限」，launchd 才跑得动：

```
1) 系统设置 → 隐私与安全性 → 完全磁盘访问权限 → 点 + →
   Cmd+Shift+G 输入 /bin/bash → 添加并打开开关
2) cp scripts/com.zucai.autorefresh.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.zucai.autorefresh.plist
   launchctl kickstart -k gui/$(id -u)/com.zucai.autorefresh   # 立即验一次
# 卸载：launchctl bootout gui/$(id -u)/com.zucai.autorefresh; rm ~/Library/LaunchAgents/com.zucai.autorefresh.plist
```

（若不想授完全磁盘访问，就用①手动一行即可。把仓库移到主目录 `~/` 下也能免授权，但会改动项目路径。）

只在本机开机联网时更新。日志在 `.wrangler/auto-refresh.log`。`refresh_data.py` 只改数据（JQC/ZFC 快照、两张走势表 ROWS、Elo 随 latest 一起滚动），**不碰算法**；任一路 fetch 失败即整体放弃、保证多文件一致。
