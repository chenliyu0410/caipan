# 行情來源轉發器（proxy）

## 為什麼需要

`data.moa.gov.tw` 的防火牆**只放行台灣 IP**，境外一律在 TCP 層被丟包（不是回 403，是連線逾時）。

實測（2026-10-28）從 12 個國外節點對 `data.moa.gov.tw:443` 建立連線，全部 `Connection timed out`：

```
Brazil Sao Paulo / Germany Langen / Germany Frankfurt / Iran Shiraz
Netherlands Amsterdam / Netherlands Meppel / Sweden Stockholm
Singapore Singapore / Turkey Istanbul / USA Los Angeles
USA New York / Vietnam Ho Chi Minh City
```

同一時間從台灣連線：`200 OK`，1.09 MB，2.8 秒。

GitHub Actions 的 runner 在境外，所以每日更新會卡在逾時。解法是讓請求**從台灣出去**。

> 注意：一般的公用代理（allorigins、codetabs 等）主機也在境外，實測同樣連不到，不能用。

## 方案一：Google Cloud Run（建議，落點確定在台灣彰化）

`asia-east1` 的實體機房在台灣，出口 IP 固定。免費額度遠超過每天 8 次請求。

```bash
cd proxy/cloudrun
gcloud run deploy caipan-moa-proxy --source . --region asia-east1 \
    --allow-unauthenticated --set-env-vars CAIPAN_TOKEN=<自訂字串>
```

> 仍需實測確認：來源若是以「台灣 ISP 位址段白名單」而非「IP 地理位置」放行，
> 雲端機房的位址也可能被擋。部署後跑一次下方的驗證指令就知道。

## 方案二：Cloudflare Workers（本專案不適用，程式碼留作參考）

Worker 本身的轉發邏輯是好的，但**落點搬不到台灣**，原因是 Cloudflare 官方文件寫明
Smart Placement 的前提：

- 需要「來自多個地點的持續流量」才會做出放置決策；
- 請求太少會得到 `INSUFFICIENT_INVOCATIONS`，不做任何搬移；
- 而且**只能選擇該 Worker 已經執行過的地點**。

本專案每天只有 4～8 次請求，而且全部來自同一個地點（GitHub 的境外 runner）。
Worker 永遠不會在台灣節點執行過，Smart Placement 也就永遠不會把它搬到台灣。

要確認實際落點，看回應的 `cf-placement` 標頭：`local-XXX` 表示沒搬，`remote-XXX` 才是搬過。

程式碼保留在 `proxy/cloudflare/`，若日後流量型態改變或改用可指定區域的方案再啟用。

## 接到 GitHub Actions

在 repo 的 **Settings → Secrets and variables → Actions** 設定：

| 類型 | 名稱 | 值 |
|---|---|---|
| Variables | `MOA_PROXY_BASE` | `https://<你的轉發網址>/?url={url}` |
| Secrets | `MOA_PROXY_TOKEN` | 上面設的 `CAIPAN_TOKEN`（沒設就留空） |

`{url}` 會被替換成 URL-encode 後的目標網址。多個轉發點用逗號分隔，會依序嘗試：

```
https://a.workers.dev/?url={url},https://b.run.app/?url={url}
```

## 行為說明

`scripts/fetch_data.py` 的路由順序是**代理優先、直連墊底**：

- 本機在台灣跑：代理沒設 → 直接走直連，行為跟以前一樣。
- CI 在境外跑：代理通就用代理；代理掛了會退回直連（雖然大概也不通，但留著當保險）。
- 某條路由成功後會被記住，同一次執行的後續日期直接走那條，不再浪費逾時時間。
- 想關掉直連墊底：設 `MOA_ALLOW_DIRECT=0`。
- 單次請求逾時秒數：`MOA_TIMEOUT`，預設 45。

跑完後 `data/latest.json` 的 `fetch_status.route` 會記錄實際走哪條路由，CI 日誌也會印 `改用代理路由取得資料`。

## 驗證

```bash
MOA_PROXY_BASE='https://<你的轉發網址>/?url={url}' MOA_ALLOW_DIRECT=0 python scripts/fetch_data.py
```

關掉直連墊底，確認純靠代理也抓得到。
