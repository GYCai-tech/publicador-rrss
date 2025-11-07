import os
from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired
import PIL.Image
import logging
import tempfile

from pydantic_core import ValidationError

# Configuración de logging para este módulo
logger = logging.getLogger(__name__)

# Cargar credenciales al inicio del módulo
load_dotenv()
username = os.getenv("INSTAGRAM_USERNAME")
password = os.getenv("INSTAGRAM_PASSWORD")
if not username or not password:
    raise ValueError("Credenciales de Instagram (INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD) no encontradas en el fichero .env")

# Usar una variable global para guardar el cliente en memoria y no tener que loguear
# ni leer el fichero en cada llamada dentro del mismo ciclo del scheduler.
_client_instance = None


def get_instagram_client() -> Client:
    """
    Obtiene un cliente de Instagrapi logueado.
    Reutiliza una sesión guardada si existe y es válida.
    Si no, crea una nueva sesión y la guarda para futuros usos.
    """
    global _client_instance

    # Si ya existe un cliente válido en memoria, devolverlo directamente
    if _client_instance:
        logger.info("Reutilizando cliente de Instagram desde la memoria.")
        return _client_instance

    # Si no, crear uno nuevo
    client = Client()
    session_file = "sessions/ig_session.json"

    # Intentar usar una sesión existente
    if os.path.exists(session_file):
        try:
            logger.info(f"Intentando cargar la sesión desde {session_file}...")
            client.load_settings(session_file)
            client.login(username, password)
            logger.info("Sesión reutilizada con éxito.")
            _client_instance = client  # Guardar el cliente en memoria
            return client
        except Exception as e:
            logger.warning(f"La sesión guardada era inválida. Se creará una nueva. Error: {e}")

    # Si no hay sesión o la anterior falló, login completo
    logger.info("Realizando un nuevo login completo en Instagram...")
    try:
        client.login(username, password)
        logger.info("Login en Instagram exitoso. Guardando nueva sesión...")
        client.dump_settings(session_file)
        _client_instance = client  # Guardar el cliente en memoria
        return client
    except Exception as e:
        logger.critical(f"FALLO CRÍTICO: No se pudo iniciar sesión en Instagram. Error: {e}")
        raise e


def post_image_ig(image_path: str, caption: str):
    """Publica una única imagen en Instagram."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"No se encuentra la imagen: {image_path}")
    client = get_instagram_client()
    logger.info(f"Subiendo imagen a Instagram: {image_path}")
    try:
        media = client.photo_upload(path=image_path, caption=caption)
        logger.info("Respuesta del servidor de Instagram (Imagen): %s", media.dict())
        return media.pk
    except ValidationError as e:
        logger.warning(
            f"Publicación de imagen en Instagram completada, pero la respuesta del servidor no pudo ser validada. "
            f"Asumiendo éxito. Error de Pydantic: {e}"
        )
        return True  # Devolver True indica éxito al scheduler


def post_carousel_ig(image_paths: list, caption: str):
    """Publica un carrusel, estandarizando las imágenes para máxima compatibilidad."""
    if not (2 <= len(image_paths) <= 10):
        raise ValueError("El carrusel debe contener entre 2 y 10 imágenes.")

    client = get_instagram_client()
    processed_paths = []
    temp_files_to_clean = []

    logger.info("Procesando y estandarizando imágenes para el carrusel...")
    try:
        for path in image_paths:
            if not os.path.exists(path):
                logger.warning(f"La imagen {path} no existe y será omitida.")
                continue

            try:
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                    temp_path = temp_file.name
                    with PIL.Image.open(path) as img:
                        with img.convert('RGB') as converted_img:
                            converted_img.save(temp_path, 'jpeg', quality=95)

                processed_paths.append(temp_path)
                temp_files_to_clean.append(temp_path)
                logger.info(f"Imagen '{path}' procesada y guardada temporalmente en '{temp_path}'")
            except Exception as e:
                logger.error(f"Error procesando la imagen '{path}': {e}")
                continue

        if not processed_paths:
            raise FileNotFoundError("Ninguna de las imágenes proporcionadas para el carrusel es válida.")

        logger.info(f"Subiendo carrusel a Instagram con {len(processed_paths)} imágenes procesadas.")

        try:
            media = client.album_upload(paths=processed_paths, caption=caption)
            logger.info("Respuesta del servidor de Instagram (Carrusel): %s", media.dict())
            return media.pk
        except ValidationError as e:
            logger.warning(
                f"Publicación de carrusel en Instagram completada, pero la respuesta del servidor no pudo ser validada. "
                f"Asumiendo éxito. Error de Pydantic: {e}"
            )
            return True  # Devolver True indica éxito al scheduler
        except ChallengeRequired as e:
            logger.error("Instagram requiere una verificación de seguridad (ChallengeRequired): %s", e)
            raise Exception("ERROR: La cuenta de Instagram requiere una verificación.")
        except Exception as e:
            logger.error("Error desconocido durante la subida del carrusel: %s", e)
            raise e

    finally:
        # Limpieza de ficheros temporales
        logger.info("Limpiando ficheros de imagen temporales...")
        for temp_path in temp_files_to_clean:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"Fichero temporal '{temp_path}' eliminado.")
                except Exception as e:
                    logger.error(f"No se pudo eliminar el fichero temporal '{temp_path}': {e}")


def post_video_ig(video_path: str, caption: str):
    """Publica un vídeo en Instagram."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"No se encuentra el vídeo: {video_path}")
    client = get_instagram_client()
    logger.info(f"Subiendo vídeo a Instagram: {video_path}")
    try:
        media = client.video_upload(path=video_path, caption=caption)
        logger.info("Respuesta del servidor de Instagram (Vídeo): %s", media.dict())
        return media.pk
    except ValidationError as e:
        logger.warning(
            f"Publicación de vídeo en Instagram completada, pero la respuesta del servidor no pudo ser validada. "
            f"Asumiendo éxito. Error de Pydantic: {e}"
        )
        return True  # Devolver True indica éxito al scheduler
