FROM python:3.9.18-bullseye

# Atualizar e instalar ffmpeg para processamento de vídeo
RUN apt-get -y update && apt-get -y upgrade && apt-get install -y --no-install-recommends libmediainfo0v5 libmediainfo-dev ffmpeg

# Atualizar pip e instalar dependências Python
RUN python -m pip install --upgrade pip

# Definir diretório de trabalho
WORKDIR /app

# Copiar o arquivo requirements.txt e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY ./app/ .

# Definir o ponto de entrada para o script principal
# ENTRYPOINT ["python3", "run.py"]