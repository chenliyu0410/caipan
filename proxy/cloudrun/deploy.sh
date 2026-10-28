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

# 建置服務帳戶預設交給 Cloud Build 自行選擇（會用專案的預設 Compute 服務帳戶）。
# 新專案的預設 Compute 服務帳戶可能沒有任何角色，建置會在讀取原始碼時被擋，
# 這時請見 proxy/README.md 的「建置權限」一節。要指定自建的服務帳戶，設 BUILD_SA。
build_args=()
if [ -n "${BUILD_SA:-}" ]; then
  build_args+=(--build-service-account "$BUILD_SA")
  echo "建置服務帳戶：${BUILD_SA##*/}"
fi

# 密鑰：沿用既有的，沒有就隨機產生一組
# 注意：不要用 --format='value(...env.filter(...))'，這版 gcloud 的 filter 轉換器會 crash
token="$(gcloud run services describe "$SERVICE" --region "$REGION" --format=json 2>/dev/null \
  | python -c "import json,sys;d=json.load(sys.stdin);e=d['spec']['template']['spec']['containers'][0].get('env',[]);print(next((x.get('value','') for x in e if x.get('name')=='CAIPAN_TOKEN'),''))" 2>/dev/null || true)"
token="$(printf %s "$token" | tr -d "[:space:]")"
if [ -z "$token" ]; then
  token="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)"
  echo "產生新的 CAIPAN_TOKEN（稍後要填進 GitHub Secrets）"
fi

# 預設部署成需要 IAM 驗證的私有服務。要讓 GitHub Actions 直接用共用密鑰呼叫，
# 請自行決定是否開放未驗證存取（見 proxy/README.md）。
echo "== 部署中（第一次約 3～5 分鐘，預設為私有服務）=="
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  "${build_args[@]}" \
  --set-env-vars "CAIPAN_TOKEN=$token" \
  --quiet

url="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo
echo "== 驗證：從 Cloud Run（台灣）抓 $TEST_DATE 的行情 =="

target="https://data.moa.gov.tw/Service/OpenData/FromM/FarmTransData.aspx?StartDate=${TEST_DATE}&EndDate=${TEST_DATE}"
encoded="$(python -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$target")"

trap 'rm -f ./caipan_probe.json' EXIT

# 帶 ID token 呼叫，私有或已開放都能驗；服務已開放時這個標頭會被忽略
idtoken="$(gcloud auth print-identity-token)"
code="$(curl -sS -m 90 -o ./caipan_probe.json -w '%{http_code}' \
        -H "Authorization: Bearer $idtoken" \
        -H "X-Caipan-Token: $token" "${url}/?url=${encoded}" || echo 000)"
count="$(python -c 'import json;d=json.load(open("./caipan_probe.json",encoding="utf-8"));print(len(d) if isinstance(d,list) else -1)' 2>/dev/null || echo -1)"

echo
if [ "$code" = "200" ] && [ "$count" -gt 0 ]; then
  echo "成功：取回 $count 筆。Cloud Run 的台灣出口 IP 沒有被來源擋。"
  echo
  echo "服務網址： ${url}"
  echo "健康檢查： ${url}/ping"
  echo "共用密鑰： 已設定（不輸出到畫面，避免留在終端機捲動紀錄裡）"
  echo
  # IAM 綁定在服務層級，重新部署不會動到它，所以這裡照實查一次目前狀態
  if gcloud run services get-iam-policy "$SERVICE" --region "$REGION" \
       --format='value(bindings.members)' 2>/dev/null | grep -q 'allUsers'; then
    echo "對外存取：已開放未驗證存取，由 X-Caipan-Token 把關。"
    echo "要把密鑰設進 GitHub Secrets，見 proxy/README.md 的「接到 GitHub Actions」。"
  else
    echo "對外存取：目前是私有服務（需要 IAM 驗證），GitHub Actions 還無法呼叫。"
    echo "要開放請執行（見 proxy/README.md 的「對外存取方式」）："
    echo "  gcloud run services add-iam-policy-binding $SERVICE \\"
    echo "      --region $REGION --member=allUsers --role=roles/run.invoker"
  fi
else
  echo "失敗：HTTP=$code，解析到 $count 筆。"
  echo "若 HTTP 是 502，代表 Cloud Run 的位址同樣被來源擋掉，"
  echo "表示來源是用 ISP 位址段白名單而非 IP 地理位置放行，雲端方案走不通，"
  echo "請改用本機排程或自架 runner。"
  head -c 300 ./caipan_probe.json 2>/dev/null || true
  exit 1
fi
