#!/usr/bin/env python3
"""
Lottery draw data fetcher, statistical analyzer, and number recommender.
Supports: 排列三 (sporttery API via curl), 福彩3D (cwl.gov.cn API via curl + cookies).

v2: Multi-strategy scoring with 012路, odd/even, big/small, repeat, consecutive analysis.
    No hard exclusion of recent draws — uses weighted penalty instead.

Usage:
    python3 lottery_analysis.py              # analyze 排列三 last 100 draws
    python3 lottery_analysis.py --game 3d    # analyze 福彩3D
    python3 lottery_analysis.py --game 35 --count 100 --recommend

PITFALLS:
- Both APIs MUST use curl (subprocess) — urllib gets 403 from sporttery and
  infinite 302 from cwl.gov.cn.
- cwl.gov.cn JSON has literal control chars — use regex extraction, not json.loads.
- sporttery.cn WAF rate-limits pagination — only page 1 (100 periods) is reliable.
"""

import json
import sys
import subprocess
import tempfile
import os
import random
from collections import Counter

GAME_NAMES = {
    '35': '排列三',
    '37': '排列五',
    '3d': '福彩3D',
    '3D': '福彩3D',
}


def fetch_pl3(game_no='35', count=100):
    """Fetch 排列三/排列五 from sporttery official API.

    MUST use curl — sporttery.cn WAF blocks urllib with 403.
    Uses regex extraction because JSON can contain control characters.
    Note: WAF often blocks pages 2+; only page 1 (100 periods) is reliable.
    """
    import re
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    url = (
        f'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry'
        f'?gameNo={game_no}&provinceId=0&pageSize={count}&isVerify=1&pageNo=1'
    )
    result = subprocess.run([
        'curl', '-s', url,
        '-H', f'User-Agent: {ua}',
        '-H', 'Accept: application/json',
        '-H', 'Referer: https://www.lottery.gov.cn/',
    ], capture_output=True, text=True, timeout=30)

    raw = result.stdout
    # Regex extraction — JSON may have control chars or WAF HTML
    nums_list = re.findall(r'"lotteryDrawResult":"(\d+ \d+ \d+)"', raw)
    periods = re.findall(r'"lotteryDrawNum":"(\d+)"', raw)
    dates = re.findall(r'"lotteryDrawTime":"(\d{4}-\d{2}-\d{2})"', raw)

    results = []
    for i in range(min(len(nums_list), len(periods))):
        ns = list(map(int, nums_list[i].split()))
        d = dates[i] if i < len(dates) else ''
        results.append({
            'period': periods[i],
            'date': d,
            'h': ns[0], 't': ns[1], 'u': ns[2],
            'sum': sum(ns[:3])
        })
    if not results:
        raise RuntimeError("sporttery.cn returned no data — WAF may have blocked the request")
    return results


def fetch_3d(count=100):
    """Fetch 福彩3D from cwl.gov.cn official API (requires curl + cookies).

    Uses regex extraction as primary method because cwl.gov.cn JSON contains
    literal control characters that break json.loads() even with strict=False.
    """
    import re
    cookie_file = os.path.join(tempfile.gettempdir(), 'cwl_cookies.txt')
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

    subprocess.run([
        'curl', '-s', '-c', cookie_file,
        'https://www.cwl.gov.cn/ygkj/wqkjgg/fc3d/',
        '-H', f'User-Agent: {ua}',
        '-o', '/dev/null'
    ], timeout=15, check=False)

    url = (
        f'https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice'
        f'?name=3d&issueCount={count}&systemType=PC'
    )
    result = subprocess.run([
        'curl', '-s', '-b', cookie_file, '-L', '--max-redirs', '5',
        url,
        '-H', f'User-Agent: {ua}',
        '-H', 'Accept: application/json',
        '-H', 'Referer: https://www.cwl.gov.cn/ygkj/wqkjgg/fc3d/',
    ], capture_output=True, text=True, timeout=30)

    raw = result.stdout

    # Primary: regex extraction (reliable even with control chars in JSON)
    codes = re.findall(r'"code":"(\d+)"', raw)
    reds = re.findall(r'"red":"(\d+,\d+,\d+)"', raw)
    dates = re.findall(r'"date":"([^"]+)"', raw)

    if codes and reds:
        results = []
        for i in range(min(len(codes), len(reds))):
            ns = list(map(int, reds[i].split(',')))
            d = dates[i][:10] if i < len(dates) else ''
            results.append({
                'period': codes[i],
                'date': d,
                'h': ns[0], 't': ns[1], 'u': ns[2],
                'sum': sum(ns[:3])
            })
        return results

    # Fallback: json.loads (may fail on control chars)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(
            "cwl.gov.cn returned unparseable data — "
            "regex found no matches and json.loads failed. "
            "Cookies may have expired, retry."
        )
    if not data.get('result'):
        raise RuntimeError("cwl.gov.cn returned empty data — cookies may have expired, retry")

    results = []
    for item in data['result']:
        nums = list(map(int, item['red'].split(',')))
        results.append({
            'period': item['code'],
            'date': item['date'],
            'h': nums[0], 't': nums[1], 'u': nums[2],
            'sum': sum(nums[:3])
        })
    return results


# ══════════════════════════════════════════════════════════════
#  v2 Multi-Strategy Scoring System
# ══════════════════════════════════════════════════════════════

def compute_context(data):
    """Compute all statistical context from draw data.
    data: list of dicts with 'h','t','u' keys, newest first.
    """
    ctx = {}
    n = len(data)

    # 1. Position frequency (recent 20/50)
    ctx['freq20'] = [Counter(), Counter(), Counter()]
    ctx['freq50'] = [Counter(), Counter(), Counter()]
    for d in data[:20]:
        for pos, key in enumerate(['h','t','u']):
            ctx['freq20'][pos][d[key]] += 1
    for d in data[:50]:
        for pos, key in enumerate(['h','t','u']):
            ctx['freq50'][pos][d[key]] += 1

    # 2. Weighted heat
    ctx['weighted'] = Counter()
    for d in data[:20]:
        for x in [d['h'],d['t'],d['u']]: ctx['weighted'][x] += 5
    for d in data[20:50]:
        for x in [d['h'],d['t'],d['u']]: ctx['weighted'][x] += 3
    for d in data[50:]:
        for x in [d['h'],d['t'],d['u']]: ctx['weighted'][x] += 1

    # 3. Omission
    ctx['miss'] = [{},{},{}]
    for digit in range(10):
        for pos, key in enumerate(['h','t','u']):
            for i, d in enumerate(data):
                if d[key] == digit:
                    ctx['miss'][pos][digit] = i
                    break
            else:
                ctx['miss'][pos][digit] = n

    # 4. Sum stats
    sums = [d['h']+d['t']+d['u'] for d in data]
    ctx['hz_avg'] = sum(sums[:30]) / min(30, n)

    # 5. Span stats
    spans = [max(d['h'],d['t'],d['u']) - min(d['h'],d['t'],d['u']) for d in data]
    ctx['kd_freq'] = Counter(spans[:30])

    # 6. 012 road stats
    def road(x): return x % 3
    ctx['road20'] = [Counter(), Counter(), Counter()]
    for d in data[:20]:
        for pos, key in enumerate(['h','t','u']):
            ctx['road20'][pos][road(d[key])] += 1

    # 7. Odd/Even stats
    ctx['odd_cnt'] = 0
    ctx['even_cnt'] = 0
    for d in data[:20]:
        for x in [d['h'],d['t'],d['u']]:
            if x % 2 == 1: ctx['odd_cnt'] += 1
            else: ctx['even_cnt'] += 1

    # 8. Big/Small stats
    ctx['big_cnt'] = 0
    ctx['small_cnt'] = 0
    for d in data[:20]:
        for x in [d['h'],d['t'],d['u']]:
            if x >= 5: ctx['big_cnt'] += 1
            else: ctx['small_cnt'] += 1

    # 9. Repeat rate
    ctx['repeat_rate'] = 0
    repeat_total = 0
    keys = ['h','t','u']
    for i in range(min(10, n-1)):
        for pos in range(3):
            repeat_total += 1
            if data[i][keys[pos]] == data[i+1][keys[pos]]:
                ctx['repeat_rate'] += 1
    ctx['repeat_rate'] = ctx['repeat_rate'] / max(repeat_total, 1)

    return ctx


def score_bet(b, s, g, ctx):
    """Score a 3-digit combination using 12 dimensions. Higher = better."""
    score = 0.0

    # 1. Weighted heat
    heat = ctx['weighted'].get(b,0) + ctx['weighted'].get(s,0) + ctx['weighted'].get(g,0)
    score += heat * 0.12

    # 2. Position frequency (recent 20)
    score += ctx['freq20'][0].get(b, 0) * 2.5
    score += ctx['freq20'][1].get(s, 0) * 2.5
    score += ctx['freq20'][2].get(g, 0) * 2.5

    # 3. Omission backfill
    for pos, digit in enumerate([b, s, g]):
        m = ctx['miss'][pos].get(digit, 0)
        if m >= 8:
            score += min(m, 25) * 0.25
        if m >= 15:
            score += 3

    # 4. 012 road match
    def road(x): return x % 3
    for pos, digit in enumerate([b, s, g]):
        r = road(digit)
        score += ctx['road20'][pos].get(r, 0) * 1.0

    # 5. Sum reasonableness
    hz = b + s + g
    hz_diff = abs(hz - ctx['hz_avg'])
    if hz_diff <= 2: score += 8
    elif hz_diff <= 4: score += 5
    elif hz_diff <= 6: score += 2
    if 9 <= hz <= 18: score += 3

    # 6. Span reasonableness
    kd = max(b, s, g) - min(b, s, g)
    score += ctx['kd_freq'].get(kd, 0) * 0.8
    if 4 <= kd <= 7: score += 2

    # 7. Shape bonus
    unique = len(set([b, s, g]))
    if unique == 3: score += 4
    elif unique == 2: score += 2

    # 8. Odd/Even balance
    odd_count = sum(1 for x in [b,s,g] if x % 2 == 1)
    if odd_count in [1, 2]: score += 2

    # 9. Big/Small balance
    big_count = sum(1 for x in [b,s,g] if x >= 5)
    if big_count in [1, 2]: score += 2

    # 10. Consecutive digits
    digits = sorted([b, s, g])
    for i in range(len(digits)-1):
        if digits[i+1] - digits[i] == 1:
            score += 2
            break

    # 11. Recent repeat penalty (NOT exclusion)
    for d in ctx.get('recent5', []):
        if (b,s,g) == (d['h'],d['t'],d['u']):
            score -= 15
            break
    for d in ctx.get('recent10', []):
        if (b,s,g) == (d['h'],d['t'],d['u']):
            score -= 25
            break

    # 12. Cold number comeback bonus
    total_miss = sum(ctx['miss'][pos].get(d, 0) for pos, d in enumerate([b,s,g]))
    if total_miss >= 30: score += 5
    if total_miss >= 50: score += 3

    return score


def generate_candidates(ctx, data):
    """Generate diverse candidates from 6 independent strategies."""
    candidates = set()
    keys = ['h','t','u']

    # Strategy 1: Position hot combos
    top_bai = [x[0] for x in ctx['freq20'][0].most_common(6)]
    top_shi = [x[0] for x in ctx['freq20'][1].most_common(6)]
    top_ge  = [x[0] for x in ctx['freq20'][2].most_common(6)]
    for b in top_bai:
        for s in top_shi:
            for g in top_ge:
                candidates.add((b,s,g))

    # Strategy 2: Weighted heat combos
    top7 = [x[0] for x in ctx['weighted'].most_common(7)]
    for b in top7:
        for s in top7:
            for g in top7:
                candidates.add((b,s,g))

    # Strategy 3: Omission backfill combos
    for pos in range(3):
        high_miss = sorted(ctx['miss'][pos].items(), key=lambda x: -x[1])[:4]
        for d, _ in high_miss:
            for h in top7:
                for h2 in top7:
                    combo = [h, h2, h2]
                    combo[pos] = d
                    candidates.add(tuple(combo))

    # Strategy 4: Sum-targeted combos
    target_hz = int(ctx['hz_avg'])
    for b in range(10):
        for s in range(10):
            for g in range(10):
                if abs(b+s+g - target_hz) <= 3:
                    candidates.add((b,s,g))

    # Strategy 5: 012 road combos
    def road(x): return x % 3
    for pos in range(3):
        hot_roads = [r for r, _ in ctx['road20'][pos].most_common(2)]
        hot_digits = [d for d in range(10) if road(d) in hot_roads]
        for d in hot_digits[:4]:
            for h in top7:
                for h2 in top7:
                    combo = [h, h2, h2]
                    combo[pos] = d
                    candidates.add(tuple(combo))

    # Strategy 6: Cold number comeback combos
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


def recommend(data, top_n=10):
    """Run v2 multi-strategy scoring and return top N recommendations."""
    ctx = compute_context(data)
    ctx['recent5'] = data[:5]
    ctx['recent10'] = data[:10]

    candidates = generate_candidates(ctx, data)

    scored = []
    for b, s, g in candidates:
        sc = score_bet(b, s, g, ctx)
        hz = b + s + g
        kd = max(b,s,g) - min(b,s,g)
        scored.append((sc, b, s, g, hz, kd))

    scored.sort(key=lambda x: -x[0])
    return scored[:top_n]


def analyze(data, name):
    """Run full statistical analysis and print report."""
    all_nums = []
    h_nums, t_nums, u_nums, sums = [], [], [], []
    for d in data:
        all_nums.extend([d['h'], d['t'], d['u']])
        h_nums.append(d['h'])
        t_nums.append(d['t'])
        u_nums.append(d['u'])
        sums.append(d['sum'])

    print(f"\n{'='*60}")
    print(f"  {name} 近{len(data)}期数据分析报告")
    print(f"  {data[-1]['period']} ~ {data[0]['period']} ({data[-1]['date']} ~ {data[0]['date']})")
    print(f"{'='*60}")

    # 1. Number frequency
    print(f"\n{'─'*60}")
    print("【号码出现频率】")
    ctr = Counter(all_nums)
    for i in range(10):
        c = ctr.get(i, 0)
        pct = c / len(all_nums) * 100
        print(f"  {i}  {c:3d} ({pct:5.1f}%) {'█' * int(pct / 2)}")

    sorted_n = sorted(ctr.items(), key=lambda x: x[1], reverse=True)
    print(f"\n  热号: {', '.join(str(x[0]) for x in sorted_n[:3])}")
    print(f"  冷号: {', '.join(str(x[0]) for x in sorted_n[-3:])}")

    # 2. Per-position frequency
    print(f"\n{'─'*60}")
    print("【各位号码频率】")
    for label, nums in [("百位", h_nums), ("十位", t_nums), ("个位", u_nums)]:
        c = Counter(nums)
        print(f"\n  {label}:")
        for i in range(10):
            cnt = c.get(i, 0)
            pct = cnt / len(nums) * 100
            print(f"    {i}: {cnt:2d} ({pct:5.1f}%) {'█' * int(pct / 2)}")

    # 3. Sum analysis
    print(f"\n{'─'*60}")
    print("【和值分析】")
    print(f"  范围: {min(sums)} ~ {max(sums)}  平均: {sum(sums)/len(sums):.1f}  中位: {sorted(sums)[len(sums)//2]}")
    for lo, hi, lbl in [(0,6,'小'), (7,13,'中'), (14,20,'大'), (21,27,'超大')]:
        cnt = sum(1 for s in sums if lo <= s <= hi)
        pct = cnt / len(sums) * 100
        print(f"  {lbl}({lo:2d}-{hi:2d}): {cnt:3d}期 ({pct:5.1f}%) {'█' * int(pct / 2)}")

    # 4. Odd/Even
    print(f"\n{'─'*60}")
    print("【奇偶分析】")
    odd = sum(1 for s in sums if s % 2 == 1)
    even = len(sums) - odd
    print(f"  奇: {odd}期 ({odd/len(sums)*100:.1f}%)  偶: {even}期 ({even/len(sums)*100:.1f}%)")

    # 5. Big/Small
    print(f"\n{'─'*60}")
    print("【大小分析】(0-4小, 5-9大)")
    big = sum(1 for n in all_nums if n >= 5)
    small = len(all_nums) - big
    print(f"  大: {big}次 ({big/len(all_nums)*100:.1f}%)  小: {small}次 ({small/len(all_nums)*100:.1f}%)")

    # 6. Span
    print(f"\n{'─'*60}")
    print("【跨度分析】")
    spans = [max(d['h'], d['t'], d['u']) - min(d['h'], d['t'], d['u']) for d in data]
    sc = Counter(spans)
    for i in range(10):
        cnt = sc.get(i, 0)
        if cnt > 0:
            pct = cnt / len(spans) * 100
            print(f"  {i}: {cnt:2d} ({pct:5.1f}%) {'█' * int(pct / 2)}")

    # 7. Shape
    print(f"\n{'─'*60}")
    print("【组选形态】")
    trip = pair = straight = 0
    for d in data:
        ns = sorted([d['h'], d['t'], d['u']])
        if ns[0] == ns[2]: trip += 1
        elif ns[0] == ns[1] or ns[1] == ns[2]: pair += 1
        else: straight += 1
    print(f"  豹子: {trip}期 ({trip/len(data)*100:.1f}%)")
    print(f"  组三: {pair}期 ({pair/len(data)*100:.1f}%)")
    print(f"  组六: {straight}期 ({straight/len(data)*100:.1f}%)")

    # 8. 012路
    print(f"\n{'─'*60}")
    print("【012路分析】")
    r0 = sum(1 for n in all_nums if n % 3 == 0)
    r1 = sum(1 for n in all_nums if n % 3 == 1)
    r2 = sum(1 for n in all_nums if n % 3 == 2)
    print(f"  0路(0,3,6,9): {r0}次 ({r0/len(all_nums)*100:.1f}%)")
    print(f"  1路(1,4,7):   {r1}次 ({r1/len(all_nums)*100:.1f}%)")
    print(f"  2路(2,5,8):   {r2}次 ({r2/len(all_nums)*100:.1f}%)")

    # 9. Recent 10
    print(f"\n{'─'*60}")
    print("【最近10期】")
    print(f"  {'期号':<8}  {'号码':<8} {'和值':>4} {'跨度':>4} {'形态'}")
    for d in data[:10]:
        ns = sorted([d['h'], d['t'], d['u']])
        sp = ns[2] - ns[0]
        if ns[0] == ns[2]: sh = "豹子"
        elif ns[0] == ns[1] or ns[1] == ns[2]: sh = "组三"
        else: sh = "组六"
        print(f"  {d['period']:<8}  {d['h']} {d['t']} {d['u']}   {d['sum']:>3}   {sp}   {sh}")

    print(f"\n{'='*60}")
    print("  ⚠ 彩票开奖为随机事件，以上分析仅供参考，不构成预测。")
    print(f"{'='*60}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Lottery draw analyzer v2')
    parser.add_argument('--game', default='35', help='Game: 35=排列三, 37=排列五, 3d=福彩3D')
    parser.add_argument('--count', type=int, default=100, help='Number of recent draws')
    parser.add_argument('--recommend', action='store_true', help='Generate number recommendations')
    parser.add_argument('--top', type=int, default=10, help='Number of recommendations')
    args = parser.parse_args()

    name = GAME_NAMES.get(args.game, f'彩票(game={args.game})')
    print(f"正在获取 {name} 近{args.count}期数据...")

    if args.game.lower() == '3d':
        data = fetch_3d(args.count)
    else:
        data = fetch_pl3(args.game, args.count)

    print(f"获取到 {len(data)} 期数据")
    analyze(data, name)

    if args.recommend:
        print(f"\n{'='*60}")
        print(f"  {name} v2多策略推荐 (12维评分)")
        print(f"{'='*60}")
        results = recommend(data, args.top)
        print(f"\n  {'序号':<4} {'号码':<6} {'和值':>4} {'跨度':>4} {'评分':>6}")
        print(f"  {'─'*30}")
        for i, (sc, b, s, g, hz, kd) in enumerate(results):
            mark = "🥇" if i < 2 else ("🥈" if i < 4 else "  ")
            print(f"  {mark}{i+1:<3} {b}{s}{g}   {hz:>3}   {kd:>3}   {sc:>6.1f}")
        print(f"\n  ⚠ 仅供参考，请理性投注！")
