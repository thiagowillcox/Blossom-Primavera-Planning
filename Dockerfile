FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp/blossom-home
WORKDIR /app
COPY requirements.txt ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi \
    && pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 blossom \
    && useradd --uid 10001 --gid blossom --no-create-home blossom
COPY --chown=blossom:blossom app.py ./
COPY --chown=blossom:blossom blossom/ ./blossom/
COPY --chown=blossom:blossom config/ ./config/
COPY --chown=blossom:blossom assets/ ./assets/
COPY --chown=blossom:blossom .streamlit/ ./.streamlit/
USER 10001:10001
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--server.enableCORS=true", "--server.enableXsrfProtection=true"]
