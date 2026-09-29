# jev-mas: 闲鱼二手数码捡漏监控

盯住指定机型，自动发现闲鱼上明显低于行情的挂单。

## 工作流程

1. **抓取**：Playwright 驱动系统 Chrome 搜索闲鱼（复用登录态）
2. **审核**：Jev 对每条挂单一次判断三件事
   - 是不是目标机型的整机（排除配件、求购、租赁、型号/容量不符）
   - 成色：准新 / 良好 / 一般 / 较差
   - 硬伤：无 / 小问题（电池、细划痕）/ 大问题（碎屏、主板、ID 锁…，直接排除）
3. **行情价**：合格挂单 + 近几天历史，按成色取中位数（样本 ≥5 条）
4. **捡漏**：低于行情 ≥8% 且 ≥¥200 → Jev 评估是否骗局/隐藏问题 → 可信度达标就推送
5. **去重**：同一商品同一价格只推一次；降价会再推

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env            # 填 TYPESAFE_API_KEY 和 TARGET_KEYWORDS

python test_jev.py              # 验证 Jev API
python test_xianyu.py --login   # 首次登录闲鱼（扫码）
python test_xianyu.py "iPhone 15 Pro Max 256G"   # 验证搜索

python -m jev_mas.main --once   # 扫一轮
python -m jev_mas.main          # 持续监控
```

## Jev API

- `POST https://api.typesafe.ai/v1/systemone`，`Authorization: Bearer apikey_...`，`model: jev-latest`
- 三种判断：`noul`（是/否概率）/ `choice`（选项）/ `score`（打分）
- instructions 用英文，state 里的中文商品信息没问题

## 目录

```
jev_mas/
├── main.py            # 入口：扫描循环
├── config.py          # .env 配置
├── scrapers/xianyu.py # 闲鱼搜索（mtop → 拦截 → DOM 三级降级）
├── jev/client.py      # Jev API 客户端
├── jev/judge.py       # 挂单审核 + 捡漏风险评估
├── deals.py           # 行情价与捡漏判定
├── db.py              # SQLite：挂单历史 + 已推送记录
├── alerts.py          # 终端 / Webhook 提醒
└── models.py
```
