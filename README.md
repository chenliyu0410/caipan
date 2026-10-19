# 菜盤 (Caipan) ｜ 蔬果行情與買點推薦

> **用農業部農產品拍賣行情，像看股票一樣看菜價，挑今天值得買的蔬果。**  
> 支援 **PWA 手機免安裝直接存桌面** ＋ **GitHub Actions 免費雲端每日自動抓取與更新**。

---

## 🌟 核心特點

1. **手機免上架 App Store / Google Play**：
   - 採用標準 **PWA（Progressive Web App）** 技術。
   - 用 iPhone 或 Android 開啟網頁後，點擊「加入主畫面 / 安裝至桌面」，桌面就會產生專屬 App 圖示。
   - 點開直接全螢幕獨立運行（無網址列干擾），支援離線快取與秒開體驗！
2. **100% 免費雲端每日自動排程更新**：
   - 使用 **GitHub Actions** 定時 Cron 工作流，完全零伺服器成本、免綁信用卡。
   - 每日早上 08:00 自動向農業部開放資料 API 抓取最新拍賣行情。
   - 計算 5 日均線、20 日均線、RSI、近 60 日價格百分位，自動產出評分與推薦榜單並發布至 **GitHub Pages**。
3. **股票級分析指標**：
   - 即時跑馬燈、大盤指數（蔬菜/水果總體漲跌、推薦買點數、自選關注觸發）。
   - 「今天值得買」智慧標籤過濾（依想吃的菜種、身體需要營養推薦）。
   - 完整 K 線圖（包含上價、下價、均價、成交量、目標價提醒虛線與互動數值 Tooltip）。

---

## 🚀 免費雲端部署步驟（只需 3 分鐘）

本專案完全為 **GitHub Actions + GitHub Pages** 設計，不需要租用任何伺服器或負擔費用。

### 第一步：建立 GitHub 儲存庫並上傳代碼
在本地專案目錄 `caipan` 下打開命令提示字元（CMD 或 PowerShell），執行以下指令：

```bash
git init
git add .
git commit -m "feat: 初次建立菜盤 PWA 與每日自動排程"
git branch -M main
```

前往 [GitHub.com](https://github.com) 建立一個新的公開儲存庫（例如命名為 `caipan`），接著執行：

```bash
git remote add origin https://github.com/<你的GitHub帳號>/caipan.git
git push -u origin main
```

---

### 第二步：啟用 GitHub Pages（免費網站託管）
1. 進入你的 GitHub 儲存庫頁面。
2. 點擊上方的 **Settings** ➔ 左側選單選擇 **Pages**。
3. 在 **Build and deployment** 下方的 **Source** 選擇：
   - 選擇 **Deploy from a branch**。
   - Branch 選擇 **main**，資料夾選擇 **/ (root)**。
   - 點擊 **Save**。
4. 等待 1~2 分鐘，上方會出現你的專屬網址：
   `https://<你的GitHub帳號>.github.io/caipan/`

---

### 第三步：啟用每日自動更新權限（GitHub Actions）
為了讓 GitHub Actions 機器人可以每日自動將更新後的行情資料推送到儲存庫中：
1. 在儲存庫頁面點擊 **Settings** ➔ 左側選單點擊 **Actions** ➔ **General**。
2. 捲動到最下方的 **Workflow permissions**：
   - 勾選 **Read and write permissions**（允許工作流程寫入）。
3. 點擊 **Save** 保存。

> 💡 **自動執行時間**：
> 系統預設排程在台灣時間每日早上 `08:00` 與中午 `12:00` 自動爬取更新。  
> 你也可以在 GitHub 的 **Actions** 分頁中，隨時點擊 **「每日自動更新農產品行情數據」** ➔ **Run workflow** 進行手動即時更新！

---

## 📱 手機存到桌面使用教學（免上架 App Store）

當你在手機瀏覽器打開部署好的網址（例如 `https://<你的GitHub帳號>.github.io/caipan/`）：

### 🍎 iPhone / iPad（使用 Safari 瀏覽器）
1. 點擊螢幕下方工具列中央的 **「分享」** 圖示（方框向上箭頭 📤）。
2. 往下滑動選單，點選 **「加入主畫面」**（Add to Home Screen ＋）。
3. 右上角點擊 **「新增」**。
4. 手機桌面即會出現 **「菜盤」** App 圖示，點擊即可像原生 App 一樣全螢幕開啟用！

### 🤖 Android 安卓手機（使用 Chrome / Edge 瀏覽器）
1. 點擊畫面上方的 **「📱 加到手機桌面」** 按鈕，或點擊瀏覽器右上角的 **「⋮」選單**。
2. 點選 **「安裝應用程式」** 或 **「新增至主畫面」**。
3. 確認後，桌面立即產生 App 圖示。

---

## 💻 本地測試與預覽

如果你想在自己的電腦上預覽或除錯：

1. 確保電腦安裝有 Python 3：
```bash
python server.py
```
2. 瀏覽器會自動開啟 `http://localhost:8000`。
3. 手動更新本地數據測試：
```bash
python scripts/fetch_data.py
```

---

## 📂 專案檔案結構

```
caipan/
├── index.html                  # 菜盤 PWA 前端網頁（支援即時資料與離線快取）
├── manifest.webmanifest         # PWA 應用程式設定清單（圖示、全螢幕顯示、主題色）
├── sw.js                       # Service Worker（支援離線運行與快速載入）
├── server.py                   # 本地預覽測試伺服器
├── icons/                      # 高解析度 PWA 圖示
│   ├── favicon.svg             # 網站 SVG 圖標
│   ├── icon-192.png           # 192x192 應用圖標
│   ├── icon-512.png           # 512x512 高清圖標
│   └── apple-touch-icon.png   # iOS 專用主畫面圖標
├── data/
│   ├── latest.json             # 經計算後的最新行情與評分資料（前端直接讀取）
│   └── history.json            # 歷史拍賣交易紀錄（滾動保留 75 個交易日）
├── scripts/
│   ├── fetch_data.py           # 農業部行情爬蟲與指標計算引擎
│   └── generate_icons.py       # PWA 圖示生成腳本
└── .github/
    └── workflows/
        └── daily_update.yml    # GitHub Actions 免費每日定時更新工作流
```

---

## 🌾 資料來源與授權說明
- 資料來源：中華民國農業部「農產品交易行情」開放資料（`https://data.moa.gov.tw/`）。
- 依據政府資料開放平臺授權條款規範使用。
