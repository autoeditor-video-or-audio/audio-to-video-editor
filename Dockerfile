FROM python:3.9.18-bullseye

# Atualizar e instalar ffmpeg para processamento de vídeo
RUN apt-get -y update && apt-get -y upgrade && apt-get install -y --no-install-recommends libmediainfo0v5 libmediainfo-dev ffmpeg

RUN apt-get update \
    && apt-get install -qq -y build-essential xvfb xdg-utils wget unzip libpq-dev vim libmagick++-dev fonts-liberation sox bc gsfonts --no-install-recommends\
    && apt-get clean

## ImageMagicK Installation 
RUN mkdir -p /tmp/distr && \
    cd /tmp/distr && \
    wget https://download.imagemagick.org/ImageMagick/download/releases/ImageMagick-7.0.11-2.tar.xz && \
    tar xvf ImageMagick-7.0.11-2.tar.xz && \
    cd ImageMagick-7.0.11-2 && \
    ./configure --enable-shared=yes --disable-static --without-perl && \
    make && \
    make install && \
    ldconfig /usr/local/lib && \
    cd /tmp && \
    rm -rf distr \
    rm -rf /var/lib/apt/lists/*

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