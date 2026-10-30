FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); browser = p.chromium.launch(headless=True); browser.close(); p.stop()"
COPY app.py browser.py validation.py ./
RUN mkdir -p /app/output
EXPOSE 8501
CMD ["python","-m","streamlit","run","app.py","--server.address=0.0.0.0","--server.port=8501","--server.headless=true"]
