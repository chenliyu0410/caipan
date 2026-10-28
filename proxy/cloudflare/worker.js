/**
 * 菜盤行情轉發器（Cloudflare Workers）
 *
 * data.moa.gov.tw 的防火牆只放行台灣 IP，GitHub Actions 的 runner 在境外會被直接丟包，
 * 這支 Worker 代為向來源取資料再回傳。
 *
 * 已知限制：本專案用不了這支 Worker。Smart Placement 需要「來自多個地點的持續流量」
 * 才會搬移執行點，而且只能選擇 Worker 已經執行過的地點；本專案每天只有 4～8 次請求、
 * 全部來自同一個境外 runner，會得到 INSUFFICIENT_INVOCATIONS，永遠搬不到台灣。
 * 請改用 proxy/cloudrun（GCP asia-east1，落點固定在台灣彰化）。
 * 轉發邏輯本身是好的，程式碼保留供日後流量型態改變時使用。
 */
const ALLOWED_HOST = "data.moa.gov.tw";

export default {
  async fetch(request, env) {
    if (request.method !== "GET") {
      return new Response("只接受 GET", { status: 405 });
    }

    // 共用密鑰放在標頭而非網址，避免跟著 URL 進到日誌或快取鍵。未設定時不檢查。
    const token = (env.CAIPAN_TOKEN || "").trim();
    if (token && request.headers.get("X-Caipan-Token") !== token) {
      return new Response("Token 不符", { status: 403 });
    }

    const raw = new URL(request.url).searchParams.get("url");
    if (!raw) {
      return new Response("缺少 url 參數", { status: 400 });
    }

    let target;
    try {
      target = new URL(raw);
    } catch {
      return new Response("url 參數格式錯誤", { status: 400 });
    }
    // 限定單一來源，避免變成任何人都能用的開放代理
    if (target.protocol !== "https:" || target.hostname !== ALLOWED_HOST) {
      return new Response("只允許轉發 https://" + ALLOWED_HOST, { status: 403 });
    }

    try {
      const upstream = await fetch(target.toString(), {
        headers: { "User-Agent": "Caipan/1.0" },
        cf: { cacheTtl: 300, cacheEverything: true },
      });
      return new Response(upstream.body, {
        status: upstream.status,
        headers: {
          "Content-Type":
            upstream.headers.get("Content-Type") || "application/json; charset=utf-8",
          "Cache-Control": "public, max-age=300",
        },
      });
    } catch (e) {
      return new Response("來源連線失敗: " + e, { status: 502 });
    }
  },
};
