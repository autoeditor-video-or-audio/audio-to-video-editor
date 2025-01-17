import os
import json
import random
import logging
from datetime import datetime
from utils import green, logger, removeFolder, createDir
from minio import Minio
from minio.error import S3Error
import pika
from moviepy.editor import (
    VideoFileClip, AudioFileClip
)

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Disable pika debug logs, setting them to WARNING or higher
logging.getLogger("pika").setLevel(logging.WARNING)

# Configuração do RabbitMQ
rabbitmq_host = os.getenv('RABBITMQ_HOST', '')
rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
rabbitmq_vhost = os.getenv('RABBITMQ_VHOST', '')
rabbitmq_user = os.getenv('RABBITMQ_USER', '')
rabbitmq_pass = os.getenv('RABBITMQ_PASS', '')
rabbitmq_queue = '02_mp3_to_video'

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

def connect_to_rabbitmq():
    """Conecta ao RabbitMQ."""
    try:
        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
        parameters = pika.ConnectionParameters(
            host=rabbitmq_host,
            port=rabbitmq_port,
            virtual_host=rabbitmq_vhost,
            credentials=credentials,
            heartbeat=120,  # Aumentar o tempo do heartbeat
            blocked_connection_timeout=1800
        )
        return pika.BlockingConnection(parameters)
    except Exception as e:
        logger.error(f"Erro ao conectar ao RabbitMQ: {str(e)}")
        return None

def download_file_from_minio(bucket_path, local_path):
    """Baixa o arquivo especificado do MinIO."""
    logger.info(f"Iniciando download do arquivo: {bucket_path}")
    try:
        client.fget_object(bucketSet, bucket_path, local_path)
        logger.info(f"Arquivo baixado com sucesso: {local_path}")
        return local_path
    except S3Error as e:
        logger.error(f"Erro ao baixar o arquivo do MinIO: {e}")
        return None

def postFileInBucket(client, bucketSet, pathDest, pathSrc, contentType=None):
    """Faz upload de um arquivo para o bucket MinIO."""
    try:
        client.fput_object(bucketSet, pathDest, pathSrc, content_type=contentType)
        logger.info(f"Upload realizado com sucesso: {pathDest}")
    except S3Error as e:
        logger.error(f"Erro ao fazer upload para o MinIO: {e}")

def getTimeCropBackgroundMovie(background_duration, audio_duration):
    """Calcula os tempos de corte do vídeo de fundo."""
    start_time = random.uniform(0, background_duration - audio_duration)
    end_time = start_time + audio_duration
    return round(start_time, 2), round(end_time, 2)

def download_random_background_video(file_category):
    """Baixa um vídeo de fundo aleatório do bucket MinIO."""
    bucketSet = "moviebackground"
    logger.info(f"Verificando arquivos no bucket: {bucketSet}/vertical/{file_category}")
    objects = list(client.list_objects(bucketSet, prefix=f"vertical/{file_category}/"))

    if not objects:
        logger.error("Nenhum arquivo de fundo encontrado no bucket.")
        return None

    random_object = random.choice(objects)
    background_video_path = f"/app/foredit/{random_object.object_name.split('/')[-1]}"

    try:
        client.fget_object(bucketSet, random_object.object_name, background_video_path)
        logger.info(f"Arquivo de fundo baixado: {background_video_path}")
        return background_video_path
    except S3Error as e:
        logger.error(f"Erro ao baixar o arquivo de fundo: {e}")
        return None

def publish_to_queue(queue_name, message):
    """Publica uma mensagem na fila especificada do RabbitMQ."""
    connection = connect_to_rabbitmq()
    if connection is None:
        logger.error("Não foi possível conectar ao RabbitMQ para publicar mensagem.")
        return False

    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)  # Mensagem persistente
        )
        logger.info(f"Mensagem publicada na fila {queue_name}: {message}")
        return True
    except Exception as e:
        logger.error(f"Erro ao publicar mensagem na fila {queue_name}: {e}")
        return False
    finally:
        connection.close()

# Ajuste na função `createVideoByAudio` para incluir a publicação na fila `03_mp3_to_video`
def createVideoByAudio(audioName, pathName, file_category):
    """Cria um vídeo com base no áudio recebido."""
    try:
        logger.info(f"{audioName} Criando vídeo com base no tempo do áudio...")

        background_video_path = download_random_background_video(file_category)
        if not background_video_path:
            logger.error("Erro ao baixar o vídeo de fundo. Processo abortado.")
            return

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
        logger.info(f"Arquivo {output_filename} criado com sucesso!")

        # Publicar o vídeo no bucket MinIO
        upload_path = f"processed-videos/{output_filename}"
        postFileInBucket(client, bucketSet, upload_path, output_path, 'video/mp4')

        # Publicar mensagem na fila `03_mp3_to_video` no formato especificado
        process_start_date = datetime.now().isoformat()
        file_name_highlight = output_filename.rsplit(".", 1)[0]
        segment_data = {
            "file_format": "mp3",
            "file_name": f"{file_name_highlight}.mp3",
            "bucket_path": f"processed-videos/{file_name_highlight}.mp3",
            "process_start_date": process_start_date,
            "category": file_category,
        }
        if publish_to_queue("03_mp3_to_video", segment_data):
            logger.info("Mensagem publicada na fila 03_mp3_to_video com sucesso.")
        else:
            logger.error("Erro ao publicar mensagem na fila 03_mp3_to_video.")

        # Remove o arquivo de áudio original
        logger.info(f"Removendo o arquivo de áudio {audioName} do bucket {bucketSet}.")
        client.remove_object(bucketSet, f"{pathName}/{audioName}")
        return True
    except Exception as exc:
        logger.error(f"Erro ao processar {audioName}: {exc}")
        return False
    finally:
        # Remove diretórios temporários
        removeFolder("/app/foredit/")

def process_message(message):
    """Processa uma mensagem recebida da fila RabbitMQ."""
    logger.info("Iniciando processamento da mensagem.")
    try:
        bucket_path = message.get("bucket_path")
        file_name = message.get("file_name")
        file_category = message.get("category")

        if not bucket_path or not file_name:
            logger.error("Mensagem inválida. Campos obrigatórios ausentes.")
            return

        # Caminhos para download e processamento
        local_audio_path = f"/app/foredit/{file_name}"
        download_file_from_minio(bucket_path, local_audio_path)

        # Processar vídeo com base no áudio
        success = createVideoByAudio(file_name, bucket_path, file_category)
        
        if not success:
            logger.error("Erro ao criar o vídeo. Mensagem não será removida da fila.")
            return
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")

def consume_messages():
    """Consome mensagens da fila RabbitMQ."""
    connection = connect_to_rabbitmq()
    if connection is None:
        return

    try:
        channel = connection.channel()
        channel.queue_declare(queue=rabbitmq_queue, durable=True)

        def callback(ch, method, properties, body):
            message = json.loads(body.decode())
            process_message(message)
            try:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info("Mensagem processada com sucesso e removida da fila.")
            except Exception as e:
                logger.error(f"Erro ao confirmar processamento da mensagem: {e}")

        channel.basic_consume(queue=rabbitmq_queue, on_message_callback=callback)
        logger.info("Aguardando mensagens na fila...")
        channel.start_consuming()
    except Exception as e:
        logger.error(f"Erro ao consumir mensagens: {e}")
    finally:
        if connection and connection.is_open:
            connection.close()

if __name__ == "__main__":
    try:
        logger.info("Iniciando consumidor de mensagens...")
        consume_messages()
    except Exception as e:
        logger.error(f"Erro na aplicação: {e}")
