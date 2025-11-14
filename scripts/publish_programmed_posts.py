import logging
import time
import traceback
from datetime import datetime
import os

from src.db_config import get_programmed_posts_raw, update_post
from src.gmail import send_mail
from src.wordpress import create_post_wordpress, upload_media
from src.instagram import post_image_ig, post_carousel_ig, post_video_ig
# from src.whatsapp import send_whatsapp
from src.linkedin import LinkedInClient

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("programmed_posts.log", encoding='utf-8'),
        # StreamHandler intenta usar la mejor codificación para la consola
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def publicar_post(post: dict):
    """
    Publica un post según su plataforma, adjuntando los medios asociados.
    Maneja la lógica de extraer imágenes y vídeos del objeto 'post'.
    """
    try:
        if not post or not post.get('id'):
            logger.warning(f"Se intentó procesar un post inválido: {post}")
            return False

        post_id = post.get('id')
        platform_lower = post.get('platform', '').lower()
        logger.info(f"Procesando post ID: {post_id} para la plataforma: {platform_lower}")

        # Extraer rutas de medios
        media_assets = post.get('media_assets', [])
        image_paths = [asset['file_path'] for asset in media_assets if
                       asset['file_type'] == 'image' and os.path.exists(asset['file_path'])]
        video_paths = [asset['file_path'] for asset in media_assets if
                       asset['file_type'] == 'video' and os.path.exists(asset['file_path'])]

        if platform_lower == 'wordpress':
            logger.info(f"Iniciando publicación programada en WordPress para el post {post_id}")

            # Extraer datos del post
            title = post.get('title', 'Sin título')
            content = post.get('content', '')

            embedded_media_html = []

            # Recorremos todas las imágenes para incrustarlas en el contenido.
            for path in image_paths:
                try:
                    logger.info(f"Subiendo imagen para incrustar: {path}")
                    wp_media_info = upload_media(path)
                    if wp_media_info and 'url' in wp_media_info:
                        embedded_media_html.append(f'<p><img src="{wp_media_info["url"]}" alt="{title}"></p>')
                except Exception as e:
                    logger.error(f"Error al subir imagen para incrustar ({path}) para el post {post_id}: {e}")

            # Subir los vídeos para incrustar en el contenido
            for path in video_paths:
                try:
                    logger.info(f"Subiendo vídeo para incrustar: {path}")
                    wp_video_info = upload_media(path)
                    if wp_video_info and 'url' in wp_video_info:
                        embedded_media_html.append(f'<p>[video src="{wp_video_info["url"]}"]</p>')
                except Exception as e:
                    logger.error(f"Error al subir vídeo para incrustar ({path}) para el post {post_id}: {e}")

            # Construir contenido final
            final_content = content + "\n\n" + "\n".join(embedded_media_html)

            # Crear el post
            create_post_wordpress(
                title=title,
                content=final_content,
                status='publish'  # Publicar directamente
            )
            logger.info(f"Publicación en WordPress exitosa para el post {post_id}")

        elif platform_lower == 'gmail':
            # Adjuntar todas las imágenes y vídeos
            attachments = image_paths + video_paths
            send_mail(
                receivers=post.get('contacts', []),
                subject=post.get('asunto', ''),
                content_text=post.get('content', ''),
                content_html=post.get('content_html'),
                attachments=attachments
            )
            logger.info(f"Correo para post {post_id} enviado exitosamente a {post.get('contacts', [])}")

        elif platform_lower == 'instagram':
            caption = post.get('content', '')
            if video_paths:
                logger.info(f"Publicando vídeo en Instagram para el post {post_id}: {video_paths[0]}")
                post_video_ig(video_path=video_paths[0], caption=caption)
            elif image_paths:
                if len(image_paths) == 1:
                    logger.info(f"Publicando imagen única en Instagram para el post {post_id}: {image_paths[0]}")
                    post_image_ig(image_path=image_paths[0], caption=caption)
                else:
                    logger.info(
                        f"Publicando carrusel en Instagram para el post {post_id} con {len(image_paths)} imágenes")
                    post_carousel_ig(image_paths=image_paths, caption=caption)
            else:
                logger.warning(f"Post de Instagram ID {post_id} no tiene medios válidos para publicar.")
                return False
            logger.info(f"Publicación en Instagram para el post {post_id} exitosa.")

        elif platform_lower == 'linkedin':
            logger.info(f"Iniciando publicación en LinkedIn para el post {post_id}")
            linkedin_client = LinkedInClient()
            # LinkedIn permite un vídeo o una o varias imágenes, no ambos. Se prioriza el vídeo.
            video_to_post = video_paths[0] if video_paths else None
            images_to_post = image_paths if not video_to_post and image_paths else None
            linkedin_client.post(
                text=post.get('content', ''),
                video_path=video_to_post,
                image_paths=images_to_post
            )
            logger.info(f"Publicación en LinkedIn para el post {post_id} procesada exitosamente.")

        else:
            if platform_lower == 'whatsapp':
                logger.warning(f"La publicación para WhatsApp (ID: {post_id}) ha sido omitida según la configuración actual.")
                return True  # Devolver True para que el post se elimine de la cola y no se reintente

            logger.warning(f"Plataforma desconocida o sin acción de publicación: {post.get('platform')} para el post {post_id}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error fatal al publicar el post ID {post.get('id', 'desconocido')} en {post.get('platform', 'desconocido')}: {e}")
        logger.error(traceback.format_exc())
        return False


def main():
    logger.info('Iniciando revisión de publicaciones programadas')
    while True:
        print('-' * 40)
        try:
            logger.info('Verificando publicaciones programadas...')
            # Obtener solo los posts que tienen fecha de programación.
            programmed_posts = get_programmed_posts_raw()

            if not programmed_posts:
                logger.info("No hay publicaciones programadas para revisar.")
                time.sleep(60)
                continue

            logger.info(f"Encontradas {len(programmed_posts)} publicaciones programadas.")
            now = datetime.now()
            posts_procesados_en_ciclo = 0

            for post in programmed_posts:
                post_id = post.get('id', 'desconocido')
                try:
                    # Comprobar que 'fecha_hora' no sea None antes de procesar
                    if post.get('fecha_hora'):
                        fecha_hora_dt = datetime.fromisoformat(post['fecha_hora'])

                        if fecha_hora_dt <= now:
                            logger.info(f"--> Es hora de publicar el post ID {post_id} programado para {fecha_hora_dt}")
                            if publicar_post(post):
                                # Marcar como enviado en lugar de eliminar
                                update_post(post_id, sent_at=datetime.now().isoformat())
                                logger.info(f"==> Post ID {post_id} procesado y marcado como enviado correctamente.")
                                posts_procesados_en_ciclo += 1
                            else:
                                logger.error(f"==> Fallo al publicar el post ID {post_id}. Permanecerá en la cola para el siguiente ciclo.")
                except Exception as e:
                    logger.error(f"Error procesando el post ID {post_id}: {e}\n{traceback.format_exc()}")

            logger.info(f"Ciclo completado: {posts_procesados_en_ciclo} publicaciones procesadas.")
            time.sleep(60)

        except Exception as e:
            logger.critical(f"Error CRÍTICO en el ciclo principal: {e}\n{traceback.format_exc()}")
            time.sleep(60)


if __name__ == "__main__":
    main()
