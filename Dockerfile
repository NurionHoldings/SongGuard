FROM python:3.12-slim
WORKDIR /app
COPY core.py server.py ./
COPY static ./static
RUN useradd --uid 10001 --create-home songguard && mkdir -p /data && chown songguard:songguard /data
USER songguard
ENV SONG_GUARD_DB=/data/songguard.sqlite3 PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health')"
CMD ["python", "server.py"]
