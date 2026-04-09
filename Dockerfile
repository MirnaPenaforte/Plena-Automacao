# Usar uma imagem base oficial do Python
FROM python:3.11-slim

# Definir o diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema necessárias (ex: para pandas e timezone)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configurar o fuso horário (America/Sao_Paulo)
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copiar os arquivos de requisitos e instalar as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código da aplicação
COPY . .

# Criar os diretórios necessários (caso não existam)
RUN mkdir -p imports output logs

# Comando para rodar a aplicação
# Nota: Se houver um loop de agendamento no main.py, ele continuará rodando.
# Caso contrário, o container será encerrado após a execução única.
CMD ["python", "main.py"]
