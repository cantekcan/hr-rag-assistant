FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hr_assistant/ hr_assistant/
COPY eval/ eval/

EXPOSE 8000
CMD ["uvicorn", "hr_assistant.api:app", "--host", "0.0.0.0", "--port", "8000"]