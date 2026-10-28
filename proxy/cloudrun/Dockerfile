# 本機建置用（備援路徑）。來源只用 Python 標準函式庫，不需要 requirements.txt。
# 專案若因 IAM 權限不足而無法使用 Cloud Build，可改用這個 Dockerfile 在本機
# 建好映像後推送到 Artifact Registry，再以 gcloud run deploy --image 部署。
FROM python:3.12-slim

WORKDIR /app
COPY main.py .

# Cloud Run 會以 PORT 環境變數指定監聽埠，這裡只是本機執行時的預設值
ENV PORT=8080
EXPOSE 8080

CMD ["python", "main.py"]
