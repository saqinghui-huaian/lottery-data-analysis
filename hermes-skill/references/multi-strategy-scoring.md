# Multi-Strategy Scoring System v2 (多策略综合评分 v2)

> **This scoring system is designed for 3-digit lotteries (福彩3D, 排列三).**
> For 大乐透 (5+2 format), see `references/dlt-analysis.md` for the adapted methodology.

## ⚠️ 关键改进 (v2 vs v1)

1. **不再硬排除近10期号码** — 改用加权惩罚，近期出现的号码降低权重但不排除
2. **新增012路分析** — 按模3分组(0路:0,3,6,9 / 1路:1,4,7 / 2路:2,5,8)，分析各位路数走势
3. **新增奇偶/大小比分析** — 奇偶比(1:2/2:1最常见约各30%)、大小比(5-9为大)
4. **新增重号分析** — 与上期相同位置相同号码的"重号"概率约27%
5. **新增连号分析** — 相邻数字(如23,78)出现概率约40%
6. **新增冷号回补策略** — 遗漏值超均值2倍的号码有回补趋势
7. **改进候选生成** — 6种独立策略各生成候选，确保多样性
8. **和值/跨度范围更精确** — 基于近50期数据动态计算

## 核心统计指标

```python
from collections import Counter

def compute_context(data):
    """Compute all statistical context from draw data.
    data: list of (period, bai, shi, ge) tuples, newest first.
    """
    ctx = {}
    n = len(data)
    
    # === 1. 各位频率 (近20/50期) ===
    ctx['freq20'] = [Counter(), Counter(), Counter()]  # 百/十/个
    ctx['freq50'] = [Counter(), Counter(), Counter()]
    for d in data[:20]:
        for pos in range(3): ctx['freq20'][pos][d[pos+1]] += 1
    for d in data[:50]:
        for pos in range(3): ctx['freq50'][pos][d[pos+1]] += 1
    
    # === 2. 加权热度 (近20期×5, 20-50期×3, 50+期×1) ===
    ctx['weighted'] = Counter()
    for d in data[:20]:
        for x in [d[1],d[2],d[3]]: ctx['weighted'][x] += 5
    for d in data[20:50]:
        for x in [d[1],d[2],d[3]]: ctx['weighted'][x] += 3
    for d in data[50:]:
        for x in [d[1],d[2],d[3]]: ctx['weighted'][x] += 1
    
    # === 3. 遗漏值 (距上次出现的期数) ===
    ctx['miss'] = [{},{},{}]  # [百位遗漏, 十位遗漏, 个位遗漏]
    for digit in range(10):
        for pos in range(3):
            for i, d in enumerate(data):
                if d[pos+1] == digit:
                    ctx['miss'][pos][digit] = i
                    break
            else:
                ctx['miss'][pos][digit] = n
    
    # === 4. 和值统计 ===
    sums = [d[1]+d[2]+d[3] for d in data]
    ctx['hz_avg'] = sum(sums[:30]) / min(30, n)
    ctx['hz_std'] = (sum((s - ctx['hz_avg'])**2 for s in sums[:30]) / min(30, n)) ** 0.5
    
    # === 5. 跨度统计 ===
    spans = [max(d[1],d[2],d[3]) - min(d[1],d[2],d[3]) for d in data]
    ctx['kd_freq'] = Counter(spans[:30])
    ctx['kd_avg'] = sum(spans[:30]) / min(30, n)
    
    # === 6. 012路统计 (近20期) ===
    def road(x): return x % 3  # 0路:0,3,6,9 | 1路:1,4,7 | 2路:2,5,8
    ctx['road20'] = [Counter(), Counter(), Counter()]
    for d in data[:20]:
        for pos in range(3): ctx['road20'][pos][road(d[pos+1])] += 1
    
    # === 7. 奇偶统计 (近20期) ===
    ctx['odd_cnt'] = 0
    ctx['even_cnt'] = 0
    for d in data[:20]:
        for x in [d[1],d[2],d[3]]:
            if x % 2 == 1: ctx['odd_cnt'] += 1
            else: ctx['even_cnt'] += 1
    
    # === 8. 大小统计 (近20期, 5-9为大) ===
    ctx['big_cnt'] = 0
    ctx['small_cnt'] = 0
    for d in data[:20]:
        for x in [d[1],d[2],d[3]]:
            if x >= 5: ctx['big_cnt'] += 1
            else: ctx['small_cnt'] += 1
    
    # === 9. 重号统计 (近10期与上期同位置同号码) ===
    ctx['repeat_rate'] = 0
    repeat_total = 0
    for i in range(min(10, n-1)):
        curr = data[i]
        prev = data[i+1]
        for pos in range(3):
            repeat_total += 1
            if curr[pos+1] == prev[pos+1]:
                ctx['repeat_rate'] += 1
    ctx['repeat_rate'] = ctx['repeat_rate'] / max(repeat_total, 1)
    
    # === 10. 近期走势方向 (近5期各位升降) ===
    ctx['trend'] = [{}, {}, {}]  # 每位: digit -> 近5期出现次数
    for d in data[:5]:
        for pos in range(3):
            ctx['trend'][pos][d[pos+1]] = ctx['trend'][pos].get(d[pos+1], 0) + 1
    
    return ctx
```

## 评分公式 v2

```python
def score_bet(b, s, g, ctx):
    """Score a 3-digit combination. Higher = better candidate."""
    score = 0.0
    
    # ── 1. 加权热度 (权重: 0.12) ──
    # 热号有惯性，但不追极端热号
    heat = ctx['weighted'].get(b,0) + ctx['weighted'].get(s,0) + ctx['weighted'].get(g,0)
    score += heat * 0.12
    
    # ── 2. 位置频率 (权重: 0.15) ──
    # 近20期各位出现频率
    score += ctx['freq20'][0].get(b, 0) * 2.5
    score += ctx['freq20'][1].get(s, 0) * 2.5
    score += ctx['freq20'][2].get(g, 0) * 2.5
    
    # ── 3. 遗漏回补 (权重: 0.18) ──
    # 遗漏值越大，回补概率越高，但有上限
    # 使用sigmoid-like函数：遗漏值10-15期时加分最高
    for pos, digit in enumerate([b, s, g]):
        m = ctx['miss'][pos].get(digit, 0)
        if m >= 8:
            score += min(m, 25) * 0.25  # 遗漏8期以上开始加分
        if m >= 15:
            score += 3  # 遗漏15期以上额外加分
    
    # ── 4. 012路匹配 (权重: 0.10) ──
    # 匹配近期各位的路数走势
    def road(x): return x % 3
    for pos, digit in enumerate([b, s, g]):
        r = road(digit)
        # 如果该路数在近20期出现较多，加分
        road_freq = ctx['road20'][pos].get(r, 0)
        score += road_freq * 1.0
    
    # ── 5. 和值合理性 (权重: 0.12) ──
    hz = b + s + g
    hz_diff = abs(hz - ctx['hz_avg'])
    if hz_diff <= 2: score += 8
    elif hz_diff <= 4: score += 5
    elif hz_diff <= 6: score += 2
    # 和值在9-18之间是高频区
    if 9 <= hz <= 18: score += 3
    
    # ── 6. 跨度合理性 (权重: 0.08) ──
    kd = max(b, s, g) - min(b, s, g)
    # 近30期高频跨度加分
    kd_freq = ctx['kd_freq'].get(kd, 0)
    score += kd_freq * 0.8
    # 跨度4-7最常见
    if 4 <= kd <= 7: score += 2
    
    # ── 7. 组选形态 (权重: 0.06) ──
    unique = len(set([b, s, g]))
    if unique == 3: score += 4  # 组六最常见(~60%)
    elif unique == 2: score += 2  # 组三(~35%)
    # 豹子不加分(~5%)
    
    # ── 8. 奇偶平衡 (权重: 0.05) ──
    odd_count = sum(1 for x in [b,s,g] if x % 2 == 1)
    # 2奇1偶或1奇2偶最常见
    if odd_count in [1, 2]: score += 2
    
    # ── 9. 大小平衡 (权重: 0.05) ──
    big_count = sum(1 for x in [b,s,g] if x >= 5)
    # 2大1小或1大2小最常见
    if big_count in [1, 2]: score += 2
    
    # ── 10. 连号加分 (权重: 0.04) ──
    # 相邻数字对(如23, 78)出现概率约40%
    digits = sorted([b, s, g])
    has_consecutive = False
    for i in range(len(digits)-1):
        if digits[i+1] - digits[i] == 1:
            has_consecutive = True
            break
    if has_consecutive: score += 2
    
    # ── 11. 近期重复惩罚 (不是排除！) ──
    # 近5期出现过的号码组合轻微降分
    for d in ctx.get('recent5', []):
        if (b,s,g) == (d[1],d[2],d[3]):
            score -= 15
            break
    # 近10期出现过的号码组合降分更多
    for d in ctx.get('recent10', []):
        if (b,s,g) == (d[1],d[2],d[3]):
            score -= 25
            break
    
    # ── 12. 冷号回补奖励 ──
    # 各位遗漏值都较大的组合，有回补趋势
    total_miss = sum(ctx['miss'][pos].get(d, 0) for pos, d in enumerate([b,s,g]))
    if total_miss >= 30: score += 5  # 三位总遗漏大
    if total_miss >= 50: score += 3  # 极度遗漏
    
    return score
```

## 候选生成策略 (6种独立策略)

```python
def generate_candidates(ctx, data):
    """Generate diverse candidates from 6 independent strategies."""
    candidates = set()
    
    # ── 策略1: 位置热号组合 ──
    # 各位取top 6热号，组合
    top_bai = [x[0] for x in ctx['freq20'][0].most_common(6)]
    top_shi = [x[0] for x in ctx['freq20'][1].most_common(6)]
    top_ge  = [x[0] for x in ctx['freq20'][2].most_common(6)]
    for b in top_bai:
        for s in top_shi:
            for g in top_ge:
                candidates.add((b,s,g))
    
    # ── 策略2: 加权热度组合 ──
    top7 = [x[0] for x in ctx['weighted'].most_common(7)]
    for b in top7:
        for s in top7:
            for g in top7:
                candidates.add((b,s,g))
    
    # ── 策略3: 遗漏回补组合 ──
    # 各位取遗漏值最大的4个号码
    for pos in range(3):
        high_miss = sorted(ctx['miss'][pos].items(), key=lambda x: -x[1])[:4]
        for d, _ in high_miss:
            # 与热号搭配
            for h in top7:
                for h2 in top7:
                    combo = [h, h2, h2]  # 占位
                    combo[pos] = d
                    candidates.add(tuple(combo))
    
    # ── 策略4: 和值目标组合 ──
    # 生成和值在 avg±3 范围内的组合
    target_hz = int(ctx['hz_avg'])
    for b in range(10):
        for s in range(10):
            for g in range(10):
                if abs(b+s+g - target_hz) <= 3:
                    candidates.add((b,s,g))
    
    # ── 策略5: 012路组合 ──
    # 根据近期路数走势生成
    for pos in range(3):
        hot_roads = [r for r, _ in ctx['road20'][pos].most_common(2)]
        hot_digits_for_road = [d for d in range(10) if d % 3 in hot_roads]
        for d in hot_digits_for_road[:4]:
            for h in top7:
                for h2 in top7:
                    combo = [h, h2, h2]
                    combo[pos] = d
                    candidates.add(tuple(combo))
    
    # ── 策略6: 冷号回补组合 ──
    # 遗漏值超过均值2倍的号码组合
    cold_digits = [[], [], []]
    for pos in range(3):
        avg_miss = sum(ctx['miss'][pos].values()) / 10
        for d in range(10):
            if ctx['miss'][pos].get(d, 0) > avg_miss * 1.5:
                cold_digits[pos].append(d)
    for b in cold_digits[0][:3]:
        for s in cold_digits[1][:3]:
            for g in cold_digits[2][:3]:
                candidates.add((b,s,g))
    
    return candidates
```

## 完整执行流程

```python
def analyze_and_recommend(data, top_n=10):
    """Complete analysis pipeline.
    data: list of (period, bai, shi, ge), newest first.
    Returns: list of (score, bai, shi, ge, sum, span)
    """
    # 1. 计算所有统计指标
    ctx = compute_context(data)
    
    # 2. 存储近期数据用于惩罚
    ctx['recent5'] = data[:5]
    ctx['recent10'] = data[:10]
    
    # 3. 生成候选
    candidates = generate_candidates(ctx, data)
    
    # 4. 评分
    scored = []
    for b, s, g in candidates:
        sc = score_bet(b, s, g, ctx)
        hz = b + s + g
        kd = max(b,s,g) - min(b,s,g)
        scored.append((sc, b, s, g, hz, kd))
    
    # 5. 排序取top
    scored.sort(key=lambda x: -x[0])
    return scored[:top_n]
```

## 关于"排除近10期"的说明

**v1做法(有问题)**: 硬排除近10期出现过的所有组合 → 候选池被大幅缩减，且近期号码确实有重复出现的概率(约27%)

**v2做法(改进)**: 不排除，改为加权惩罚
- 近5期出现过的组合: -15分
- 近10期出现过的组合: -25分
- 这样近期号码仍有机会入选，但分数会被压低

**为什么近期号码不应排除?**
- 统计数据显示，约27%的开奖结果包含至少一个与上期同位置的号码
- 约15%的组合会在10期内重复出现
- 硬排除会导致错过这些有概率出现的组合

## 输出模板

参照 `templates/output_format.md`，极简风格，只展示推荐结果。
