FROM python:3.12-slim

# Evita que o Python gere arquivos .pyc no docker e garante que o log saia em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Primeiro copiamos apenas o requirements para aproveitar o cache de camadas do Docker
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Agora copiamos o restante do código (o .dockerignore filtrará a .venv)
COPY . .

# Garante que as pastas necessárias existam
RUN mkdir -p imports output logs

CMD ["python3", "main.py"]
