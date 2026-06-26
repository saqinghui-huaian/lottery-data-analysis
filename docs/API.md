# API Documentation

## 排列三 / 排列五

**Base URL**: `https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry`

### Parameters

| Param | Type | Description |
|-------|------|-------------|
| gameNo | string | `35` = 排列三, `37` = 排列五 |
| provinceId | int | `0` = all |
| pageSize | int | Max ~100 |
| isVerify | int | `1` = verified results only |
| pageNo | int | Page number (pagination) |

### Required Headers

```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Accept: application/json
Referer: https://www.lottery.gov.cn/    ← MUST be lottery.gov.cn
```

### Response

```json
{
  "data": {
    "value": {
      "list": [
        {
          "lotteryDrawNum": "26130",
          "lotteryDrawResult": "0 7 0",
          "lotteryDrawTime": "2026-05-20"
        }
      ]
    }
  }
}
```

### Pitfalls

- WAF blocks Python `urllib` (403 Forbidden) — use `curl`
- Only page 1 (100 periods) is reliably accessible
- Rate-limited; wait 3-5s between requests

---

## 福彩3D

**Base URL**: `https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice`

### Authentication

Requires session cookies from the index page:

```bash
# Step 1: Acquire cookies
curl -s -c cookies.txt 'https://www.cwl.gov.cn/ygkj/wqkjgg/fc3d/' -o /dev/null

# Step 2: API call
curl -s -b cookies.txt -L --max-redirs 5 \
  'https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=3d&issueCount=100&systemType=PC'
```

### Parameters

| Param | Type | Description |
|-------|------|-------------|
| name | string | `3d` for 福彩3D |
| issueCount | int | Number of draws to fetch |
| systemType | string | `PC` |

### Response

```json
{
  "result": [
    {
      "code": "2026154",
      "red": "3,7,7",
      "date": "2026-06-13(六)"
    }
  ]
}
```

### Pitfalls

- **Must use curl** — urllib gets infinite 302 redirect loop
- **Cookies required** — without them, returns `{"status":0,"message":null}`
- **JSON has control chars** — use regex extraction as primary parser
