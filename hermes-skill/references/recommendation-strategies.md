# Number Recommendation Strategies (金码推荐策略)

**IMPORTANT: All recommendations must be complete 3-digit bets (整注).**
金码/银码 are presented as complete combinations (e.g. "924", "817"), never as individual digits.

## Output Template (from user screenshots)

```markdown
## 🎰 金码银码推荐 & 10注精选
**2026-05-26 | 今日待开：26137期**
---

### 📊 福彩3D
**🥇 金码：750 / 756**
**🥈 银码：754 / 780**

**📋 10注推荐：**

| 序号 | 号码 | 和值 | 跨度 |
|:---:|:---:|:---:|:---:|
| 1 | **750** | 12 | 7 |
| 2 | **756** | 18 | 2 |
| 3 | **754** | 16 | 3 |
| 4 | **780** | 15 | 8 |
| 5 | 786 | 21 | 2 |
| ... | ... | ... | ... |

---

### 📊 排列三
(same format)
```

## Strategy 1: 热号主导型 (Hot Number Dominant)

Use the 3 most frequent numbers from recent draws.

```python
def hot_number_strategy(hot_nums):
    """Generate combinations using hot numbers."""
    return [
        [hot_nums[0], hot_nums[1], hot_nums[2]],
        [hot_nums[1], hot_nums[0], hot_nums[2]],
        [hot_nums[2], hot_nums[1], hot_nums[0]]
    ]
```

## Strategy 2: 各位热号组合 (Position Hot Numbers)

Combine the hottest number from each position (百位, 十位, 个位).

```python
def position_hot_strategy(h_hot, t_hot, u_hot):
    """Combine hot numbers from each position."""
    return [
        [h_hot[0], t_hot[0], u_hot[0]],
        [h_hot[1], t_hot[1], u_hot[1]]
    ]
```

## Strategy 3: 跨度型 (Span-Based)

Generate combinations matching the most frequent span value.

```python
def span_strategy(target_span):
    """Generate valid combinations for target span."""
    valid = []
    for i in range(10):
        for j in range(10):
            for k in range(10):
                if max(i,j,k) - min(i,j,k) == target_span:
                    valid.append([i,j,k])
    return random.sample(valid[:10], 2)
```

## Strategy 4: 和值型 (Sum-Based)

Target combinations with sum equal to average sum value.

```python
def sum_strategy(target_sum):
    """Generate combinations with target sum."""
    valid = []
    for i in range(10):
        for j in range(10):
            for k in range(10):
                if i+j+k == target_sum:
                    valid.append([i,j,k])
    return random.sample(valid[:10], 2)
```

## Strategy 5: 冷热搭配型 (Hot-Cold Mix)

Mix hot numbers with cold numbers for balance.

```python
def hot_cold_strategy(hot_nums, cold_nums):
    """Mix hot and cold numbers."""
    return [
        [hot_nums[0], cold_nums[0], hot_nums[1]],
        [cold_nums[0], hot_nums[0], hot_nums[2]]
    ]
```

## Best Practice: Multi-Strategy Scoring

For the best results, use the multi-strategy scoring system in `references/multi-strategy-scoring.md` which combines all strategies into a single weighted score.

## Disclaimer

Always include:
```
> ⚠️ 仅供参考，请理性投注！
```
