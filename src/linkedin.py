import os
import requests
import json
from dotenv import load_dotenv
import logging

# Logger
logger = logging.getLogger(__name__)


class LinkedInClient:
    """
    Cliente para interactuar con la API de LinkedIn v2 para crear publicaciones.
    Maneja la publicación de texto, imágenes (única o carrusel) y vídeo.
    """

    def __init__(self):
        load_dotenv()
        self.access_token = os.getenv("ACCESS_TOKEN_LINKEDIN")
        if not self.access_token:
            logger.critical("❌ ERROR CRÍTICO: No se pudo cargar ACCESS_TOKEN_LINKEDIN desde el archivo .env.")
            raise ValueError("El token de acceso de LinkedIn no está configurado.")

        self.api_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        self.author_urn = self._get_user_urn()
        self.post_visibility = os.getenv("POST_VISIBILITY")

    def _get_user_urn(self):
        """Obtiene el URN del usuario autenticado."""
        logger.info("Obteniendo URN de usuario de LinkedIn...")
        try:
            response = requests.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {self.access_token}"})
            response.raise_for_status()
            user_info = response.json()
            user_urn = f"urn:li:person:{user_info['sub']}"
            logger.info(f"✅ URN de usuario obtenido: {user_urn}")
            return user_urn
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ ERROR al obtener el URN de LinkedIn: {e.response.status_code} - {e.response.text}")
            raise

    def _register_asset(self, is_video=False):
        """Registra un asset (imagen/video) y obtiene la URL de subida."""
        logger.info(f"Registrando nuevo asset ({'VIDEO' if is_video else 'IMAGE'})...")
        asset_type = "VIDEO" if is_video else "IMAGE"
        payload = {
            "registerUploadRequest": {
                "recipes": [f"urn:li:digitalmediaRecipe:feedshare-{asset_type.lower()}"],
                "owner": self.author_urn,
                "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
            }
        }
        try:
            response = requests.post("https://api.linkedin.com/v2/assets?action=registerUpload", headers=self.api_headers, json=payload)
            response.raise_for_status()
            data = response.json()
            upload_url = data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset_urn = data['value']['asset']
            logger.info(f"✅ Asset registrado con éxito. URN: {asset_urn}")
            return asset_urn, upload_url
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ ERROR al registrar el asset en LinkedIn: {e.response.status_code} - {e.response.text}")
            raise

    def _upload_file(self, upload_url, file_path):
        """Sube el contenido binario del fichero a la URL de subida."""
        logger.info(f"Subiendo fichero: {file_path}...")
        try:
            with open(file_path, 'rb') as f:
                headers = {'Content-Type': 'application/octet-stream'}
                response = requests.put(upload_url, headers=headers, data=f)
                response.raise_for_status()
                logger.info(f"✅ Fichero subido correctamente (Status: {response.status_code}).")
        except FileNotFoundError:
            logger.error(f"❌ ERROR: Fichero no encontrado en {file_path}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ ERROR al subir el fichero a LinkedIn: {e.response.status_code} - {e.response.text}")
            raise

    def post(self, text: str, image_paths: list = None, video_path: str = None):
        """Crea una nueva publicación en LinkedIn.
        - Si no se proporcionan medios, publica solo texto.
        - Si se proporciona video_path, publica el vídeo (ignora image_paths).
        - Si se proporcionan image_paths, publica las imágenes.
        """
        logger.info("Iniciando proceso de publicación en LinkedIn...")

        # Publicación con vídeo
        if video_path:
            logger.info("Tipo de publicación: VÍDEO")
            asset_urn, upload_url = self._register_asset(is_video=True)
            self._upload_file(upload_url, video_path)
            media_category = "VIDEO"
            media_list = [{"status": "READY", "media": asset_urn}]

        # Publicación con imágenes
        elif image_paths:
            logger.info(f"Tipo de publicación: IMAGEN ({len(image_paths)} ficheros)")
            asset_urns = []
            for path in image_paths:
                asset_urn, upload_url = self._register_asset(is_video=False)
                self._upload_file(upload_url, path)
                asset_urns.append(asset_urn)
            media_category = "IMAGE"
            media_list = [{"status": "READY", "media": urn} for urn in asset_urns]

        # Solo texto
        else:
            logger.info("Tipo de publicación: TEXTO")
            media_category = "NONE"
            media_list = []

        # Payload de la publicación
        payload = {
            "author": self.author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": media_category
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": self.post_visibility}
        }

        # Añadir la clave "media" solo si hay medios
        if media_list:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_list

        logger.info("Enviando payload final a LinkedIn...")
        try:
            response = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=self.api_headers, data=json.dumps(payload))
            response.raise_for_status()
            logger.info("🎉 ¡Publicación en LinkedIn realizada con éxito!")
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ ERROR al crear la publicación final en LinkedIn: {e.response.status_code} - {e.response.text}")
            raise
