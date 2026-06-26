# Chinese Lottery Data Sources

## Working APIs (verified 2026-06-14)

### Sporttery (official) - BEST for 排列三/排列五
- Base URL: `https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry`
- Game numbers: 35=排列三, 37=排列五
- Max pageSize ~100, paginate via pageNo
- Required headers:
  - `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36`
  - `Accept: application/json`
  - `Referer: https://www.lottery.gov.cn/` (NOT zhcw.com — that was the old referer)
- **PITFALL**: WAF blocks urllib in some sessions but allows curl. If urllib fails with empty response or 302 loop, switch to `curl -s` via terminal()
- **Does NOT work for 福彩3D** (gameNo=3 returns empty data)
- Verified working 2026-06-14

### cwl.gov.cn - BEST for 福彩3D (as of 2026-06)
- **Requires 2-step cookie flow** (cookie-less requests return empty `{"status":0,"message":null}`)
- Step 1: GET index page to acquire cookies: `curl -s -c cookies.txt 'https://www.cwl.gov.cn/ygkj/wqkjgg/fc3d/'`
- Step 2: Hit API with cookies: `curl -s -b cookies.txt -L --max-redirs 5 'https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=100&systemType=PC'`
- Headers needed: User-Agent + Accept: application/json + Referer: cwl.gov.cn
- Response: `data['result']` array, each with `code` (period), `red` (comma-sep numbers like "3,7,7"), `date`
- **CRITICAL**: Must use curl, not Python urllib — urllib hits infinite 302 redirect loops even with cookie handling
- If WAF blocks ("云安全平台检测到您当前的访问行为存在异常"), wait 5-10s and retry
- Verified working 2026-06-14

### kjapi.com - Browser scraping fallback
- URLs: fc3d.html for 3D, pl3.html for PL3
- About 30 recent draws in HTML table
- Requires browser tool due to anti-bot JS

## Blocked Sources (2026-06 status)
- 500.com: 404 Not Found
- 17500.cn: Anti-scraping
- caipiao.163.com: DNS fails
- sina.com.cn lottery API: 404
- lottery.gov.cn: serves JS shell, actual data via sporttery.cn API

## Period Numbering
- PL3/PL5: 5-digit like 26130
- 3D: 7-digit like 2026130
