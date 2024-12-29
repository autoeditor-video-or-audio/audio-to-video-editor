import os
import random
from utils import green, logger, removeFolder, verificar_extensao_arquivo, createDir
from minio import Minio
from minio.error import S3Error
import json
from PIL import Image
import numpy as np
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ColorClip, CompositeVideoClip, ImageClip
)
from datetime import datetime

# Inicialização do cliente MinIO
MINIO_URL = os.environ['MINIO_URL']
MINIO_PORT = os.environ['MINIO_PORT']
MINIO_ROOT_USER = os.environ['MINIO_ROOT_USER']
MINIO_ROOT_PASSWORD = os.environ['MINIO_ROOT_PASSWORD']
bucketSet = "autoeditor"
client = Minio(
    f"{MINIO_URL}:{MINIO_PORT}",
    access_key=MINIO_ROOT_USER,
    secret_key=MINIO_ROOT_PASSWORD,
    secure=False,
)

# Função para realizar upload no bucket do MinIO
def postFileInBucket(client, bucketSet, pathDest, pathSrc, contentType=None):
    if pathSrc.endswith('txt'):
        contentType = 'text/plain'
    logger.debug(green(f"Fazendo upload no bucket {bucketSet} arquivo {pathDest}"))
    client.fput_object(bucketSet, pathDest, pathSrc, content_type=contentType)
    logger.debug(green(f"Upload do arquivo {pathSrc} realizado com sucesso."))

# Função para redimensionar imagens
def resize_image(image_path, target_width, target_height, video_duration):
    image = Image.open(image_path)
    resized_image = image.resize((target_width, target_height))
    return ImageClip(np.array(resized_image), duration=video_duration)

# Função para calcular tempos de corte do vídeo de fundo
def getTimeCropBackgroundMovie(background_duration, audio_duration):
    start_time = random.uniform(0, background_duration - audio_duration)
    end_time = start_time + audio_duration
    return round(start_time, 2), round(end_time, 2)

# Função para verificar a existência de arquivos no MinIO
def checkAudioCast():
    logger.debug(green(f"Verificando arquivo no diretório minio: {bucketSet}/files-without-silence/"))
    objects = client.list_objects(bucketSet, prefix="files-without-silence/")

    for obj in objects:
        fileName = obj.object_name.replace('\\', '/').split('/')[-1]

        if verificar_extensao_arquivo(fileName, ".mp3"):
            logger.debug(green(f"Arquivo .mp3 encontrado: {fileName}. Fazendo download..."))
            client.fget_object(bucketSet, obj.object_name, f'./foredit/{fileName}')
            logger.debug(green(f"{fileName} Download realizado com sucesso."))
            return True, "files-without-silence", fileName

    logger.debug(green("Nenhum arquivo .mp3 encontrado no prefixo especificado."))
    return False, '', ''

# Função para baixar vídeos de fundo do bucket MinIO
def downloadMovieBackground():
    bucketSet = "moviebackground"
    logger.debug(green(f"Verificando arquivo no diretório minio: {bucketSet}/vertical/"))

    objects = list(client.list_objects(bucketSet, prefix="vertical/"))
    countFile = len(objects)

    if countFile == 0:
        logger.error("Nenhum arquivo encontrado no bucket moviebackground.")
        return False

    backgroundSorted = random.randint(1, countFile)
    logger.debug(green(f"{backgroundSorted}-BGVertical.mp4 Download iniciado..."))
    client.fget_object(bucketSet, f"vertical/{backgroundSorted}-BGVertical.mp4", "./foredit/BGVertical.mp4")
    logger.debug(green(f"{backgroundSorted}-BGVertical.mp4 Download realizado com sucesso."))
    return True

# Função para criar vídeo a partir do áudio
def createVideoByAudio(audioName, pathName):
    logger.debug(green(f"{audioName} Criando vídeo com base no tempo do áudio..."))
    background_video_path = '/app/foredit/BGVertical.mp4'
    audio_path = f'/app/foredit/{audioName}'

    background_clip = VideoFileClip(background_video_path)
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration

    start_time, end_time = getTimeCropBackgroundMovie(background_clip.duration, audio_duration)
    final_clip = background_clip.subclip(start_time, end_time).set_audio(audio_clip)

    # Nomeando o arquivo com timestamp atual
    current_datetime = datetime.now().strftime("%d-%m-%Y--%H-%M-%S")
    output_filename = f"video_final_{current_datetime}.mp4"
    output_path = f"/app/foredit/{output_filename}"

    final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24)
    logger.debug(green(f"Arquivo {output_filename} criado com sucesso!"))

    # Publicar o vídeo no bucket MinIO
    upload_path = f"files-without-silence/{output_filename}"
    postFileInBucket(client, bucketSet, upload_path, output_path, 'video/mp4')

    # Remover o arquivo .mp3 do bucket MinIO
    try:
        logger.debug(green(f"Removendo o arquivo de áudio {audioName} do bucket {bucketSet}."))
        client.remove_object(bucketSet, f"{pathName}/{audioName}")
        logger.debug(green(f"Arquivo {audioName} removido com sucesso do bucket {bucketSet}."))
    except S3Error as exc:
        logger.error(f"Erro ao remover o arquivo {audioName} do bucket: {exc}")

    # Remove diretórios temporários
    removeFolder("/app/foredit/")

# Função principal para execução do pipeline
def main():
    result, pathName, audioName = checkAudioCast()
    if result:
        logger.debug(green(f"{result}, {pathName}, {audioName}"))

        if not downloadMovieBackground():
            logger.error("Erro ao baixar vídeo de fundo.")
            return

        createVideoByAudio(audioName, pathName)

    logger.debug(green('...FINISHED...'))

if __name__ == "__main__":
    try:
        main()
    except S3Error as exc:
        print("Erro ocorrido.", exc)
