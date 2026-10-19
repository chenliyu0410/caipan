"""
server.py - 菜盤本地測試與預覽伺服器
運行方式：
  python server.py           (預設使用 8080，若被佔用會自動遞增尋找可用 port)
  python server.py 3000      (指定 port 為 3000)
  python server.py 8888      (指定 port 為 8888)
"""

import http.server
import socketserver
import webbrowser
import subprocess
import sys
import os
import mimetypes

DEFAULT_PORT = 8080
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

def get_target_port():
    # 支援命令列指定 port: python server.py 3000
    for arg in sys.argv[1:]:
        if arg.isdigit():
            return int(arg)
        if arg.startswith('--port='):
            val = arg.split('=', 1)[1]
            if val.isdigit():
                return int(val)
    return DEFAULT_PORT

def run_server():
    os.chdir(DIRECTORY)
    start_port = get_target_port()
    port = start_port
    httpd = None

    socketserver.TCPServer.allow_reuse_address = True

    # 若指定 Port 被其他程式佔用，自動嘗試下一個可用 Port
    while port < start_port + 50:
        try:
            httpd = socketserver.TCPServer(("", port), CaipanHandler)
            break
        except OSError:
            print(f"Port {port} 已被佔用，嘗試下一個 Port {port + 1}...")
            port += 1

    if not httpd:
        print(f"錯誤：無法在 {start_port} ~ {port} 範圍內找到可用的 Port！")
        return

    url = f"http://localhost:{port}"
    print(f"==================================================")
    print(f"  菜盤｜蔬果行情與買點推薦 伺服器啟動成功！")
    print(f"  本地網址: {url}")
    print(f"  （可使用參數指定 port，例如：python server.py 3000）")
    print(f"  按 Ctrl + C 可停止伺服器")
    print(f"==================================================")

    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n伺服器已停止。")

if __name__ == '__main__':
    run_server()
