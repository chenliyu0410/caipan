"""
菜盤行情轉發器（Google Cloud Run，asia-east1 / 台灣彰化）

data.moa.gov.tw 的防火牆只放行台灣 IP。部署在 asia-east1 的 Cloud Run
出口固定在台灣，可代 GitHub Actions 取得資料。相較 Cloudflare Workers 的
Smart Placement（盡力而為），這個方式的落地位置是確定的。

部署：
    cd proxy/cloudrun
    gcloud run deploy caipan-moa-proxy --source . --region asia-east1 \
        --allow-unauthenticated --set-env-vars CAIPAN_TOKEN=<自訂字串>

只用標準函式庫，不需要 requirements.txt。
"""

import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED_HOST = "data.moa.gov.tw"
TOKEN = os.environ.get("CAIPAN_TOKEN", "").strip()


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def reply(self, status: int, body: bytes, content_type: str = "text/plain; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/healthz":
            return self.reply(200, b"ok")

        # 共用密鑰放在標頭而非網址，避免跟著 URL 進到日誌
        if TOKEN and self.headers.get("X-Caipan-Token") != TOKEN:
            return self.reply(403, "Token 不符".encode("utf-8"))

        target = urllib.parse.parse_qs(parsed.query).get("url", [""])[0]
        if not target:
            return self.reply(400, "缺少 url 參數".encode("utf-8"))

        pieces = urllib.parse.urlparse(target)
        # 限定單一來源，避免變成任何人都能用的開放代理
        if pieces.scheme != "https" or pieces.hostname != ALLOWED_HOST:
            return self.reply(403, f"只允許轉發 https://{ALLOWED_HOST}".encode("utf-8"))

        req = urllib.request.Request(target, headers={"User-Agent": "Caipan/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read()
                ctype = resp.headers.get("Content-Type", "application/json; charset=utf-8")
            self.reply(200, body, ctype)
        except urllib.error.HTTPError as e:
            self.reply(e.code, f"來源回應 {e.code}".encode("utf-8"))
        except Exception as e:
            self.reply(502, f"來源連線失敗: {e}".encode("utf-8"))

    def log_message(self, fmt, *args):
        print(fmt % args)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), ProxyHandler).serve_forever()
