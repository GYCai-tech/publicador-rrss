import streamlit as st
import os
import time
import pandas as pd
from datetime import datetime
from streamlit_tags import st_tags

# --- DEFINIMOS render_header PRIMERO ---
def render_header():
    """
    Función vacía. El banner ha sido eliminado.
    """
    pass  # <--- ESTO ES IMPORTANTE: Evita el IndentationError

# --- IMPORTS DIFERIDOS (Lazy Imports) para evitar errores circulares ---
from .db_config import get_post_by_id, update_post, delete_post, get_all_media_assets, link_media_to_post, get_programmed_posts, get_unprogrammed_posts
from src.db_config import get_all_contacts, get_all_contact_lists
from .utils import validar_contacto, handle_add_selection, get_logo_path

def display_post_editor(post_id):
    # Imports necesarios solo para esta función
    from . import models 
    
    if st.button("← Volver", key=f"back_btn_{post_id}"):
        # Limpiar variables de estado
        keys_to_remove = [
            f"edited_title_{post_id}",
            f"edited_asunto_{post_id}",
            f"edited_content_{post_id}",
            f"post_contacts_{post_id}",
            f"selected_media_ids_{post_id}"
        ]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]

        st.session_state.selected_pub_id = None
        st.rerun()

    post = get_post_by_id(post_id)
    if not post:
        st.error("No se pudo encontrar la publicación seleccionada.")
        return

    # Inicializar estados de texto
    if f"edited_title_{post_id}" not in st.session_state:
        st.session_state[f"edited_title_{post_id}"] = post['title']
    if f"edited_content_{post_id}" not in st.session_state:
        st.session_state[f"edited_content_{post_id}"] = post['content']
    if f"post_contacts_{post_id}" not in st.session_state:
        st.session_state[f"post_contacts_{post_id}"] = post.get('contacts', [])
    if f"edited_asunto_{post_id}" not in st.session_state:
        st.session_state[f"edited_asunto_{post_id}"] = post.get('asunto')
    if f"post_history_{post_id}" not in st.session_state:
        st.session_state[f"post_history_{post_id}"] = [post['content']]
    if f"temp_images_{post_id}" not in st.session_state:
        st.session_state[f"temp_images_{post_id}"] = []
    if f"deleted_images_{post_id}" not in st.session_state:
        st.session_state[f"deleted_images_{post_id}"] = []
    if f"edited_content_html_{post_id}" not in st.session_state:
        st.session_state[f"edited_content_html_{post_id}"] = post.get('content_html', '')

    all_assets_from_db = get_all_media_assets()
    all_valid_assets = [asset for asset in all_assets_from_db if os.path.exists(asset['file_path'])]

    current_associated_ids = {asset['id'] for asset in post.get('media_assets', [])}
    valid_asset_ids_set = {asset['id'] for asset in all_valid_assets}
    default_selected_ids = list(current_associated_ids.intersection(valid_asset_ids_set))

    asset_options = {
        asset['id']: f"[{asset['file_type'].upper()}] - {asset.get('original_filename', os.path.basename(asset['file_path']))}"
        for asset in all_valid_assets
    }

    with st.container():
        platform = post['platform']
        col_logo, col_title = st.columns([1, 9])

        with col_logo:
            image_path = get_logo_path(platform)
            try:
                st.image(image_path, width=70)
            except:
                st.markdown(f"**{platform}**")

        with col_title:
            title = st.text_input(
                "Título de la publicación",
                value=st.session_state[f"edited_title_{post_id}"],
                key=f"title_input_detail_{post_id}"
            )
            st.session_state[f"edited_title_{post_id}"] = title

        if platform.lower().startswith("gmail"):
            from .graph_mail import EMAIL_FOOTER
            st.markdown("##### Vista Previa del HTML (Final)")
            
            current_text = st.session_state.get(f"textarea_detail_{post_id}", st.session_state[f"edited_content_{post_id}"])
            original_html = st.session_state[f"edited_content_html_{post_id}"]
            
            if original_html:
                 st.markdown(original_html, unsafe_allow_html=True)
            else:
                 preview_html = f"<div>{current_text.replace(chr(10), '<br>')}</div>{EMAIL_FOOTER}"
                 st.markdown(preview_html, unsafe_allow_html=True)
                 
            st.info("ℹ️ Si editas el texto de abajo, el formato HTML original se perderá y se usará el texto plano + footer.")
            st.markdown("---")
            st.markdown("##### Editor de Texto Plano")

        edited = st.text_area(
            'Modifique la publicación a su gusto',
            value=st.session_state[f"edited_content_{post_id}"],
            height=500,
            key=f"textarea_detail_{post_id}",
            help="Tip: Escribe **texto** para negrita y *texto* para cursiva"
        )
        st.session_state[f"edited_content_{post_id}"] = edited

        st.markdown("### 📚 Biblioteca de Medios")

        if not all_valid_assets:
            st.info("No hay imágenes o vídeos disponibles en la biblioteca. Sube algunos desde la página de 'Generación'.")
        else:
            if post['platform'].lower().startswith("instagram"):
                st.info("ℹ️ Consejo: La primera imagen determina el formato del carrusel.")
            
            selected_asset_ids = st.multiselect(
                "Selecciona o cambia las imágenes y vídeos",
                options=list(asset_options.keys()),
                format_func=lambda asset_id: asset_options.get(asset_id, "Medio no encontrado"),
                default=default_selected_ids,
                key=f"media_selector_{post_id}"
            )

            st.session_state[f"selected_media_ids_{post_id}"] = selected_asset_ids

            if selected_asset_ids:
                st.markdown("##### Vista Previa")
                preview_cols = st.columns(min(4, len(selected_asset_ids)))
                col_idx = 0
                selected_assets_details = [asset for asset in all_valid_assets if asset['id'] in selected_asset_ids]
                for asset in selected_assets_details:
                    with preview_cols[col_idx % 4]:
                        if asset['file_type'] == 'image':
                            st.image(asset['file_path'], width='stretch')
                        elif asset['file_type'] == 'video':
                            st.video(asset['file_path'])
                        col_idx += 1

        if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp"):
            with st.expander("👥 Destinatarios"):
                tipo_contacto = "email" if platform.lower().startswith("gmail") else "phone"
                contact_label = "Direcciones de correo 📧" if platform.lower().startswith("gmail") else "Números de teléfono 📱"

                all_lists = get_all_contact_lists()
                all_contacts_data = get_all_contacts()
                valid_contacts = [c for c in all_contacts_data if c.get(tipo_contacto)]

                sc1, sc2 = st.columns(2)
                with sc1:
                    list_options = {lst['id']: lst['name'] for lst in all_lists}
                    st.multiselect("Desde Listas", options=list(list_options.keys()), format_func=lambda x: list_options[x], key=f"list_select_detail_{platform}")
                with sc2:
                    contact_options = {c['id']: f"{c['name']}" for c in valid_contacts}
                    st.multiselect("Desde Contactos", options=list(contact_options.keys()), format_func=lambda x: contact_options[x], key=f"contact_select_detail_{platform}")

                st.button("Añadir Selección", key=f"add_selection_detail_{platform}", on_click=handle_add_selection, args=(platform, tipo_contacto, valid_contacts, post_id), width='stretch')

                contacts_key = f"post_contacts_{post_id}"
                if contacts_key not in st.session_state:
                    st.session_state[contacts_key] = []

                contactos_validos, contactos_invalidos = [], []
                for c in st.session_state[contacts_key]:
                    es_valido, error = validar_contacto(c, "email" if platform.lower().startswith("gmail") else "telefono")
                    if es_valido: contactos_validos.append(c)
                    else: contactos_invalidos.append((c, error))

                if contactos_invalidos:
                    for c, error in contactos_invalidos:
                        st.warning(f"• '{c}': {error} (será eliminado)")

                st.session_state[contacts_key] = contactos_validos

                st_tags(
                    label=contact_label,
                    text="Presiona Enter para añadir",
                    value=st.session_state[contacts_key]
                )

        instrucciones = st.text_area(' ', placeholder="Instrucciones para regenerar...", key=f"instrucciones_detail_{post_id}", height=75)

        if st.button("🔄 Regenerar", key=f"regen_detail_{post_id}", width='stretch'):
            if instrucciones:
                try:
                    nuevo_contenido = models.regenerate_post(
                        platform=platform,
                        content=st.session_state[f"edited_content_{post_id}"],
                        prompt=instrucciones
                    )
                    st.session_state[f"edited_content_{post_id}"] = nuevo_contenido["content"]
                    st.session_state[f"post_history_{post_id}"].append(nuevo_contenido["content"])
                    st.success("Contenido regenerado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Ingresa instrucciones.")

        st.markdown("### ⏰ Programación")

        fecha_inicial = datetime.now().date() + pd.Timedelta(days=1)
        hora_inicial = datetime.now().time().replace(second=0, microsecond=0)

        if post['fecha_hora']:
            try:
                fecha_dt = datetime.fromisoformat(post['fecha_hora'])
                if fecha_dt.date() >= datetime.now().date():
                    fecha_inicial = fecha_dt.date()
                    hora_inicial = fecha_dt.time()
            except: pass

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Actualizar y programar", key=f"update_prog_detail_{post_id}", width='stretch'):
                try:
                    if not st.session_state.get(f"selected_media_ids_{post_id}") and platform.lower().startswith("instagram"):
                        st.warning("Selecciona al menos un medio para Instagram")
                    elif fecha_hora_programada <= datetime.now() + pd.Timedelta(minutes=1):
                        st.error("La fecha debe ser futura")
                    else:
                        update_data = {
                            "title": st.session_state[f"edited_title_{post_id}"],
                            "content": st.session_state[f"edited_content_{post_id}"],
                            "content_html": st.session_state[f"edited_content_html_{post_id}"],
                            "asunto": st.session_state.get(f"edited_asunto_{post_id}"),
                            "contacts": contactos_validos if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp") else [],
                            "fecha_hora": fecha_hora_programada.isoformat(),
                            "sent_at": None
                        }
                        update_post(post_id, **update_data)
                        link_media_to_post(post_id, st.session_state.get(f"selected_media_ids_{post_id}", []))
                        
                        st.cache_data.clear() # <--- ELIMINA LA CACHÉ VIEJA CORRECTAMENTE
                        
                        st.success(f"Programada para {fecha_hora_programada}")
                        st.session_state.selected_pub_id = None
                        st.session_state.force_page_rerun = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

        with col2:
            if st.button("💾 Actualizar sin programar", key=f"update_save_detail_{post_id}", width='stretch'):
                try:
                    update_data = {
                        "title": st.session_state[f"edited_title_{post_id}"],
                        "content": st.session_state[f"edited_content_{post_id}"],
                        "content_html": st.session_state[f"edited_content_html_{post_id}"],
                        "asunto": st.session_state.get(f"edited_asunto_{post_id}"),
                        "contacts": contactos_validos if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp") else [],
                        "fecha_hora": None,
                        "sent_at": None
                    }
                    update_post(post_id, **update_data)
                    link_media_to_post(post_id, st.session_state.get(f"selected_media_ids_{post_id}", []))
                    
                    st.cache_data.clear() # <--- ELIMINA LA CACHÉ VIEJA CORRECTAMENTE
                    
                    st.success("Guardado sin programar")
                    st.session_state.selected_pub_id = None
                    st.session_state.force_page_rerun = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

        with col2:
            if st.button("💾 Actualizar sin programar", key=f"update_save_detail_{post_id}", width='stretch'):
                try:
                    update_data = {
                        "title": st.session_state[f"edited_title_{post_id}"],
                        "content": st.session_state[f"edited_content_{post_id}"],
                        "content_html": st.session_state[f"edited_content_html_{post_id}"],
                        "asunto": st.session_state.get(f"edited_asunto_{post_id}"),
                        "contacts": contactos_validos if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp") else [],
                        "fecha_hora": None
                    }
                    # Pasamos explícitamente sent_at=None aquí:
                    update_post(post_id, sent_at=None, **update_data)
                    link_media_to_post(post_id, st.session_state.get(f"selected_media_ids_{post_id}", []))
                    
                    st.cache_data.clear() # <--- LIMPIEZA GLOBAL INFALIBLE
                    
                    st.success("Guardado sin programar")
                    st.session_state.selected_pub_id = None
                    st.session_state.force_page_rerun = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")


def display_posts(posts, date_range, sort_by, post_type, usar_filtro_fecha=False):
    # Imports diferidos
    from .graph_mail import send_mail_graph_batch, send_mail_graph as send_mail
    from .wordpress import create_post_wordpress, upload_media
    from .linkedin import LinkedInClient
    
    if date_range and usar_filtro_fecha and post_type in ['scheduled', 'history']:
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = end_date = date_range
        
        filtered_posts = []
        for post in posts:
            date_field = 'sent_at' if post_type == 'history' else 'fecha_hora'
            if post.get(date_field):
                post_date = datetime.fromisoformat(post[date_field]).date()
                if start_date <= post_date <= end_date:
                    filtered_posts.append(post)
    else:
        filtered_posts = posts

    if sort_by == "Fecha (ascendente)" and post_type == 'scheduled':
        filtered_posts = sorted(filtered_posts, key=lambda x: x['fecha_hora'] if x['fecha_hora'] else '')
    elif sort_by == "Fecha (descendente)" and post_type == 'scheduled':
        filtered_posts = sorted(filtered_posts, key=lambda x: x['fecha_hora'] if x['fecha_hora'] else '', reverse=True)
    elif sort_by.startswith("Fecha de envío"):
        reverse = "reciente" in sort_by
        filtered_posts = sorted(filtered_posts, key=lambda x: x.get('sent_at', ''), reverse=reverse)
    elif sort_by.startswith("Fecha de creación"):
        reverse = "reciente" in sort_by
        filtered_posts = sorted(filtered_posts, key=lambda x: x['created_at'], reverse=reverse)
    elif sort_by == "Plataforma":
        filtered_posts = sorted(filtered_posts, key=lambda x: x['platform'])

    if filtered_posts:
        for post_index, post in enumerate(filtered_posts):
            platform = post['platform']
            with st.container():
                st.markdown('---')
                col_logo, col_title = st.columns([0.5, 7])
                with col_logo: st.image(get_logo_path(platform), width=50)
                with col_title:
                    if post['title']: st.markdown(f"#### {post['title']}")

                col1, col2, col3 = st.columns(3)
                with col1: st.markdown(f"📅 Creada: {datetime.fromisoformat(post['created_at']).strftime('%d/%m/%Y %H:%M')}")
                with col2:
                    if post.get('sent_at'): st.markdown(f"✅ Enviada: {datetime.fromisoformat(post['sent_at']).strftime('%d/%m/%Y %H:%M')}")
                    elif post['fecha_hora']: st.markdown(f"⏱️ Programada: {datetime.fromisoformat(post['fecha_hora']).strftime('%d/%m/%Y %H:%M')}")
                with col3:
                    if post['fecha_hora'] is not None and not post.get('sent_at'):
                        if st.button("🗑️ Desprogramar", key=f"cancel_{post['id']}", width='stretch'):
                            try:
                                update_post(post['id'], fecha_hora=None)
                                get_unprogrammed_posts.clear()
                                get_programmed_posts.clear()
                                st.success("Cancelada")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e: st.error(str(e))

                with st.expander("📄 Ver contenido"):
                    if platform.lower().startswith("gmail"):
                        st.markdown(f"**Asunto:** {post.get('asunto', 'Sin asunto')}")
                        st.markdown("---")
                        html_content = post.get('content_html', f"<p>{post.get('content', 'Contenido no disponible.')}</p>")
                        st.markdown(html_content, unsafe_allow_html=True)
                    elif platform.lower().startswith("wordpress"):
                        st.markdown(' ```html ' + post['content'] + ' ``` ')
                    else:
                        st.markdown(post['content'])

                if (platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp")) and post.get('contacts'):
                    with st.expander("👥 Ver contactos"):
                        st.markdown(f"**{len(post['contacts'])} contactos**")
                        for contacto in post['contacts']:
                            st.text(f"• {contacto}")

                if post['media_assets']:
                    with st.expander("🖼️ Ver Medios Adjuntos"):
                        images = [a for a in post['media_assets'] if a['file_type'] == 'image']
                        if images:
                            st.markdown("Imágenes")
                            cols = st.columns(min(4, len(images)))
                            for i, asset in enumerate(images):
                                with cols[i % 4]:
                                    if os.path.exists(asset['file_path']): st.image(asset['file_path'], width='stretch')
                        
                        videos = [a for a in post['media_assets'] if a['file_type'] == 'video']
                        if videos:
                            st.markdown("Vídeos")
                            for asset in videos:
                                if os.path.exists(asset['file_path']): st.video(asset['file_path'])

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✏️ Editar", key=f"edit_{post['id']}", width='stretch'):
                        st.session_state.selected_pub_id = post['id']
                        st.rerun()
                with col2:
                    delete_key = f"delete_btn_{post['id']}_{platform}"
                    confirm_key = f"confirm_delete_{post['id']}_{platform}"
                    if st.session_state.get(confirm_key, False):
                        if st.button("⚠️ Confirmar", key=f"confirm_{post['id']}_{platform}", width='stretch', type="primary"):
                            try:
                                if delete_post(post['id']):
                                    del st.session_state[confirm_key]
                                    get_unprogrammed_posts.clear()
                                    get_programmed_posts.clear()
                                    st.success("Eliminada")
                                    time.sleep(0.5)
                                    st.rerun()
                            except Exception as e: st.error(str(e))
                        if st.button("Cancelar", key=f"cancel_{post['id']}_{platform}", width='stretch'):
                            del st.session_state[confirm_key]
                            st.rerun()
                    else:
                        if st.button("❌ Eliminar", key=delete_key, width='stretch'):
                            for key in list(st.session_state.keys()):
                                if key.startswith("confirm_delete_"): del st.session_state[key]
                            st.session_state[confirm_key] = True
                            st.rerun()

                with col3:
                    inline_opt = False
                    if platform.lower().startswith("gmail") and post.get('media_assets'):
                        inline_opt = st.checkbox("Incrustar", key=f"inline_opt_{post['id']}")

                    if st.button("🚀Publicar ahora", key=f"publish_now_{post['id']}", width='stretch'):
                        with st.spinner(f"Publicando en {post['platform']}..."):
                            text = post.get('content', '')
                            contacts = post.get('contacts', [])
                            asunto = post.get('asunto', 'Sin asunto')
                            title = post.get('title', 'Sin título')
                            platform_lower = post.get('platform', '').lower()
                            
                            media_assets = post.get('media_assets', [])
                            image_paths = [a['file_path'] for a in media_assets if a['file_type'] == 'image' and os.path.exists(a['file_path'])]
                            video_paths = [a['file_path'] for a in media_assets if a['file_type'] == 'video' and os.path.exists(a['file_path'])]
                            all_attachments = image_paths + video_paths

                            # 1. VARIABLE PARA CONTROLAR EL ÉXITO
                            envio_exitoso = False

                            if platform_lower.startswith("instagram"):
                                try:
                                    from .instagram import post_image_ig, post_carousel_ig, post_video_ig
                                    if not all_attachments: st.error('Se necesita imagen/vídeo para Instagram.')
                                    else:
                                        if video_paths: post_video_ig(video_path=video_paths[0], caption=text)
                                        elif len(image_paths) == 1: post_image_ig(image_path=image_paths[0], caption=text)
                                        else: post_carousel_ig(image_paths=image_paths, caption=text)
                                        st.success("¡Publicado en Instagram!")
                                        envio_exitoso = True # <-- ÉXITO
                                except ImportError: st.error("Falta librería 'instagrapi'.")
                                except Exception as e: st.error(f"Error Instagram: {e}")

                            elif platform_lower.startswith("gmail"):
                                try:
                                    if len(contacts) > 1:
                                        with st.status("Enviando masivo...", expanded=True):
                                            result = send_mail_graph_batch(
                                                subject=asunto, content_text=text, content_html=post.get('content_html'),
                                                receivers=contacts, attachments=all_attachments, inline_images=inline_opt,
                                                batch_size=20
                                            )
                                            st.success(f"Enviado a {result['successful']}/{result['total']}")
                                            if result['successful'] > 0: envio_exitoso = True # <-- ÉXITO
                                    else:
                                        send_mail(
                                            subject=asunto, content_text=text, content_html=post.get('content_html'),
                                            receivers=contacts, attachments=all_attachments, inline_images=inline_opt
                                        )
                                        st.success("Correo enviado.")
                                        envio_exitoso = True # <-- ÉXITO
                                except Exception as e: st.error(f"Error Email: {e}")

                            elif platform_lower.startswith("wordpress"):
                                try:
                                    embed_html = []
                                    for p in image_paths:
                                        info = upload_media(p)
                                        if info: embed_html.append(f'<p><img src="{info["url"]}" alt="{title}"></p>')
                                    for p in video_paths:
                                        info = upload_media(p)
                                        if info: embed_html.append(f'<p>[video src="{info["url"]}"]</p>')
                                    
                                    final = text + "\n\n" + "\n".join(embed_html)
                                    wp_post = create_post_wordpress(title=title, content=final, status='publish')
                                    if wp_post: 
                                        st.success("Publicado en WordPress!")
                                        envio_exitoso = True # <-- ÉXITO
                                    else: st.error("Fallo WordPress")
                                except Exception as e: st.error(f"Error WP: {e}")

                            elif platform_lower.startswith("linkedin"):
                                try:
                                    cli = LinkedInClient()
                                    video = video_paths[0] if video_paths else None
                                    imgs = image_paths if not video and image_paths else None
                                    cli.post(text=text, video_path=video, image_paths=imgs)
                                    st.success("¡Publicado en LinkedIn!")
                                    envio_exitoso = True # <-- ÉXITO
                                except Exception as e: st.error(f"Error LinkedIn: {e}")
                            else:
                                st.error("Plataforma no soportada.")
                                
                            # 2. SI FUE EXITOSO, ACTUALIZAR BD Y MOVER A HISTORIAL
                            if envio_exitoso:
                                update_post(post['id'], sent_at=datetime.now().isoformat())
                                from .db_config import get_sent_posts
                                get_unprogrammed_posts.clear()
                                get_programmed_posts.clear()
                                get_sent_posts.clear()
                                time.sleep(1.5) 
                                st.rerun() 
    else:
        st.warning("No hay publicaciones.")

def create_image_carousel(images, platform):
    if not images: return
    with st.expander("📸 Imágenes adjuntas", expanded=True):
        cols = st.columns(min(4, len(images)))
        for i, img in enumerate(images):
            with cols[i % 4]:
                try:
                    if hasattr(img, 'seek'): img.seek(0)
                    st.image(img, caption=getattr(img, 'name', f'Img {i}'), width='stretch')
                    if hasattr(img, 'seek'): img.seek(0)
                except Exception: st.error(f"Error img {i}")