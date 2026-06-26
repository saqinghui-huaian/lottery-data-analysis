---
name: lottery-data-analysis
description: >
  Analyze Chinese lottery draw history (福彩3D, 排列三, 排列五, 大乐透, 双色球, etc.)
  — fetch data from official APIs, compute statistical metrics (frequency, sum,
  odd/even, span, 012路, shape), and generate multi-strategy number recommendations.
trigger:
  - user asks to analyze lottery draws
  - user asks for lottery statistics, trends, hot/cold numbers
  - user wants frequency analysis or pattern detection
  - user sends lottery trend chart images
  - user asks for "金码" or number recommendations
---

# Lottery Data Analysis

Fetches historical draw data for Chinese lotteries and produces analysis with multi-strategy scoring recommendations.

## Data Sources

### 排列三 / 排列五 (sporttery.cn)

```bash
curl -s 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=35&provinceId=0&pageSize=100&isVerify=1&pageNo=1' \
  -H 'User-Agent: Mozilla/5.0 ...' \
  -H 'Referer: https://www.lottery.gov.cn/'
```

### 福彩3D (cwl.gov.cn)

```bash
# Step 1: Get cookies
curl -s -c /tmp/cwl_cookies.txt 'https://www.cwl.gov.cn/ygkj/wqkjgg/fc3d/' -o /dev/null

# Step 2: API call with cookies
curl -s -b /tmp/cwl_cookies.txt \
  'https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=100&systemType=PC'
```

## Analysis Metrics

1. **号码频率** — hot/cold numbers across positions
2. **各位频率** — per-position (百/十/个) frequency
3. **和值** — sum distribution (min/max/avg)
4. **奇偶比** — odd vs even ratio
5. **大小比** — big(5-9) vs small(0-4)
6. **跨度** — max-min digit span
7. **组选形态** — 豹子/组三/组六
8. **012路** — mod-3 grouping analysis
9. **重号** — repeat numbers from previous draw
10. **连号** — consecutive digit pairs

## Multi-Strategy Scoring v2

See `references/multi-strategy-scoring.md` for the complete 12-dimension scoring system with 6 independent candidate generation strategies.

**Key improvements in v2:**
- No hard exclusion of recent draws — uses weighted penalty instead
- 012 road analysis added
- Odd/even and big/small balance analysis
- Repeat number tracking
- Consecutive digit detection
- Cold number comeback strategy

## Output Format

See `templates/output_format.md`. Output is minimal — only recommendations, no analysis process shown.

```
## 🎰 金码银码推荐 & 10注精选
**YYYY-MM-DD | 今日待开：XXXXX期**

### 📊 福彩3D
**🥇 金码：XXX / XXX**
**🥈 银码：XXX / XXX**

| 序号 | 号码 | 和值 | 跨度 |
|:---:|:---:|:---:|:---:|
| 1 | **XXX** | X | X |
```

## Pitfalls

- sporttery.cn WAF blocks urllib — use `curl` via subprocess
- cwl.gov.cn requires cookies — 2-step curl flow mandatory
- cwl.gov.cn JSON has control chars — use regex, not json.loads
- WAF rate-limits pagination — only page 1 reliable
- 金码/银码 must be complete 3-digit combos, not individual digits
- Results should vary each run — use multiple strategies for diversity
