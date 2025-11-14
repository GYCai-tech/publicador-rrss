import os
from heyoo import WhatsApp
from dotenv import load_dotenv
import logging
import mimetypes

load_dotenv()

# Configuración
TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('WHATSAPP_BUSINESS_ID')

if not TOKEN or not PHONE_NUMBER_ID:
    raise ValueError("Faltan credenciales de WhatsApp en el entorno (WHATSAPP_TOKEN, WHATSAPP_BUSINESS_ID)")

# Inicializar cliente de WhatsApp
wa_client = WhatsApp(token=TOKEN, phone_number_id=PHONE_NUMBER_ID)


def _upload_media_and_get_url(local_path: str) -> str:
    """
    *** MARCADOR DE POSICIÓN - REQUIERE IMPLEMENTACIÓN ***
    Esta función debe subir el fichero en la ruta local a un servidor
    y devolver una URL pública accesible por los servidores de WhatsApp.

    Ejemplos de implementación:
    - Subir a un bucket de Amazon S3 y obtener la URL pública.
    - Subir a un blob de Azure Storage.
    - Copiar a un directorio público de tu propio servidor web.
    - Para pruebas locales: usar ngrok para exponer un directorio local a internet.

    Por ahora, esta función devolverá un placeholder.
    """
    logging.warning(
        f"La función _upload_media_and_get_url no está implementada. Se usará una URL de placeholder para {local_path}.")
    # Lógica a reemplazar con la implementación real
    return f"https://your-public-server.com/media/{os.path.basename(local_path)}"


def send_whatsapp(recipients: list, message: str, media_path: str = None):
    """
    Envía un mensaje de WhatsApp a una lista de destinatarios,
    adjuntando opcionalmente un único fichero multimedia (imagen o vídeo).
    """
    if not recipients:
        logging.warning("No se proporcionaron destinatarios para WhatsApp.")
        return

    media_type = None
    media_url = None

    if media_path and os.path.exists(media_path):
        mime_type, _ = mimetypes.guess_type(media_path)
        if mime_type:
            if mime_type.startswith('image/'):
                media_type = 'image'
            elif mime_type.startswith('video/'):
                media_type = 'video'

        if media_type:
            # Subir el fichero multimedia y obtener la URL pública
            media_url = _upload_media_and_get_url(media_path)

    for recipient in recipients:
        try:
            if media_type == 'image' and media_url:
                wa_client.send_image(image=media_url, recipient_id=recipient, caption=message)
                logging.info(f"Imagen con mensaje enviada a {recipient}")
            elif media_type == 'video' and media_url:
                wa_client.send_video(video=media_url, recipient_id=recipient, caption=message)
                logging.info(f"Vídeo con mensaje enviado a {recipient}")
            else:
                wa_client.send_message(message=message, recipient_id=recipient)
                logging.info(f"Mensaje de texto enviado a {recipient}")
        except Exception as e:
            logging.error(f"Error al enviar WhatsApp a {recipient}: {e}")
