# 大乐透 (Super Lotto) Analysis Guide

## Game Rules
- **前区 (Front area)**: Pick 5 numbers from 1-35
- **后区 (Back area)**: Pick 2 numbers from 1-12
- Draw schedule: Mon/Wed/Sat evenings
- Period format: 5-digit YY+seq (e.g. 26061 = 2026 year, 61st draw)

## Data Source
Check these in order:
1. User's local Documents folder (ask user for path)
2. `~/Desktop/超级大乐透历史开奖数据.xlsx`
3. `~/Documents/Claude Code生成/超级大乐透历史开奖数据.xlsx`

**固定格式**（每个号码独立单元格，倒序排列）：
`期号, 开奖日期, 前区1, 前区2, 前区3, 前区4, 前区5, 后区1, 后区2`

最新一期在最前面。Historical data: 2800+ periods from 2007.

If no local file, the sporttery API may work with `gameNo` for 大乐透 (unverified).

## Position Analysis (Front Area — Sorted)
Since front area is 5 numbers from 1-35, always **sort ascending** first.
Then compute position-specific frequency for 5 positions:
- 第1位 (smallest): typically 1-12
- 第2位: typically 4-20
- 第3位 (median): typically 12-25
- 第4位: typically 20-30
- 第5位 (largest): typically 25-35

```python
def pos_freq(data):
    freqs = [Counter() for _ in range(5)]
    for d in data:
        for i, num in enumerate(d['front']):  # front must be sorted
            freqs[i][num] += 1
    return freqs
```

## Multi-Strategy Scoring for 大乐透

The 3-digit scoring system does NOT directly apply. 大乐透 needs separate
front (5 from 35) and back (2 from 12) scoring.

### Front Area Scoring Weights
1. **Weighted heat** (×0.1): recent 20 = 5x, 20-50 = 3x, 50-100 = 1x
2. **Position-specific freq** (×2): each number scored against its sorted position
3. **Omission backfill** (×0.3, capped at 30): sweet spot is 10-25 periods overdue
4. **Sum reasonableness**: avg ±5 = +8, ±10 = +5, ±15 = +3
5. **Odd/even balance**: 2:3 or 3:2 = +3
6. **Big/small balance** (17+ = big): 2:3 or 3:2 = +3
7. **Three-zone distribution**: [2:2:1] or [2:1:2] or [1:2:2] = best (zones: 1-12, 13-23, 24-35)
8. **Span**: 25-33 = +3
9. **012路 balance**: all 3 roads represented = +2
10. **Repeat numbers** (重号): 1 repeat from last draw = +3, 2 = +2
11. **Hot tail digits**: tail 3/4/2 are hottest in recent 20 periods
12. **Consecutive numbers** (连号): 1 pair = +2, ≥3 consecutive = -3
13. **Pair frequency**: bonus for recently co-occurring pairs

### Back Area Scoring Weights
1. **Weighted heat** (×0.2): same weighting scheme
2. **Omission backfill** (×0.3): sweet spot 5-15 periods overdue
3. **Sum reasonableness**: close to avg (typically 11-14) = +5
4. **Odd/even**: 1:1 (one odd one even) = +2
5. **012路 diversity**: 2 different roads = +1

### Candidate Generation Strategy
Generate 10,000+ front candidates from multiple pools:
- **Position hot**: pick top 6-8 from each position → random combos (3000 tries)
- **Hot numbers**: random 5 from top 15 hottest (1500 tries)
- **Hot + overdue mix**: 3 hot + 2 overdue (1500 tries)
- **Repeat-inclusive**: include 1-2 numbers from last draw (2000 tries)
- **Pair-based**: start from top 30 co-occurring pairs (1000 tries)
- **Zone-balanced**: force 2-2-1 or 2-1-2 zone distribution (3000 tries)

Back candidates: all C(12,2) = 66 combinations (small enough to enumerate).

### Diversity Constraint (CRITICAL — USER EXPLICITLY COMPLAINED)
User said "你这个怎么这么像" when 35 appeared in 6/10 bets and 2 in 6/10.
Simply requiring "unique front combo" is NOT sufficient. Enforce ALL of:

1. **Max overlap between any two bets: 1 number** — `len(set(a) & set(b)) <= 1`
2. **Max occurrences per number across all bets: 2** — no number in 3+ bets
3. **Sum gap between any two bets: ≥8** — ensures and-value diversity
4. **No empty zone** — every bet must have ≥1 number in each of the 3 zones
5. **All back combos different** — 10 unique back pairs
6. **Coverage target: ≥20 different front numbers** across all 10 bets

Selection algorithm (order matters):
```
for combo in top_scored_candidates:
    if overlap_with_any_selected(combo) > 1: skip
    if any_number_used_3_times(combo): skip
    if sum_too_close_to_any(combo, threshold=8): skip
    if has_empty_zone(combo): skip
    select(combo)
# If <10 selected after first pass, relax overlap to ≤2 and re-run
```

Without this, the single highest-scoring front area dominates all slots
with only back numbers varying (learned the hard way, user complained).

## Mathematical Analysis Dimensions (USER DEMANDED RIGOR)
User said "按照网络上的方法等，好好分析，以及概率公式等" — they want real
probability formulas, not just simple frequency counting. Include ALL of:

### AC值 (Arithmetic Complexity)
- Definition: count unique pairwise differences among 5 numbers, subtract 4
- Formula: AC = |{ |aᵢ-aⱼ| : i<j }| - (n-1), where n=5
- Range: 0~10; AC≥4 required, AC 5-8 is the sweet spot
- ~73% of draws have AC 4-6; AC<4 means numbers are too clustered — EXCLUDE
```python
def calc_ac(combo):
    diffs = set()
    for i in range(5):
        for j in range(i+1, 5):
            diffs.add(abs(combo[i] - combo[j]))
    return len(diffs) - 4
```

### 偏度 (Skewness)
- Formula: γ₁ = Σ(xᵢ-x̄)³ / (n·σ³)
- Positive skew = leans toward small numbers; negative = toward large
- Theoretical ≈0 for uniform; actual typically near 0 (slight positive)
- Use to verify combo is not abnormally skewed

### 峰度 (Kurtosis)
- Formula: γ₂ = Σ(xᵢ-x̄)⁴ / (n·σ⁴) - 3
- Positive = concentrated; negative = dispersed (excess kurtosis)
- Theoretical ≈0; actual typically slightly negative (-1.2 in recent data)
- Use to verify combo spacing is realistic

### 质合比 (Prime/Composite Ratio)
- Front area primes (11): 2,3,5,7,11,13,17,19,23,29,31
- Front area composites (24): 1,4,6,8,9,10,12,14,15,16,18,20,21,22,24,25,26,27,28,30,32,33,34,35
- Note: 1 is neither prime nor composite; treat as composite for lottery
- Expected: 5×11/35 ≈ 1.57 primes per draw
- Most common: 1:4 (≈40%) and 2:3 (≈37%); ≥4 primes is rare — EXCLUDE

### 号码间距 (Number Gaps)
- Gap between consecutive sorted numbers: dᵢ = aᵢ₊₁ - aᵢ
- Average gap ≈ (max-min)/4 ≈ 7
- One pair of consecutive numbers (gap=1) appears ~50% of draws
- All gaps ≥6 = too uniform; multiple gaps=1 = too clustered

### 和值分布 (Sum Distribution)
- Theoretical: E[Sum] = 5 × (1+35)/2 = 90
- Variance ≈ 5 × (35²-1)/12 ≈ 510, σ ≈ 22.6
- ~68% of draws: sum in [67, 113] (±1σ)
- ~95% of draws: sum in [45, 135] (±2σ)
- Sum <50 or >135 is extremely rare — EXCLUDE

### 概率基础公式
- C(n,k) = n! / (k!(n-k)!)
- 前区组合: C(35,5) = 324,632
- 后区组合: C(12,2) = 66
- 总组合: 324,632 × 66 = 21,425,712
- 一等奖概率: 1/21,425,712 ≈ 4.67×10⁻⁸

### 奇偶比理论概率
- 3奇2偶: C(18,3)×C(17,2)/C(35,5) ≈ 34.2%
- 2奇3偶: C(18,2)×C(17,3)/C(35,5) ≈ 31.8%
- 4奇1偶: ≈ 14.7%
- 1奇4偶: ≈ 11.3%
- 5奇0偶: ≈ 2.1% — rare, EXCLUDE as primary strategy

### 遗漏概率模型
- P(号码遗漏≥k期) = (6/7)^k (each draw independent, p=5/35=1/7)
- P(≥15期) = 9.9%, P(≥20期) = 4.6%, P(≥25期) = 2.1%, P(≥30期) = 1.0%
- Gambler's fallacy warning: overdue numbers are NOT "due" — each draw is independent
- But very overdue (>25) numbers appearing IS statistically notable

### 重号期望
- Expected repeats per draw: 5×5/35 ≈ 0.71
- Distribution: 0 repeats ≈37%, 1 ≈37%, 2 ≈18%, 3 ≈6%

### Multi-Dimensional Scoring (13 Dimensions)
When scoring front combos, weight ALL of these (not just frequency):
1. Weighted heat (×0.1): recent 20=5x, 20-50=3x, 50-100=1x
2. Position-specific freq (×2): match sorted position
3. Omission backfill (×0.3, cap 30): sweet spot 10-20 periods
4. Sum reasonableness: 80-100=+10, 75-110=+6, 65-120=+2, else -5
5. AC value: ≥5=+6, =4=+3, <4=-8 (exclude)
6. Span: 20-28=+6, 18-32=+3, <15=-5
7. Odd/even: 2:3 or 3:2=+5, else=+1 or -5
8. Big/small: 2:3 or 3:2=+5, else=+1 or -5
9. Three-zone: (2,2,1)/(2,1,2)/(1,2,2)=+8, empty zone=-8
10. 012路: 3 roads=+5, 2=+2
11. Prime/composite: 1:4 or 2:3=+4, 3:2=+1, ≥4=-3
12. Repeat numbers: 1=+4, 2=+2, 0=0
13. Tail digit heat: tails 3/2/1/0/4 bonus +1.5 each

## Additional 大乐透-Specific Metrics

### 重号 (Repeat Numbers)
Count how many numbers from the previous draw reappear in the current draw.
Recent trend analysis: typically 0-2 repeats per draw. Track for last 10 draws.

### 连号 (Consecutive Numbers)
Count consecutive pairs in the 5-number front area.
~50% of draws have exactly 1 consecutive pair.

### 三区分布 (Three-Zone Distribution)
Split front area into 3 zones: 1-12, 13-23, 24-35.
Track distribution patterns like [2:2:1], [2:1:2], etc.

### 尾数频率 (Tail Digit Frequency)
Last digit (n % 10) frequency across recent periods.
Useful for identifying which digit endings are trending.

### 后区走势 (Back Area Trends)
Track recent back area draws — note that 01/05 appeared in 3 of last 5 draws
in one analysis run. Look for such clustering patterns.

## 大乐透 Output Format

```
🎰 大乐透 XXXXX期 10注精选推荐
数据来源：XXXX期历史开奖数据 | 分析方法：多策略加权综合评分

📅 最新开奖：XXXXX期 (YYYY-MM-DD)
   前区: XX XX XX XX XX  后区: XX XX
📅 待开：XXXXX期

📊 关键数据速览
【前区热度TOP5】 XX(XX) XX(XX) ...
【前区遗漏TOP5】 XX(XX期) ...
【后区热度TOP3】 XX(XX) ...
【后区遗漏TOP3】 XX(XX期) ...
【近期特征】 ...
【重号趋势】 ...
【连号趋势】 ...

🏆 10注精选推荐
 序号  前区号码               后区    和值 AC 跨度 奇偶  三区    选号依据
───────────────────────────────────────────────────────────────────
  1.  XX XX XX XX XX  + XX XX   XXX  X  XX  X:X  X:X:X  策略说明
  2.  ...
(每注必显: 和值、AC值、跨度、奇偶比、三区分布、选号依据)
Excel版额外列: 012路、质合比

🔍 选号核心逻辑
1️⃣ 前区重点号码 (热号/遗漏/重号)
2️⃣ 后区重点号码 (冷号/热号)
3️⃣ 形态特征 (三区/奇偶/和值)

⚠️ 仅供参考，请理性投注！
```

## Pitfalls (大乐透-Specific)
- **Front area must be sorted ascending** before position analysis
- **Diversity constraint is CRITICAL** — user complained "你这个怎么这么像". See Diversity Constraint section above for strict rules.
- **Back area is 1-12, not 1-10**: don't forget 11 and 12
- **Three-zone analysis is critical** for 大乐透; doesn't apply to 3-digit games
- **012路 applies to front area (1-35)** not just 0-9
- **Sum range is 15-165** for front area (not 0-27 like 3D)
- **Repeat numbers** (重号) analysis: check overlap with previous draw's front set
- **Overdue sweet spot**: numbers overdue 10-25 periods are best candidates;
  very overdue (>25) get diminishing returns bonus
- **AC值 < 4 must be excluded** — numbers too clustered, historically unrealistic
- **Data path**: check `/mnt/c/Users/21920/Documents/Hermes/` first, not just Desktop
