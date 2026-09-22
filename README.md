# jev-mas: 二手数码跨平台套利监控系统

Multi-platform Arbitrage Scanner for second-hand electronics.

监控 **闲鱼 / 转转 / 拍机堂** 三大平台的二手数码产品价格差，自动发现套利机会。

## 架构

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   闲鱼       │    │   转转       │    │   拍机堂     │
│  (自由市场)   │    │ (官方回收+C2C)│    │  (官方回收)   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────┐
│              Scraper Layer (Playwright)              │
│         jev-ultrafast 浏览器 Agent 驱动               │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              Jev Processing Layer                    │
│  · 商品匹配 (同型号/同成色判断)                        │
│  · 价格清洗 (去掉异常值)                              │
│  · 套利信号评分                                      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              Alert & Dashboard                       │
│  · 价差超阈值 → 推送通知                              │
│  · 历史价格趋势                                      │
│  · 套利机会看板                                      │
└─────────────────────────────────────────────────────┘
```

## 技术栈

- **Python 3.11+**
- **Playwright** - 浏览器自动化，模拟登录和数据抓取
- **Jev API** - 快速判断模型，用于：
  - 浏览器 Agent 决策（点哪里、输什么）
  - 商品匹配和分类
  - 套利信号评分
- **SQLite** - 本地价格数据存储
- **Rich** - 终端 Dashboard

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 配置
cp .env.example .env
# 编辑 .env 填入 Jev API Key

# 运行监控
python -m jev_mas.main
```

## 目录结构

```
jev_mas/
├── __init__.py
├── main.py              # 入口
├── config.py            # 配置管理
├── scrapers/            # 各平台爬虫
│   ├── base.py          # 爬虫基类
│   ├── xianyu.py        # 闲鱼
│   ├── zhuanzhuan.py    # 转转
│   └── paijitang.py     # 拍机堂
├── jev/                 # Jev 集成
│   ├── client.py        # Jev API 客户端
│   ├── matcher.py       # 商品匹配
│   └── scorer.py        # 套利评分
├── models.py            # 数据模型
├── db.py                # 数据库操作
├── arbitrage.py         # 套利计算引擎
├── alerts.py            # 通知推送
└── dashboard.py         # 终端看板
```
