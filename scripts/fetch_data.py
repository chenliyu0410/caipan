"""
fetch_data.py - 農業部農產品交易行情抓取與指標計算程式
每日由 GitHub Actions 定時執行，或手動執行更新。
"""

import os
import sys
import json
import ssl
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# 確保輸出支援 UTF-8
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 目標品項定義（與 DEMO 對齊）
CROPS = [
    # id, 官方作物代號偏好, 開放資料名稱, 常用名, 類別, 大類, 基準價, 當季月份, 營養標籤, 預設日均量
    {"id": "C01", "codes": ["LA1", "LA0"], "raw": "甘藍-初秋", "name": "高麗菜", "cat": "葉菜", "type": "veg", "base": 28.0, "season": [10, 11, 12, 1, 2, 3], "tags": ["高纖", "低熱量"], "vol": 320},
    {"id": "C02", "codes": ["LB1", "LB0"], "raw": "小白菜-土白菜", "name": "小白菜", "cat": "葉菜", "type": "veg", "base": 32.0, "season": [10, 11, 12, 1, 2, 3, 4], "tags": ["補鈣", "低熱量"], "vol": 90},
    {"id": "C03", "codes": ["LF2", "LF1"], "raw": "蕹菜-小葉", "name": "空心菜", "cat": "葉菜", "type": "veg", "base": 38.0, "season": [5, 6, 7, 8, 9, 10], "tags": ["補鐵", "高纖"], "vol": 70},
    {"id": "C04", "codes": ["LO1"], "raw": "甘薯葉", "name": "地瓜葉", "cat": "葉菜", "type": "veg", "base": 30.0, "season": [4, 5, 6, 7, 8, 9, 10], "tags": ["補鐵", "高纖"], "vol": 55},
    {"id": "C05", "codes": ["LD1"], "raw": "青江白菜", "name": "青江菜", "cat": "葉菜", "type": "veg", "base": 34.0, "season": [10, 11, 12, 1, 2, 3, 4], "tags": ["補鈣"], "vol": 80},
    {"id": "C06", "codes": ["LH1", "LH2"], "raw": "菠菜", "name": "菠菜", "cat": "葉菜", "type": "veg", "base": 70.0, "season": [11, 12, 1, 2, 3], "tags": ["補鐵"], "vol": 35},
    {"id": "C07", "codes": ["SA1", "SA3", "SA0"], "raw": "蘿蔔", "name": "白蘿蔔", "cat": "根莖", "type": "veg", "base": 20.0, "season": [11, 12, 1, 2, 3], "tags": ["潤燥", "低熱量"], "vol": 120},
    {"id": "C08", "codes": ["SB2", "SB1"], "raw": "胡蘿蔔", "name": "胡蘿蔔", "cat": "根莖", "type": "veg", "base": 32.0, "season": [12, 1, 2, 3, 4], "tags": ["維生素A"], "vol": 110},
    {"id": "C09", "codes": ["SD1", "SD9"], "raw": "洋蔥", "name": "洋蔥", "cat": "根莖", "type": "veg", "base": 26.0, "season": [2, 3, 4, 5], "tags": ["抗氧化"], "vol": 150},
    {"id": "C10", "codes": ["SC1", "SC9"], "raw": "馬鈴薯", "name": "馬鈴薯", "cat": "根莖", "type": "veg", "base": 32.0, "season": [1, 2, 3, 4], "tags": ["飽足"], "vol": 100},
    {"id": "C11", "codes": ["SO1", "SO0"], "raw": "甘薯", "name": "地瓜", "cat": "根莖", "type": "veg", "base": 30.0, "season": [8, 9, 10, 11, 12], "tags": ["高纖", "飽足"], "vol": 85},
    {"id": "C12", "codes": ["FJ3"], "raw": "番茄-牛番茄", "name": "牛番茄", "cat": "瓜果", "type": "veg", "base": 48.0, "season": [12, 1, 2, 3, 4], "tags": ["維生素C", "抗氧化"], "vol": 60},
    {"id": "C13", "codes": ["FC1", "FD1"], "raw": "胡瓜", "name": "小黃瓜", "cat": "瓜果", "type": "veg", "base": 42.0, "season": [4, 5, 6, 7, 8, 9, 10], "tags": ["低熱量", "消暑"], "vol": 75},
    {"id": "C14", "codes": ["FF1", "FF0"], "raw": "絲瓜", "name": "絲瓜", "cat": "瓜果", "type": "veg", "base": 38.0, "season": [5, 6, 7, 8, 9], "tags": ["消暑"], "vol": 65},
    {"id": "C15", "codes": ["FG1", "FG2", "FG0"], "raw": "苦瓜", "name": "苦瓜", "cat": "瓜果", "type": "veg", "base": 45.0, "season": [5, 6, 7, 8, 9, 10], "tags": ["消暑"], "vol": 40},
    {"id": "C16", "codes": ["FI2", "FI0"], "raw": "茄子", "name": "茄子", "cat": "瓜果", "type": "veg", "base": 38.0, "season": [5, 6, 7, 8, 9, 10], "tags": ["抗氧化"], "vol": 45},
    {"id": "C17", "codes": ["FK4", "FK5"], "raw": "甜椒", "name": "甜椒", "cat": "瓜果", "type": "veg", "base": 80.0, "season": [11, 12, 1, 2, 3, 4], "tags": ["維生素C"], "vol": 30},
    {"id": "C18", "codes": ["FB1", "FB2"], "raw": "花椰菜", "name": "花椰菜", "cat": "花果", "type": "veg", "base": 55.0, "season": [11, 12, 1, 2, 3], "tags": ["維生素C", "高纖"], "vol": 50},
    {"id": "C19", "codes": ["FY3", "FY1", "FY0"], "raw": "玉米-甜玉米", "name": "甜玉米", "cat": "花果", "type": "veg", "base": 32.0, "season": [3, 4, 5, 6, 7, 8, 9, 10, 11], "tags": ["飽足"], "vol": 70},
    {"id": "C20", "codes": ["MJ1"], "raw": "杏鮑菇", "name": "杏鮑菇", "cat": "菇類", "type": "veg", "base": 62.0, "season": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "tags": ["高纖", "低熱量"], "vol": 40},
    {"id": "C21", "codes": ["MD1"], "raw": "香菇", "name": "香菇", "cat": "菇類", "type": "veg", "base": 160.0, "season": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "tags": ["免疫"], "vol": 15},
    {"id": "C22", "codes": ["A1", "A0"], "raw": "香蕉", "name": "香蕉", "cat": "水果", "type": "fruit", "base": 32.0, "season": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "tags": ["補鉀", "飽足"], "vol": 160},
    {"id": "C23", "codes": ["P1", "P0"], "raw": "番石榴-珍珠芭", "name": "芭樂", "cat": "水果", "type": "fruit", "base": 42.0, "season": [9, 10, 11, 12, 1, 2, 3], "tags": ["維生素C", "高纖"], "vol": 70},
    {"id": "C24", "codes": ["B2", "B1"], "raw": "鳳梨-金鑽鳳梨", "name": "鳳梨", "cat": "水果", "type": "fruit", "base": 32.0, "season": [3, 4, 5, 6, 7, 8], "tags": ["助消化"], "vol": 110},
    {"id": "C25", "codes": ["I1", "I3"], "raw": "木瓜", "name": "木瓜", "cat": "水果", "type": "fruit", "base": 28.0, "season": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], "tags": ["助消化"], "vol": 60},
    {"id": "C26", "codes": ["E1"], "raw": "柳橙-柳丁", "name": "柳丁", "cat": "水果", "type": "fruit", "base": 32.0, "season": [11, 12, 1, 2], "tags": ["維生素C"], "vol": 80},
    {"id": "C27", "codes": ["H1"], "raw": "文旦柚", "name": "文旦", "cat": "水果", "type": "fruit", "base": 45.0, "season": [8, 9, 10], "tags": ["維生素C"], "vol": 50},
    {"id": "C28", "codes": ["Q1", "Q2"], "raw": "蓮霧", "name": "蓮霧", "cat": "水果", "type": "fruit", "base": 95.0, "season": [12, 1, 2, 3, 4], "tags": ["消暑"], "vol": 25},
    {"id": "C29", "codes": ["R1", "R0"], "raw": "芒果-愛文", "name": "愛文芒果", "cat": "水果", "type": "fruit", "base": 75.0, "season": [5, 6, 7, 8], "tags": ["維生素A"], "vol": 60},
    {"id": "C30", "codes": ["T1", "T0"], "raw": "西瓜", "name": "西瓜", "cat": "水果", "type": "fruit", "base": 22.0, "season": [4, 5, 6, 7, 8], "tags": ["消暑"], "vol": 130},
    {"id": "C31", "codes": ["812", "811"], "raw": "火龍果-紅肉", "name": "火龍果", "cat": "水果", "type": "fruit", "base": 45.0, "season": [6, 7, 8, 9, 10, 11], "tags": ["高纖"], "vol": 45},
    {"id": "C32", "codes": ["51", "50"], "raw": "百香果", "name": "百香果", "cat": "水果", "type": "fruit", "base": 62.0, "season": [7, 8, 9, 10, 11], "tags": ["維生素C"], "vol": 30},
    {"id": "C33", "codes": ["Z4", "Z1"], "raw": "柿子-甜柿", "name": "甜柿", "cat": "水果", "type": "fruit", "base": 70.0, "season": [9, 10, 11], "tags": ["維生素A"], "vol": 35},
    {"id": "C34", "codes": ["O4", "O1"], "raw": "梨-新興", "name": "梨子", "cat": "水果", "type": "fruit", "base": 60.0, "season": [7, 8, 9, 10], "tags": ["潤燥"], "vol": 40},
]

# 目標批發市場（包含代號與名稱比對）
MARKETS = [
    {"id": "109", "name": "台北一", "aliases": ["台北一", "109", "台北第一"]},
    {"id": "104", "name": "台北二", "aliases": ["台北二", "104", "台北第二"]},
    {"id": "241", "name": "三重", "aliases": ["三重", "三重區", "241"]},
    {"id": "220", "name": "板橋", "aliases": ["板橋", "板橋區", "220"]},
    {"id": "400", "name": "台中", "aliases": ["台中", "台中市", "400"]},
    {"id": "800", "name": "高雄", "aliases": ["高雄", "高雄市", "800"]},
    {"id": "648", "name": "西螺", "aliases": ["西螺", "西螺鎮", "648"]},
]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
LATEST_FILE = os.path.join(DATA_DIR, "latest.json")

def to_roc_date(dt: datetime) -> str:
    """西元日期轉民國格式：115.10.19"""
    roc_year = dt.year - 1911
    return f"{roc_year}.{dt.month:02d}.{dt.day:02d}"

def from_roc_date(roc_str: str) -> datetime:
    """民國格式轉西元日期"""
    parts = roc_str.strip().split(".")
    year = int(parts[0]) + 1911
    month = int(parts[1])
    day = int(parts[2])
    return datetime(year, month, day)

# 來源站台只開放台灣 IP，GitHub Actions 的 runner 在境外會被防火牆直接丟包。
# MOA_PROXY_BASE 可填一個或多個（逗號分隔）落地台灣的轉發網址，依序嘗試；
# 範本中的 {url} 會替換成 URL-encode 後的目標網址，沒寫就直接接在結尾。
#   例：https://caipan-moa-proxy.xxx.workers.dev/?url={url}
# 未設定時只走直連，本機在台灣執行即可。
SOURCE_URL = "https://data.moa.gov.tw/Service/OpenData/FromM/FarmTransData.aspx?StartDate={roc}&EndDate={roc}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Caipan/1.0"

_preferred_route = None     # 已確認可用的路由，後續日期優先重用
_all_routes_failed = False  # 第一個日期就全軍覆沒，後面不再浪費逾時時間

def reset_route_cache():
    """清掉路由記憶，供測試與重跑使用"""
    global _preferred_route, _all_routes_failed
    _preferred_route = None
    _all_routes_failed = False

def build_routes(roc_date: str):
    """組出這個日期要嘗試的連線路由，代理優先、直連墊底"""
    target = SOURCE_URL.format(roc=roc_date)
    quoted = urllib.parse.quote(target, safe="")
    routes = []
    for raw in os.environ.get("MOA_PROXY_BASE", "").split(","):
        template = raw.strip()
        if not template:
            continue
        if "{url}" in template:
            routes.append(("代理", template.replace("{url}", quoted)))
        else:
            routes.append(("代理", template.rstrip("/") + "/" + quoted))
    # 沒設代理就只能直連；有設代理時仍保留直連當最後手段（可用 MOA_ALLOW_DIRECT=0 關掉）
    if not routes or os.environ.get("MOA_ALLOW_DIRECT", "1") != "0":
        routes.append(("直連", target))
    if _preferred_route:
        routes.sort(key=lambda route: route[0] != _preferred_route)
    return routes

def request_market_json(url: str):
    """送出單次請求並驗證回傳格式"""
    headers = {"User-Agent": USER_AGENT}
    token = os.environ.get("MOA_PROXY_TOKEN", "").strip()
    if token:
        headers["X-Caipan-Token"] = token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=float(os.environ.get("MOA_TIMEOUT", "45"))) as resp:
        content = resp.read().decode("utf-8")
    items = json.loads(content)
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError("API 回傳格式不正確")
    return items

def fetch_moa_date(roc_date: str, retries: int = 3):
    """抓取農業部單一日期所有交易行情，某條路由不通就換下一條"""
    global _preferred_route, _all_routes_failed
    attempts = 1 if _all_routes_failed else retries
    last_error = None
    for label, url in build_routes(roc_date):
        for attempt in range(attempts):
            try:
                items = request_market_json(url)
                if _preferred_route != label:
                    print(f"[{roc_date}] 改用{label}路由取得資料")
                _preferred_route = label
                _all_routes_failed = False
                return items
            except Exception as e:
                last_error = e
                if attempt < attempts - 1:
                    print(f"[{roc_date}] {label}第 {attempt + 1} 次失敗，稍後重試: {e}")
                    time.sleep(min(2 ** (attempt + 1), 8))
        print(f"[{roc_date}] {label}路由不通: {last_error}")
    if _preferred_route is None:
        _all_routes_failed = True
    print(f"[{roc_date}] 抓取失敗: {last_error}")
    return None

def find_matched_crop(raw_crop_code: str, raw_crop_name: str):
    """比對開放資料紀錄是否屬於我們追蹤的 34 項作物"""
    clean_code = (raw_crop_code or "").strip()
    clean_name = (raw_crop_name or "").strip()
    for crop in CROPS:
        # 1. 優先精準比對作物代號
        if clean_code in crop["codes"]:
            return crop
    for crop in CROPS:
        # 2. 次要比對作物名稱
        if crop["name"] in clean_name or crop["raw"].split("-")[0] in clean_name:
            return crop
    return None

def find_matched_market(raw_mk_code: str, raw_mk_name: str):
    """比對開放資料紀錄是否屬於我們追蹤的市場"""
    code = (raw_mk_code or "").strip()
    name = (raw_mk_name or "").strip()
    for m in MARKETS:
        if code == m["id"] or any(alias in name for alias in m["aliases"]):
            return m["id"]
    return None

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"讀取 history.json 失敗: {e}")
    return {"dates": [], "records": {}}

def save_history(history):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def update_history_data(days_back: int = 40):
    """抓取並更新歷史資料庫"""
    history = load_history()
    existing_dates = set(history.get("dates", []))
    records = history.get("records", {})

    now = datetime.now(ZoneInfo("Asia/Taipei"))
    dates_to_fetch = []
    failed_dates = []
    successful_dates = []
    
    # 決定抓取的日期清單（由舊到新）
    for i in range(days_back, -1, -1):
        d = now - timedelta(days=i)
        roc = to_roc_date(d)
        # 如果該日期不在現有紀錄中，或是最近 3 天（重新抓取最新修正與確認開市）
        if roc not in existing_dates or i <= 2:
            dates_to_fetch.append((d, roc))

    print(f"準備更新 {len(dates_to_fetch)} 個日期的交易數據...")

    # 優先取得最新行情，再補查歷史缺漏。
    for d, roc in reversed(dates_to_fetch):
        print(f"正在查詢 {roc} ({d.strftime('%Y-%m-%d')})...")
        raw_items = fetch_moa_date(roc)
        if raw_items is None:
            failed_dates.append(roc)
            continue
        successful_dates.append(roc)
        
        # 檢查是否全為休市
        active_items = [x for x in raw_items if x.get("作物名稱") != "休市"]
        if not active_items:
            print(f"  {roc}: 全市場休市或無交易")
            continue
        
        # 整理當天資料：記錄 key = "marketId_cropId"
        # 結構：{o, h, l, c, v}
        day_matched = 0
        for item in active_items:
            mk_id = find_matched_market(item.get("市場代號"), item.get("市場名稱"))
            if not mk_id:
                continue
            crop = find_matched_crop(item.get("作物代號"), item.get("作物名稱"))
            if not crop:
                continue
            
            try:
                avg_px = float(item.get("平均價", 0.0) or 0.0)
                high_px = float(item.get("上價", 0.0) or 0.0)
                low_px = float(item.get("下價", 0.0) or 0.0)
                vol = float(item.get("交易量", 0.0) or 0.0)
            except (ValueError, TypeError):
                continue
            
            if avg_px <= 0.0:
                continue

            k = f"{mk_id}_{crop['id']}"
            if k not in records:
                records[k] = {}

            # 如果當天已有一筆紀錄（例如同作物不同細項規格），以交易量大或優先代碼為準
            if roc not in records[k] or vol > records[k][roc].get("v", 0):
                records[k][roc] = {
                    "h": round(high_px if high_px > 0 else avg_px * 1.05, 1),
                    "l": round(low_px if low_px > 0 else avg_px * 0.95, 1),
                    "c": round(avg_px, 1),
                    "v": round(vol / 1000.0, 1) if vol > 200 else round(vol, 1)
                }
                day_matched += 1

        if day_matched > 0:
            if roc not in existing_dates:
                history["dates"].append(roc)
                existing_dates.add(roc)
            print(f"  {roc}: 成功匹配 {day_matched} 筆指定作物行情")
        else:
            print(f"  {roc}: 今日休市或無目標蔬果拍賣數據")
        time.sleep(0.3)

    # 排序日期（只保留至少有撮合資料的真實交易日）
    valid_dates = [d for d in history["dates"] if any(d in rec for rec in records.values())]
    history["dates"] = sorted(list(set(valid_dates)), key=lambda x: [int(p) for p in x.split(".")])
    # 保留最近 75 個交易日
    if len(history["dates"]) > 75:
        history["dates"] = history["dates"][-75:]
    history["records"] = records
    
    save_history(history)
    print(f"歷史資料更新完成，共保留 {len(history['dates'])} 個有效交易日！")
    return {"failed_dates": failed_dates, "successful_dates": successful_dates, "route": _preferred_route}

def rsi(series_c, n=14):
    """計算 RSI(14)"""
    if len(series_c) < n + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(len(series_c) - n, len(series_c)):
        diff = series_c[i] - series_c[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    if losses == 0:
        return 100.0
    rs = gains / losses
    return round(100.0 - (100.0 / (1.0 + rs)), 1)

def build_latest_dataset(fetch_status):
    """依據最新歷史資料，計算均線、RSI、買點評分並產出最新前端專用 JSON"""
    history = load_history()
    dates = history.get("dates", [])
    records = history.get("records", {})
    
    if not dates:
        print("沒有歷史資料可供計算！")
        return None

    latest_roc = dates[-1]
    latest_dt = from_roc_date(latest_roc)
    wk_names = ["一", "二", "三", "四", "五", "六", "日"]
    weekday_str = wk_names[latest_dt.weekday()]
    formatted_date = f"{latest_dt.year}/{latest_dt.month:02d}/{latest_dt.day:02d}（{weekday_str}）"

    output = {
        "updated_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
        "fetch_status": fetch_status,
        "trade_date": latest_roc,
        "formatted_date": formatted_date,
        "is_real_data": True,
        "dates": dates,
        "markets": MARKETS,
        "crops": CROPS,
        "market_data": {}
    }

    for mk in MARKETS:
        mk_id = mk["id"]
        crop_analyses = []
        
        for crop in CROPS:
            k = f"{mk_id}_{crop['id']}"
            crop_recs = records.get(k, {})
            
            # 建立每個日期的完整時間序列（缺失日用前日遞補或基準價）
            series = []
            prev_price = crop["base"]
            
            for d in dates:
                if d in crop_recs:
                    pt = crop_recs[d]
                    pt_c = pt["c"]
                    pt_h = pt.get("h", pt_c * 1.05)
                    pt_l = pt.get("l", pt_c * 0.95)
                    pt_v = pt.get("v", crop["vol"])
                    pt_o = prev_price
                    prev_price = pt_c
                    series.append({"o": round(pt_o, 1), "h": round(pt_h, 1), "l": round(pt_l, 1), "c": round(pt_c, 1), "v": round(pt_v, 1)})
                else:
                    # 當日該市場未交易此品項，沿用前價
                    series.append({"o": round(prev_price, 1), "h": round(prev_price * 1.02, 1), "l": round(prev_price * 0.98, 1), "c": round(prev_price, 1), "v": round(crop["vol"] * 0.5, 1)})

            # 指標計算
            cur_pt = series[-1]
            yesterday_pt = series[-2] if len(series) >= 2 else cur_pt
            
            chg = round(cur_pt["c"] - yesterday_pt["c"], 1)
            pct = round((chg / yesterday_pt["c"]) * 100.0, 1) if yesterday_pt["c"] > 0 else 0.0

            close_prices = [p["c"] for p in series]
            volumes = [p["v"] for p in series]

            # 5日均線、20日均線
            ma5 = round(sum(close_prices[-5:]) / min(5, len(close_prices)), 1)
            ma20 = round(sum(close_prices[-20:]) / min(20, len(close_prices)), 1)

            # 60日價格區間
            window_60 = close_prices[-60:]
            lo_60 = min(window_60)
            hi_60 = max(window_60)
            avg_60 = round(sum(window_60) / len(window_60), 1)

            # 價格相對位置 (Rank: 0.0 = 最低點, 1.0 = 最高點)
            lower_count = sum(1 for v in window_60 if v < cur_pt["c"])
            rank = lower_count / max(1, (len(window_60) - 1))

            # RSI(14)
            rsi_val = rsi(close_prices, 14)

            # 到貨量比率（相較於近20日均量）
            vol_20_avg = sum(volumes[-20:]) / min(20, len(volumes))
            vr = round(cur_pt["v"] / vol_20_avg, 2) if vol_20_avg > 0 else 1.0

            # 是否當季
            in_season = latest_dt.month in crop["season"]

            # 買點評分系統 (0~100)
            score = 0
            reasons = []

            # 1. 便宜程度權重 (最多 40 分)
            score += (1.0 - rank) * 40.0
            if rank <= 0.2:
                cheaper_pct = round((1.0 - rank) * 100)
                reasons.append(f"價格在近 60 日低檔（比 {cheaper_pct}% 的日子便宜）")

            # 2. 當季盛產 (20 分)
            if in_season:
                score += 20.0
                reasons.append("當季盛產，品質與產量最佳")

            # 3. 跌破 20 日均線 (最多 20 分)
            below_ma20 = (ma20 - cur_pt["c"]) / ma20 if ma20 > 0 else 0
            if below_ma20 > 0:
                score += min(1.0, below_ma20 / 0.15) * 20.0
                if below_ma20 > 0.05:
                    reasons.append(f"比 20 日均價便宜 {round(below_ma20 * 100)}%")
            elif below_ma20 < -0.08:
                reasons.append(f"比 20 日均價高 {round(-below_ma20 * 100)}%")

            # 4. RSI 短線指標 (最多 10 分)
            if rsi_val < 30:
                score += 10.0
                reasons.append(f"RSI {rsi_val}，短線超賣跌深")
            elif rsi_val < 40:
                score += 5.0

            # 5. 到貨量充足 (最多 10 分)
            if vr > 1.15:
                score += 10.0
                reasons.append("今日到貨量充足，市場供應旺盛")
            elif vr > 1.0:
                score += 5.0

            final_score = int(round(score))
            level = "buy" if final_score >= 70 else ("watch" if final_score >= 50 else ("pricey" if rank >= 0.8 else "hold"))

            crop_analyses.append({
                "crop": crop,
                "t": cur_pt,
                "y": yesterday_pt,
                "chg": chg,
                "pct": pct,
                "ma5": ma5,
                "ma20": ma20,
                "lo": lo_60,
                "hi": hi_60,
                "avg60": avg_60,
                "rank": round(rank, 2),
                "rsi": rsi_val,
                "vr": vr,
                "score": final_score,
                "reasons": reasons,
                "level": level,
                "in_season": in_season,
                "spark": close_prices[-20:],
                "series": series[-60:] # 提供近 60 日 K 線
            })

        output["market_data"][mk_id] = {
            "analyses": crop_analyses
        }

    with open(LATEST_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"成功生成最新市場 JSON: {LATEST_FILE}（更新日期：{formatted_date}）")
    return output

if __name__ == "__main__":
    print("=== 菜盤：農業部行情數據更新開始 ===")
    report = update_history_data(days_back=35)
    fetch_status = {
        "state": "failed" if not report["successful_dates"] else ("partial" if report["failed_dates"] else "ok"),
        **report,
    }
    dataset = build_latest_dataset(fetch_status)
    if report["failed_dates"] or dataset is None:
        print("::error::行情抓取不完整，已保留可用行情並記錄失敗日期；請檢查來源連線。")
        sys.exit(1)
    print("=== 所有更新工作完成 ===")
