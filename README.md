# 🎰 Lottery Data Analysis Skill

[中文文档](#中文文档) | [English](#features)

A comprehensive Chinese lottery analysis toolkit with multi-strategy number scoring.

Supports: **福彩3D** | **排列三** | **排列五** | **大乐透**

> ⚠️ Lottery draws are random events. This tool provides statistical analysis only. Please gamble responsibly.

---

## Features

- 📊 **Official API Integration** — Real-time data from sporttery.cn and cwl.gov.cn
- 🔢 **Multi-Strategy Scoring v2** — 12-dimension weighted scoring system
- 🎯 **6 Candidate Generation Strategies** — Ensures diverse recommendations
- 📈 **Comprehensive Statistics** — Frequency, sum, span, odd/even, 012路, shape analysis
- 🖼️ **Trend Chart Recognition** — Extract data from lottery trend chart images
- 🤖 **Hermes Agent Skill** — Drop-in skill for [Hermes Agent](https://hermes-agent.nousresearch.com)

## Quick Start

### Standalone Python Script

```bash
# No dependencies needed (stdlib only)
python3 src/lottery_analysis.py --game 35 --count 100 --recommend   # 排列三
python3 src/lottery_analysis.py --game 3d --count 100 --recommend   # 福彩3D
```

### As Hermes Agent Skill

```bash
# Copy to Hermes skills directory
cp -r hermes-skill/ ~/.hermes/skills/lottery-data-analysis/

# Then ask Hermes:
# "分析一下福彩3D"
# "排列三推荐号码"
# "大乐透分析"
```

### Python API

```python
from src.lottery_analysis import fetch_pl3, fetch_3d, recommend

data = fetch_pl3(game_no='35', count=100)  # 排列三
results = recommend(data, top_n=10)

for score, b, s, g, hz, kd in results:
    print(f"{b}{s}{g}  sum={hz}  span={kd}  score={score:.1f}")
```

## Supported Lotteries

| Lottery | API | Format | Period |
|---------|-----|--------|--------|
| 排列三 | sporttery.cn | 3 digits (0-9) | 5-digit |
| 排列五 | sporttery.cn | 5 digits (0-9) | 5-digit |
| 福彩3D | cwl.gov.cn | 3 digits (0-9) | 7-digit |
| 大乐透 | Local xlsx | 5+2 (1-35 + 1-12) | 5-digit |

## Multi-Strategy Scoring v2

12-dimension weighted scoring:

| # | Dimension | Weight | Description |
|---|-----------|--------|-------------|
| 1 | Weighted Heat | ×0.12 | Recent frequency with time decay |
| 2 | Position Frequency | ×0.15 | Per-position hot numbers |
| 3 | Omission Backfill | ×0.18 | Overdue numbers (sigmoid bonus) |
| 4 | 012 Road Match | ×0.10 | Mod-3 trend matching |
| 5 | Sum Reasonableness | ×0.12 | Near average sum |
| 6 | Span | ×0.08 | Match frequent spans |
| 7 | Shape | ×0.06 | 组六 > 组三 > 豹子 |
| 8 | Odd/Even | ×0.05 | 1:2 or 2:1 preferred |
| 9 | Big/Small | ×0.05 | 1:2 or 2:1 preferred |
| 10 | Consecutive | ×0.04 | Adjacent digit pairs |
| 11 | Repeat Penalty | -15/-25 | Recent combos penalized |
| 12 | Cold Comeback | +5/+8 | High omission bonus |

See [docs/SCORING.md](docs/SCORING.md) for algorithm details.

## Project Structure

```
├── README.md
├── LICENSE
├── src/lottery_analysis.py          # Standalone script
├── hermes-skill/                    # Hermes Agent skill
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   └── templates/
├── docs/
│   ├── API.md                       # API endpoints
│   └── SCORING.md                   # Scoring algorithm
└── examples/sample_output.md
```

## API Endpoints

### 排列三 / 排列五
```
GET https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry
    ?gameNo=35&provinceId=0&pageSize=100&isVerify=1&pageNo=1
Headers: Referer: https://www.lottery.gov.cn/
```

### 福彩3D
```
Step 1: GET https://www.cwl.gov.cn/ygkj/wqkjgg/fc3d/ (cookies)
Step 2: GET https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice
        ?name=3d&issueCount=100&systemType=PC
```

## Known Pitfalls

- sporttery.cn WAF blocks urllib → use `curl`
- cwl.gov.cn requires cookies → 2-step curl flow
- cwl.gov.cn JSON has control chars → use regex extraction
- WAF rate-limits pagination → only page 1 reliable

---

## 中文文档

### 功能特点

- 📊 对接官方API实时获取开奖数据
- 🔢 12维度多策略加权评分系统
- 🎯 6种独立候选生成策略确保多样性
- 📈 频率/和值/跨度/奇偶/012路/形态 全面统计
- 🖼️ 走势图图片识别提取数据
- 🤖 可作为 Hermes Agent 技能直接使用

### 快速使用

```bash
# 分析排列三并推荐号码
python3 src/lottery_analysis.py --game 35 --recommend

# 分析福彩3D
python3 src/lottery_analysis.py --game 3d --recommend
```

### 安装为Hermes技能

```bash
cp -r hermes-skill/ ~/.hermes/skills/lottery-data-analysis/
```

然后对Hermes说："分析一下福彩3D" 或 "排列三推荐号码"

---

## License

MIT License

## Disclaimer

本工具仅用于教育和统计分析目的。彩票开奖为随机事件，分析结果不构成任何保证。请理性投注。

---

**Author**: [saqinghui-huaian](https://github.com/saqinghui-huaian)
