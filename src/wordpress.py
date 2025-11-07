from __future__ import annotations
import base64
import os
from typing import Iterable
import requests
from dotenv import load_dotenv
import mimetypes
import logging
import json

# Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Carga de variables de entorno
WP_SITE = os.getenv("WP_SITE", "").rstrip("/")
WP_USER = os.getenv("WP_USER", "").rstrip("/")
WP_APP_PASS = (os.getenv("WP_APP_PASS", "").replace(" ", "").rstrip("."))

if not all((WP_SITE, WP_USER, WP_APP_PASS)):
    error_msg = "Faltan variables de entorno para WordPress. Asegúrate de que WP_SITE, WP_USER, y WP_APP_PASS están en tu fichero .env"
    logger.critical(error_msg)
else:
    API_BASE = f"{WP_SITE}/wp-json/wp/v2"


def _check_config():
    """Verifica si la configuración de WordPress está completa."""
    if not all((WP_SITE, WP_USER, WP_APP_PASS)):
        raise ValueError("La configuración de WordPress (WP_SITE, WP_USER, WP_APP_PASS) no está completa en el fichero .env.")


def _auth_header() -> dict[str, str]:
    """Crea la cabecera de autenticación Basic Auth."""
    _check_config()
    token = base64.b64encode(f"{WP_USER}:{WP_APP_PASS}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _request(method: str, endpoint: str, **kwargs) -> dict | None:
    """
    Función centralizada para realizar peticiones a la API de WordPress.
    Maneja errores y respuestas contaminadas con avisos de PHP.
    """
    _check_config()
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    headers = kwargs.pop('headers', _auth_header())

    logger.info(f"Realizando petición a WordPress: {method} {url}")
    try:
        r = requests.request(method, url, headers=headers, timeout=120, **kwargs)
        r.raise_for_status()

        if not r.text:
            return None

        response_text = r.text
        json_start_index = response_text.find('{')

        if json_start_index == -1:
            logger.error(f"La respuesta de WordPress no contiene un objeto JSON. Respuesta: {response_text}")
            raise json.JSONDecodeError("No JSON object could be decoded", response_text, 0)

        if json_start_index > 0:
            warning_text = response_text[:json_start_index].strip()
            logger.warning(f"Respuesta de WordPress contenía texto no-JSON. Se ignorará. Texto: '{warning_text}'")
            json_text = response_text[json_start_index:]
        else:
            json_text = response_text

        return json.loads(json_text)

    except json.JSONDecodeError as e:
        logger.error(f"Error de JSON: WordPress no devolvió un JSON válido. Status: {r.status_code}. Respuesta: {r.text}")
        raise RuntimeError(f"WordPress devolvió una respuesta no-JSON (Status: {r.status_code})") from e
    except requests.exceptions.HTTPError as e:
        logger.error(f"Error HTTP de WordPress ({r.status_code}) en {method} {url}: {r.text}")
        raise RuntimeError(f"Error de WordPress ({r.status_code}): {r.text}") from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión a WordPress en {method} {url}: {e}")
        raise RuntimeError(f"Error de conexión a WordPress: {e}") from e


def upload_media(file_path: str) -> dict | None:
    """
    Sube un archivo de media a WordPress y devuelve un diccionario con su ID y URL.
    """
    logger.info(f"Iniciando subida a WordPress para: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"Fichero no encontrado para subir a WordPress: {file_path}")
        raise FileNotFoundError(f"El fichero de medios no existe: {file_path}")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'
        logger.warning(f"No se pudo determinar el tipo MIME para {file_path}. Usando fallback: {mime_type}")

    file_name = os.path.basename(file_path)

    with open(file_path, 'rb') as f:
        file_data = f.read()

    headers = _auth_header()
    headers['Content-Disposition'] = f'attachment; filename="{file_name}"'
    headers['Content-Type'] = mime_type

    response_json = _request("POST", "media", data=file_data, headers=headers)

    if response_json and 'id' in response_json:
        media_info = {
            'id': response_json['id'],
            'url': response_json.get('source_url')
        }
        logger.info(f"Medio subido con éxito a WordPress. ID: {media_info['id']}")
        return media_info

    logger.error("La subida del medio a WordPress no devolvió un ID válido.")
    return None


def create_post_wordpress(*, title: str, content: str, status: str = "publish", excerpt: str | None = None, categories: Iterable[int] | None = None, tags: Iterable[int] | None = None) -> dict:
    """
    Crea una nueva entrada en WordPress.
    """
    logger.info(f"Creando post en WordPress con título: '{title}' y estado: '{status}'")
    payload = {
        "title": title,
        "content": content,
        "status": status,
    }
    if excerpt is not None: payload["excerpt"] = excerpt
    if categories: payload["categories"] = list(categories)
    if tags: payload["tags"] = list(tags)

    headers = _auth_header()
    headers["Content-Type"] = "application/json"

    response_data = _request("POST", "posts", json=payload, headers=headers)

    if response_data and response_data.get('id'):
        logger.info(f"Post creado con éxito en WordPress. ID: {response_data.get('id')}")
    else:
        logger.error(f"No se pudo crear el post en WordPress. Respuesta: {response_data}")

    return response_data
