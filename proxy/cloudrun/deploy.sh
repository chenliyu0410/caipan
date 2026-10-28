#!/usr/bin/env bash
# 部署轉發器到 GCP Cloud Run（asia-east1 / 台灣彰化）並立刻驗證是否真的抓得到行情。
#
# 用法：
#   cd proxy/cloudrun && bash deploy.sh
#
# 需要先完成（這兩步會開瀏覽器，必須你本人操作）：
#   gcloud auth login
#   gcloud config set project <你的專案ID>

set -euo pipefail

SERVICE="caipan-moa-proxy"
REGION="asia-east1"
TEST_DATE="${TEST_DATE:-$(date +%Y/%m/%d | awk -F/ '{printf "%d.%02d.%02d", $1-1911, $2, $3}')}"

project="$(gcloud config get-value project 2>/dev/null || true)"
if [ -z "$project" ] || [ "$project" = "(unset)" ]; then
  echo "錯誤：還沒設定專案。請先執行 gcloud config set project <你的專案ID>" >&2
  exit 1
fi
echo "專案：$project    區域：$REGION"

# 密鑰：沿用既有的，沒有就隨機產生一組
token="$(gcloud run services describe "$SERVICE" --region "$REGION" \
          --format='value(spec.template.spec.containers[0].env.filter("name","CAIPAN_TOKEN").extract("value"))' \
          2>/dev/null || true)"
token="$(printf '%s' "$token" | tr -d '[:space:]')"
if [ -z "$token" ]; then
  token="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)"
  echo "產生新的 CAIPAN_TOKEN（稍後要填進 GitHub Secrets）"
fi

echo "== 部署中（第一次約 3～5 分鐘）=="
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "CAIPAN_TOKEN=$token" \
  --quiet

url="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo
echo "== 驗證：從 Cloud Run（台灣）抓 $TEST_DATE 的行情 =="

target="https://data.moa.gov.tw/Service/OpenData/FromM/FarmTransData.aspx?StartDate=${TEST_DATE}&EndDate=${TEST_DATE}"
encoded="$(python -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$target")"

code="$(curl -sS -m 90 -o /tmp/caipan_probe.json -w '%{http_code}' \
        -H "X-Caipan-Token: $token" "${url}/?url=${encoded}" || echo 000)"
count="$(python -c 'import json;d=json.load(open("/tmp/caipan_probe.json",encoding="utf-8"));print(len(d) if isinstance(d,list) else -1)' 2>/dev/null || echo -1)"

echo
if [ "$code" = "200" ] && [ "$count" -gt 0 ]; then
  echo "成功：取回 $count 筆。Cloud Run 的台灣出口 IP 沒有被來源擋。"
  echo
  echo "接著把這兩個值填進 GitHub（Settings → Secrets and variables → Actions）："
  echo "  Variables  MOA_PROXY_BASE  = ${url}/?url={url}"
  echo "  Secrets    MOA_PROXY_TOKEN = ${token}"
else
  echo "失敗：HTTP=$code，解析到 $count 筆。"
  echo "若 HTTP 是 502，代表 Cloud Run 的位址同樣被來源擋掉，"
  echo "表示來源是用 ISP 位址段白名單而非 IP 地理位置放行，雲端方案走不通，"
  echo "請改用本機排程或自架 runner。"
  head -c 300 /tmp/caipan_probe.json 2>/dev/null || true
  exit 1
fi
