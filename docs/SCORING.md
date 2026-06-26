# Scoring Algorithm Details

## Overview

The multi-strategy scoring system v2 evaluates 3-digit lottery combinations across 12 dimensions. It generates candidates from 6 independent strategies, then scores each candidate.

## Scoring Dimensions

### 1. Weighted Heat (×0.12)
Recent numbers have higher weight:
- Last 20 periods: weight × 5
- Periods 20-50: weight × 3
- Periods 50+: weight × 1

### 2. Position Frequency (×0.15)
Each position (百/十/个) has its own frequency counter from the last 20 periods. Score = frequency × 2.5 per position.

### 3. Omission Backfill (×0.18)
Numbers that haven't appeared for many periods get bonus:
- Miss ≥ 8 periods: +miss × 0.25 (capped at 25)
- Miss ≥ 15 periods: additional +3

### 4. 012 Road Match (×0.10)
Numbers grouped by mod 3:
- 0路: {0, 3, 6, 9}
- 1路: {1, 4, 7}
- 2路: {2, 5, 8}

Score based on how well the combo matches recent road trends per position.

### 5. Sum Reasonableness (×0.12)
- Within ±2 of average: +8
- Within ±4: +5
- Within ±6: +2
- Sum in 9-18 range: +3

### 6. Span Reasonableness (×0.08)
- Match frequent span values from last 30 periods: +freq × 0.8
- Span 4-7 (most common): +2

### 7. Shape Bonus (×0.06)
- 组六 (all different): +4 (~60% of draws)
- 组三 (one pair): +2 (~35%)
- 豹子 (triple): +0 (~5%)

### 8. Odd/Even Balance (×0.05)
- 1 odd or 2 odd: +2 (most common patterns)

### 9. Big/Small Balance (×0.05)
- 1 big or 2 big: +2 (most common patterns)

### 10. Consecutive Digits (×0.04)
- Any adjacent pair (e.g., 23, 78): +2

### 11. Recent Repeat Penalty
- Appeared in last 5 draws: -15
- Appeared in last 10 draws: -25
- **NOT excluded** — just penalized (v2 improvement)

### 12. Cold Comeback Bonus
- Total miss across all 3 positions ≥ 30: +5
- Total miss ≥ 50: +3

## Candidate Generation

6 independent strategies ensure diversity:

1. **Position Hot** — Top 6 from each position → 6×6×6 = 216 combos
2. **Weighted Heat** — Top 7 overall → 7³ = 343 combos
3. **Omission Backfill** — Top 4 miss per position + hot companions
4. **Sum-Targeted** — All combos within sum ±3 of average
5. **012 Road** — Hot road digits per position + hot companions
6. **Cold Comeback** — Miss > 1.5× average per position

Total candidates: typically 2000-5000 unique combos.

## Why Not Exclude Recent Numbers?

v1 excluded the last 10 periods entirely. This caused:
- Candidate pool too small
- Missed the ~27% of draws that DO repeat numbers
- Same recommendations every time (limited diversity)

v2 uses weighted penalty instead — recent numbers CAN appear but with lower scores.
