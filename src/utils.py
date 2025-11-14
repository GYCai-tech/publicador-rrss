import os
import base64
import logging
import re
from typing import List, Any
from uuid import uuid4
import streamlit as st

from PIL import Image, ImageOps
from io import BytesIO

from .db_config import create_media_asset, get_contacts_by_list

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_env_vars() -> None:
    """
    Verifica que todas las variables de entorno necesarias estén configuradas.
    Lanza una excepción SystemExit si alguna de las claves requeridas no se encuentra.
    """
    required_keys = ['OPENAI_API_KEY']
    missing_keys = [key for key in required_keys if not os.getenv(key)]

    if missing_keys:
        error_message = (
            "Error: Faltan variables de entorno esenciales. Por favor, asegúrate de que tu fichero `.env` en la raíz del proyecto contiene las siguientes claves:\n"
            + "\n".join(f" - {key}" for key in missing_keys)
        )
        logger.error(error_message)
        raise SystemExit(error_message)

    logger.info("Todas las variables de entorno necesarias están configuradas correctamente.")


def save_uploaded_media(uploaded_files: List[Any], target_dir: str = "media") -> List[dict]:
    """
    Procesa una lista de archivos subidos (imágenes o vídeos), los guarda en el directorio 'media',
    los registra en la base de datos y devuelve una lista de los activos creados.

    Args:
        uploaded_files: Una lista de objetos UploadedFile de Streamlit.

    Returns:
        Una lista de diccionarios, cada uno representando un activo de medios guardado.
    """
    if not uploaded_files:
        return []

    os.makedirs(target_dir, exist_ok=True)
    saved_assets = []

    # Mapeo de extensiones a tipos de archivo para la base de datos
    FILE_TYPE_MAP = {
        # Imágenes
        'png': 'image', 'jpg': 'image', 'jpeg': 'image', 'webp': 'image', 'gif': 'image',
        # Vídeos
        'mp4': 'video', 'mov': 'video', 'avi': 'video', 'mkv': 'video', 'webm': 'video'
    }


    for uploaded_file in uploaded_files:
        try:
            # Obtener la extensión y determinar el tipo de archivo
            file_name = uploaded_file.name
            extension = file_name.split('.')[-1].lower()
            file_type = FILE_TYPE_MAP.get(extension)

            if not file_type:
                logger.warning(f"El formato del archivo '{file_name}' no es compatible y será ignorado.")
                st.warning(f"El formato del archivo '{file_name}' no es compatible y será ignorado.")
                continue

            # Generar un nombre de archivo único usando UUID para evitar colisiones
            unique_filename = f"{uuid4()}.{extension}"
            save_path = os.path.join(target_dir, unique_filename)

            # Guardar el contenido del archivo directamente en el disco
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Crear el registro en la base de datos a través de la función de db_config
            asset_dict = create_media_asset(
                file_path=save_path,
                file_type=file_type,
                original_filename=file_name
            )

            saved_assets.append(asset_dict)

        except Exception as e:
            logger.error(f"Error procesando el archivo {getattr(uploaded_file, 'name', 'N/A')}: {e}")
            st.error(f"Error al procesar el archivo {uploaded_file.name}: {e}")

    return saved_assets


def image_to_base64(path: str) -> str | None:
    """
    Convierte un fichero de imagen a una cadena Base64 para embeber en HTML.

    Args:
        path: La ruta al fichero de imagen.

    Returns:
        La cadena Base64 de la imagen, o None si el fichero no existe.
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error al convertir la imagen {path} a Base64: {e}")
        return None


def update_prompt_function(function_name: str, new_content: str, file_path: str):
    try:
        # Leer el archivo
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Buscar la función completa
        function_pattern = rf"def {function_name}\(\):.*?return.*?\"\"\".*?\"\"\""
        match = re.search(function_pattern, content, re.DOTALL)

        if not match:
            print(f"No se encontró la función {function_name}")
            return False

        # Obtener la función completa actual
        original_function = match.group(0)

        # Construir la nueva función
        new_content = new_content.strip()
        new_function = f'''def {function_name}():
    return """
{new_content}
    """'''

        # Reemplazar solo la función encontrada
        updated_content = content.replace(original_function, new_function)

        # Escribir el archivo actualizado
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(updated_content)

        return True

    except Exception as e:
        print(f"Error al actualizar: {str(e)}")
        return False


def get_image_preview(image_bytes, target_size):
    """
    Adapta una imagen a la resolución de vídeo deseada para una previsualización.
    """
    try:
        # Abrir la imagen desde los bytes
        img = Image.open(BytesIO(image_bytes))

        # Usar ImageOps.fit para redimensionar y recortar la imagen de una sola vez.
        preview_img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
        return preview_img

    except Exception as e:
        # Si hay un error None
        print(f"Error al procesar la previsualización de la imagen: {e}")
        return None


def validar_contacto(texto, tipo):
    if tipo == "email":
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(patron, texto):
            return True, None
        else:
            return False, "Formato de email inválido. Debe ser 'usuario@dominio.extension'"

    elif tipo == "telefono":
        texto_limpio = re.sub(r'[\s-]', '', texto)
        patron = r'^(\+[1-9]\d{7,14}|[6789]\d{8})$'
        if re.match(patron, texto_limpio):
            return True, None
        else:
            return False, "Formato de teléfono inválido. Debe ser un número internacional (ej: +34...) o un número español de 9 dígitos."
    else:
        return False, f"Tipo de validación '{tipo}' no reconocido. Use 'email' o 'telefono'"


def handle_add_selection(platform_key, tipo_contacto, valid_contacts, post_id_key=None):
    if post_id_key:
        list_select_key = f"list_select_detail_{platform_key}"
        contact_select_key = f"contact_select_detail_{platform_key}"
        contacts_key = f"post_contacts_{post_id_key}"
    else:
        list_select_key = f"list_select_{platform_key}"
        contact_select_key = f"contact_select_{platform_key}"
        contacts_key = f"contacts_{platform_key}"

    selected_lists = st.session_state.get(list_select_key, [])
    selected_contacts_ids = st.session_state.get(contact_select_key, [])

    if not selected_lists and not selected_contacts_ids:
        return  # No hacer nada si no hay selección

    newly_selected_recipients = set()
    for list_id in selected_lists:
        contacts_in_list = get_contacts_by_list(list_id)
        for contact in contacts_in_list:
            if contact.get(tipo_contacto):
                newly_selected_recipients.add(contact[tipo_contacto])
    for contact_id in selected_contacts_ids:
        contact = next((c for c in valid_contacts if c['id'] == contact_id), None)
        if contact and contact.get(tipo_contacto):
            newly_selected_recipients.add(contact[tipo_contacto])

    current_contacts = set(st.session_state.get(contacts_key, []))
    updated_contacts = current_contacts.union(newly_selected_recipients)

    # Actualizar el estado principal de los contactos
    st.session_state[contacts_key] = list(updated_contacts)

    # Limpiar los widgets multiselect para el siguiente ciclo
    st.session_state[list_select_key] = []
    st.session_state[contact_select_key] = []


def get_logo_path(platform_name):
    """
    Normaliza el nombre de la plataforma eliminando sufijos como '(Idioma)'
    y devuelve la ruta completa al archivo del logo.
    Ej: "WhatsApp (Polaco)" -> "WhatsApp"
    """
    base_platform = platform_name.split(' (')[0]
    # Convierte a minúsculas y construye la ruta.
    return f"assets/logos/{base_platform.lower()}.png"
