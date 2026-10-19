"""
server.py - 菜盤本地測試與預覽伺服器
運行方式：python server.py
即可在 http://localhost:8000 開啟網站，並支援點擊重新整理或手動觸發爬蟲。
"""

import http.server
import socketserver
import webbrowser
import subprocess
import sys
import os
import mimetypes

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# 註冊常見 MIME 類型
mimetypes.add_type('application/manifest+json', '.webmanifest')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('application/json', '.json')

class CaipanHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        # 支援手動觸發後端爬蟲端點
        if self.path == '/api/refresh':
            print("收到前端手動觸發更新請求，正在執行 fetch_data.py...")
            try:
                result = subprocess.run(
                    [sys.executable, os.path.join(DIRECTORY, 'scripts', 'fetch_data.py')],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(result.stdout)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'{"status":"ok","message":"Market data successfully updated"}')
            except Exception as e:
                print(f"執行爬蟲失敗: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(f'{{"status":"error","message":"{str(e)}"}}'.encode('utf-8'))
            return

        return super().do_GET()

def run_server():
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), CaipanHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"==================================================")
        print(f"  菜盤｜蔬果行情與買點推薦 伺服器啟動成功！")
        print(f"  本地網址: {url}")
        print(f"  請在瀏覽器開啟該網址預覽 PWA 效果")
        print(f"  按 Ctrl + C 可停止伺服器")
        print(f"==================================================")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n伺服器已停止。")

if __name__ == '__main__':
    run_server()
