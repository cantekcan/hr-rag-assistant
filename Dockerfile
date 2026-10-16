FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached when only the code changes
# Exact versions with hashes (regenerate after editing requirements.txt, see README),
# wheels only, so no package runs a setup script during the build
COPY requirements.lock .
RUN pip install --no-cache-dir --only-binary :all: --require-hashes -r requirements.lock

COPY hr_assistant/ hr_assistant/
COPY eval/ eval/
COPY data/ data/
# The regulation and its prebuilt index ship with the image: a free host's disk is wiped on every restart
COPY documents/ documents/
COPY chroma_db/ chroma_db/

# Run without root; the app only writes to the vector store
RUN useradd --create-home --uid 1000 app && chown -R app chroma_db
USER app

EXPOSE 8000
# Hosts like Render pass the port in $PORT. --proxy-headers takes the client address from
# X-Forwarded-For, which the per-client question limit needs behind the host's proxy.
CMD ["sh", "-c", "uvicorn hr_assistant.api:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
