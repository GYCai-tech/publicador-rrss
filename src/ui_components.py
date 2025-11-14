import streamlit as st
import os
import time
import pandas as pd
from datetime import datetime
from streamlit_tags import st_tags

from .db_config import get_post_by_id, update_post, delete_post, get_all_media_assets, link_media_to_post, get_programmed_posts, get_unprogrammed_posts
from src.db_config import get_all_contacts, get_all_contact_lists
from . import models
from .instagram import post_image_ig, post_carousel_ig, post_video_ig
from .wordpress import create_post_wordpress, upload_media
from .linkedin import LinkedInClient
from .gmail import send_mail
from .utils import validar_contacto, handle_add_selection, get_logo_path


def display_post_editor(post_id):
    if st.button("← Volver", key=f"back_btn_{post_id}"):
        # Limpiar solo las variables de estado necesarias para este editor
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
    # Para llevar un control de imágenes temporales
    if f"temp_images_{post_id}" not in st.session_state:
        st.session_state[f"temp_images_{post_id}"] = []
    # Para llevar un control de imágenes eliminadas
    if f"deleted_images_{post_id}" not in st.session_state:
        st.session_state[f"deleted_images_{post_id}"] = []
    if f"edited_content_html_{post_id}" not in st.session_state:
        st.session_state[f"edited_content_html_{post_id}"] = post.get('content_html', '')

    # Obtener todos los activos disponibles de la BD
    all_assets_from_db = get_all_media_assets()

    # Filtrar solo los activos cuyo fichero existe en el disco
    all_valid_assets = [
        asset for asset in all_assets_from_db if os.path.exists(asset['file_path'])
    ]

    # Informar si hay medios rotos
    broken_assets_count = len(all_assets_from_db) - len(all_valid_assets)
    if broken_assets_count > 0:
        st.warning(f"ℹ️ Se han ocultado {broken_assets_count} medios porque no se encontraron sus ficheros.")

    # Obtener los IDs de los activos actualmente asociados al post
    current_associated_ids = {asset['id'] for asset in post.get('media_assets', [])}

    # Asegurarse de que los assets pre-seleccionados existen en disco
    valid_asset_ids_set = {asset['id'] for asset in all_valid_assets}
    default_selected_ids = list(current_associated_ids.intersection(valid_asset_ids_set))

    # Crear las opciones para el selector
    asset_options = {
        asset['id']: f"[{asset['file_type'].upper()}] - {asset.get('original_filename', os.path.basename(asset['file_path']))}"
        for asset in all_valid_assets
    }

    # Contenedor principal
    with st.container():
        # Mostrar logo de la plataforma y título
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
            st.markdown("##### Vista Previa del HTML")
            st.markdown(st.session_state[f"edited_content_html_{post_id}"], unsafe_allow_html=True)
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
            st.info(
                "No hay imágenes o vídeos disponibles en la biblioteca. Sube algunos desde la página de 'Generación'."
            )
        else:
            if post['platform'].lower().startswith("instagram"):
                st.info(
                    """
                    ℹ️ **Consejo para Carruseles:** La primera imagen que selecciones determinará el formato 
                    (cuadrado, vertical, etc.) de todas las demás. Para evitar recortes no deseados,
                    asegúrate de que todas las imágenes tengan la misma orientación.
                    
                    ℹ️ **No se pueden subir vídeo e imágenes a la vez:** En el caso en el que intentes subir
                    ambos, se subirá el vídeo.
                    """
                )
            # Mostrar el selector múltiple
            selected_asset_ids = st.multiselect(
                "Selecciona o cambia las imágenes y vídeos para esta publicación",
                options=list(asset_options.keys()),
                format_func=lambda asset_id: asset_options.get(asset_id, "Medio no encontrado"),
                default=default_selected_ids,
                key=f"media_selector_{post_id}"
            )

            # Guardar la selección actual en el estado de la sesión
            st.session_state[f"selected_media_ids_{post_id}"] = selected_asset_ids

            # Mostrar una vista previa de los medios seleccionados
            if selected_asset_ids:
                st.markdown("##### Vista Previa de Medios Seleccionados")
                preview_cols = st.columns(min(4, len(selected_asset_ids)))
                col_idx = 0
                # Filtrar los assets completos para la vista previa
                selected_assets_details = [asset for asset in all_valid_assets if asset['id'] in selected_asset_ids]
                for asset in selected_assets_details:
                    with preview_cols[col_idx % 4]:
                        if asset['file_type'] == 'image':
                            st.image(asset['file_path'], width='stretch')
                        elif asset['file_type'] == 'video':
                            st.video(asset['file_path'])
                        col_idx += 1

        # Gestión de contactos para WhatsApp y Gmail
        if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp"):
            with st.expander("👥 Destinatarios"):
                tipo_contacto = "email" if platform.lower().startswith("gmail") else "phone"
                # Configurar el componente según la plataforma
                contact_label = "Direcciones de correo 📧" if platform.lower().startswith("gmail") else "Números de teléfono 📱"

                all_lists = get_all_contact_lists()
                all_contacts_data = get_all_contacts()
                valid_contacts = [c for c in all_contacts_data if c.get(tipo_contacto)]

                sc1, sc2 = st.columns(2)
                with sc1:
                    list_options = {lst['id']: lst['name'] for lst in all_lists}
                    st.multiselect(
                        "Desde Listas",
                        options=list(list_options.keys()),
                        format_func=lambda x: list_options[x],
                        key=f"list_select_detail_{platform}"
                    )
                with sc2:
                    contact_options = {c['id']: f"{c['name']}" for c in valid_contacts}
                    st.multiselect(
                        "Desde Contactos",
                        options=list(contact_options.keys()),
                        format_func=lambda x: contact_options[x],
                        key=f"contact_select_detail_{platform}"
                    )

                st.button(
                    "Añadir Selección",
                    key=f"add_selection_detail_{platform}",
                    on_click=handle_add_selection,
                    args=(platform, tipo_contacto, valid_contacts, post_id),
                    width='stretch'
                )

                contacts_key = f"post_contacts_{post_id}"
                if contacts_key not in st.session_state:
                    st.session_state[contacts_key] = []

                contactos_validos, contactos_invalidos = [], []
                for c in st.session_state[contacts_key]:
                    es_valido, error = validar_contacto(c, "email" if platform.lower().startswith("gmail") else "telefono")
                    if es_valido:
                        contactos_validos.append(c)
                    else:
                        contactos_invalidos.append((c, error))

                if contactos_invalidos:
                    for c, error in contactos_invalidos:
                        st.warning(f"• '{c}': {error} (será eliminado)")

                st.session_state[contacts_key] = contactos_validos

                # Componente para añadir/editar contactos
                st_tags(
                    label=contact_label,
                    text=f"Escribe y presiona Enter para añadir más" if platform.lower().startswith("gmail") else "Escribe el número sin +34 y presiona Enter (se añadirá automáticamente)",
                    value=st.session_state[contacts_key]
                )

        # Campo de instrucciones para regenerar
        instrucciones = st.text_area(
            ' ',
            placeholder="Escribe aquí instrucciones para regenerar el contenido",
            key=f"instrucciones_detail_{post_id}",
            height=75
        )

        # Botón de regeneración
        if st.button("🔄 Regenerar", key=f"regen_detail_{post_id}", width='stretch'):
            if instrucciones:
                try:
                    nuevo_contenido = models.regenerate_post(
                        platform=platform,
                        content=st.session_state[f"edited_content_{post_id}"],
                        prompt=instrucciones
                    )
                    # Guardar el nuevo contenido en el historial (solo en session_state)
                    st.session_state[f"edited_content_{post_id}"] = nuevo_contenido["content"]
                    st.session_state[f"post_history_{post_id}"].append(nuevo_contenido["content"])
                    st.success("Contenido regenerado exitosamente (cambios pendientes de guardar)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al regenerar el contenido: {str(e)}")
            else:
                st.warning("Por favor, ingresa instrucciones para modificar el contenido")

        # Opciones de programación
        st.markdown("### ⏰ Programación")

        # Determinar valores iniciales para fecha y hora
        fecha_inicial = datetime.now().date() + pd.Timedelta(days=1)
        hora_inicial = datetime.now().time().replace(second=0, microsecond=0)

        if post['fecha_hora']:
            try:
                fecha_dt = datetime.fromisoformat(post['fecha_hora'])
                # Verificar que la fecha no sea anterior a la actual
                if fecha_dt.date() >= datetime.now().date():
                    fecha_inicial = fecha_dt.date()
                    hora_inicial = fecha_dt.time()
            except:
                # Si hay algún error al parsear la fecha, usar los valores por defecto
                pass

        # Selector de fecha y hora
        col1, col2 = st.columns(2)
        with col1:
            # Calcular fecha máxima (1 año desde hoy)
            max_date = datetime.now().date() + pd.Timedelta(days=365)

            fecha_programada = st.date_input(
                "Fecha de publicación",
                value=fecha_inicial,
                min_value=datetime.now().date(),
                max_value=max_date,
                key=f"fecha_prog_detail_{post_id}"
            )
        with col2:
            hora_programada = st.time_input(
                "Hora de publicación",
                value=hora_inicial,
                key=f"hora_prog_detail_{post_id}",
                step=60 * 5
            )

        # Combinar fecha y hora en un datetime
        fecha_hora_programada = datetime.combine(fecha_programada, hora_programada)

        # Botones de acción
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Actualizar y programar", key=f"update_prog_detail_{post_id}", width='stretch'):
                try:
                    # Validaciones
                    if not st.session_state.get(f"selected_media_ids_{post_id}") and platform.lower().startswith("instagram"):
                        st.warning("🚧 Debes seleccionar al menos un medio para publicar en Instagram")
                    elif fecha_hora_programada <= datetime.now() + pd.Timedelta(minutes=1):
                        st.error("La fecha de programación debe ser al menos 1 minuto posterior a la hora actual")
                    else:
                        # Crear un diccionario con los datos de texto a actualizar
                        update_data = {
                            "title": st.session_state[f"edited_title_{post_id}"],
                            "content": st.session_state[f"edited_content_{post_id}"],
                            "content_html": st.session_state[f"edited_content_html_{post_id}"],
                            "asunto": st.session_state.get(f"edited_asunto_{post_id}"),
                            "contacts": contactos_validos if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp") else [],
                            "fecha_hora": fecha_hora_programada.isoformat()
                        }
                        # Actualizar los datos de texto del post
                        update_post(post_id, **update_data)

                        # Obtener y actualizar los medios asociados
                        selected_media_ids = st.session_state.get(f"selected_media_ids_{post_id}", [])
                        link_media_to_post(post_id, selected_media_ids)

                        get_unprogrammed_posts.clear()
                        get_programmed_posts.clear()

                        st.success(f"¡Publicación actualizada y programada para {fecha_hora_programada.strftime('%d/%m/%Y a las %H:%M')}!")
                        st.session_state.selected_pub_id = None
                        st.session_state.force_page_rerun = True
                        st.rerun()

                except Exception as e:
                    st.error(f"Error al actualizar la publicación: {str(e)}")

        with col2:
            if st.button("💾 Actualizar sin programar", key=f"update_save_detail_{post_id}", width='stretch'):
                try:
                    # Crear un diccionario con los datos base a actualizar
                    update_data = {
                        "title": st.session_state[f"edited_title_{post_id}"],
                        "content": st.session_state[f"edited_content_{post_id}"],
                        "content_html": st.session_state[f"edited_content_html_{post_id}"],
                        "asunto": st.session_state.get(f"edited_asunto_{post_id}"),
                        "contacts": contactos_validos if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp") else [],
                        "fecha_hora": None
                    }

                    # Actualizar los datos de texto del post
                    update_post(post_id, **update_data)

                    # Obtener y actualizar los medios asociados
                    selected_media_ids = st.session_state.get(f"selected_media_ids_{post_id}", [])
                    link_media_to_post(post_id, selected_media_ids)

                    get_unprogrammed_posts.clear()
                    get_programmed_posts.clear()

                    st.success("¡Publicación actualizada exitosamente sin programación!")
                    st.session_state.selected_pub_id = None
                    st.session_state.force_page_rerun = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al actualizar la publicación: {str(e)}")


def display_posts(posts, date_range, sort_by, post_type, usar_filtro_fecha=False):
    # Filtrado por fecha
    if date_range and usar_filtro_fecha and post_type in ['scheduled', 'history']:
        # Asegurar que date_range sea una tupla de dos fechas
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            # Si solo es una fecha, usar la misma como inicio y fin
            start_date = end_date = date_range

        filtered_posts = []
        for post in posts:
            # Para publicaciones programadas usar fecha_hora, para historial usar sent_at
            date_field = 'sent_at' if post_type == 'history' else 'fecha_hora'
            if post.get(date_field):
                post_date = datetime.fromisoformat(post[date_field]).date()
                if start_date <= post_date <= end_date:
                    filtered_posts.append(post)
    else:
        filtered_posts = posts

    # Ordenamiento
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

    # Mostrar publicaciones usando cards
    if filtered_posts:
        for post_index, post in enumerate(filtered_posts):
            platform = post['platform']

            # Crear tarjeta para cada publicación
            with st.container():
                st.markdown('---')
                st.markdown('')

                # Crear varias columnas para mostrar toda la información en la misma línea
                col_logo, col_title = st.columns([0.5, 7])

                # Mostrar logo en la primera columna
                with col_logo:
                    st.image(get_logo_path(platform), width=50)

                # Mostrar título en la segunda columna
                with col_title:
                    if post['title']:
                        st.markdown(f"#### {post['title']}")

                col1, col2, col3 = st.columns(3)

                with col1:
                    created_dt = datetime.fromisoformat(post['created_at'])
                    st.markdown(f"📅 Creada: {created_dt.strftime('%d/%m/%Y %H:%M')}")

                with col2:
                    if post.get('sent_at'):
                        sent_dt = datetime.fromisoformat(post['sent_at'])
                        st.markdown(f"✅ Enviada: {sent_dt.strftime('%d/%m/%Y %H:%M')}")
                    elif post['fecha_hora']:
                        fecha_dt = datetime.fromisoformat(post['fecha_hora'])
                        st.markdown(f"⏱️ Programada: {fecha_dt.strftime('%d/%m/%Y %H:%M')}")
                with col3:
                    if post['fecha_hora'] is not None and not post.get('sent_at'):
                        if st.button("🗑️ Desprogramar", key=f"cancel_{post['id']}", width='stretch'):
                            try:
                                update_post(post['id'], fecha_hora=None)

                                get_unprogrammed_posts.clear()
                                get_programmed_posts.clear()

                                st.success("Programación cancelada con éxito")
                                time.sleep(0.5)  # Pequeña pausa para mostrar el mensaje
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al cancelar la programación: {str(e)}")


                # Vista previa del contenido
                with st.expander("📄 Ver contenido"):
                    if platform.lower().startswith("gmail"):
                        st.markdown(f"**Asunto:** {post.get('asunto', 'Sin asunto')}")
                        st.markdown("---")
                        st.markdown("##### Vista Previa del Correo:")
                        # Renderizar el HTML del post guardado
                        html_content = post.get('content_html', f"<p>{post.get('content', 'Contenido no disponible.')}</p>")
                        st.markdown(html_content, unsafe_allow_html=True)
                    elif platform.lower().startswith("wordpress"):
                        st.markdown(' ```html ' + post['content'] + ' ``` ')
                    else:
                        st.markdown(post['content'])


                # Mostrar contactos si es WhatsApp o Gmail
                if (platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp")) and post.get('contacts'):
                    with st.expander("👥 Ver contactos"):
                        contact_cols = st.columns(3)
                        st.markdown(f"**{len(post['contacts'])} contactos para esta publicación**")
                        if len(post['contacts']) < 1:
                            st.info(f"No hay contactos asociados a esta publicación de {platform}")
                        for i, contacto in enumerate(post['contacts']):
                            with contact_cols[i % 3]:
                                icon = "✉️" if platform.lower().startswith("gmail") else "📱"
                                st.markdown(f"{icon} `{contacto}`")

                if post['media_assets']:
                    with st.expander("🖼️ Ver Medios Adjuntos"):
                        # Filtrar solo las imágenes
                        images = [asset for asset in post['media_assets'] if asset['file_type'] == 'image']
                        if images:
                            st.markdown("##### Imágenes")
                            img_cols = st.columns(min(4, len(images)))
                            for i, asset in enumerate(images):
                                with img_cols[i % 4]:
                                    if os.path.exists(asset['file_path']):
                                        st.image(asset['file_path'], width='stretch')

                        # Filtrar solo los vídeos
                        videos = [asset for asset in post['media_assets'] if asset['file_type'] == 'video']
                        if videos:
                            st.markdown("##### Vídeos")
                            for asset in videos:
                                if os.path.exists(asset['file_path']):
                                    st.video(asset['file_path'])

                col1, col2, col3 = st.columns(3)

                with col1:
                    # Botón de editar
                    if st.button("✏️ Editar", key=f"edit_{post['id']}", width='stretch'):
                        st.session_state.selected_pub_id = post['id']
                        st.rerun()
                with col2:
                    # Generar claves únicas para cada post
                    delete_key = f"delete_btn_{post['id']}_{platform}"
                    confirm_key = f"confirm_delete_{post['id']}_{platform}"

                    # Verificar si ya hay una confirmación pendiente
                    if st.session_state.get(confirm_key, False):
                        # Mostrar botón de confirmación en rojo
                        if st.button("⚠️ Confirmar eliminación",
                                    key=f"confirm_{post['id']}_{platform}",
                                    width='stretch',
                                    type="primary"):
                            try:
                                resultado = delete_post(post['id'])
                                if resultado:
                                    # Limpiar la variable de estado
                                    del st.session_state[confirm_key]

                                    get_unprogrammed_posts.clear()
                                    get_programmed_posts.clear()

                                    st.success("Publicación eliminada exitosamente")
                                    time.sleep(0.5)  # Pequeña pausa para que se vea el mensaje
                                    st.rerun()
                                else:
                                    st.error("No se pudo eliminar la publicación")
                            except Exception as e:
                                st.error(f"Error al eliminar la publicación: {str(e)}")

                        # Botón para cancelar la eliminación
                        if st.button("Cancelar",
                                    key=f"cancel_{post['id']}_{platform}",
                                    width='stretch'):
                            # Eliminar la confirmación
                            if confirm_key in st.session_state:
                                del st.session_state[confirm_key]
                            st.rerun()
                    else:
                        # Botón normal de eliminación
                        if st.button("❌ Eliminar publicación",
                                    key=delete_key,
                                    width='stretch'):
                            # Limpiar cualquier otra confirmación pendiente
                            for key in list(st.session_state.keys()):
                                if key.startswith("confirm_delete_") and key != confirm_key:
                                    del st.session_state[key]

                            # Establecer esta confirmación
                            st.session_state[confirm_key] = True
                            st.rerun()

                with col3:
                    if st.button("🚀Publicar ahora", key=f"publish_now_{post['id']}", width='stretch'):
                        with st.spinner(f"Publicando en {post['platform']}..."):
                            # Extraer los datos del post
                            text = post.get('content', '')
                            contacts = post.get('contacts', [])
                            asunto = post.get('asunto', 'Sin asunto')
                            title = post.get('title', 'Sin título')
                            platform_lower = post.get('platform', '').lower()

                            # Obtener las rutas de los medios adjuntos, igual que hace el publicador automático
                            media_assets = post.get('media_assets', [])
                            image_paths = [asset['file_path'] for asset in media_assets if
                                           asset['file_type'] == 'image' and os.path.exists(asset['file_path'])]
                            video_paths = [asset['file_path'] for asset in media_assets if
                                           asset['file_type'] == 'video' and os.path.exists(asset['file_path'])]
                            all_attachments = image_paths + video_paths

                            if platform_lower.startswith("instagram"):
                                if not all_attachments:
                                    st.error('Se necesita al menos un vídeo o imagen para publicar en Instagram.')
                                else:
                                    try:
                                        if video_paths:
                                            post_video_ig(video_path=video_paths[0], caption=text)
                                        elif len(image_paths) == 1:
                                            post_image_ig(image_path=image_paths[0], caption=text)
                                        else:
                                            post_carousel_ig(image_paths=image_paths, caption=text)
                                        st.success("¡Publicación subida a Instagram con éxito!")
                                    except Exception as e:
                                        st.error(f"Error al publicar en Instagram: {str(e)}")

                            elif platform_lower.startswith("gmail"):
                                try:
                                    send_mail(
                                        subject=asunto,
                                        content_text=text,
                                        content_html=post.get('content_html'),
                                        receivers=contacts,
                                        attachments=all_attachments
                                    )
                                    st.success("Correo enviado exitosamente.")
                                except Exception as e:
                                    st.error(f"Error al enviar el correo: {str(e)}")

                            elif platform_lower.startswith("wordpress"):
                                try:
                                    st.info("Iniciando publicación en WordPress...")
                                    embedded_media_html = []

                                    # Recorrer todas las imágenes para incrustarlas
                                    for asset_path in image_paths:
                                        st.info(f"Subiendo imagen para incrustar: {os.path.basename(asset_path)}...")
                                        wp_media_info = upload_media(asset_path)

                                        if wp_media_info and 'url' in wp_media_info:
                                            # Se añade la etiqueta HTML <img> para la imagen
                                            embedded_media_html.append(
                                                f'<p><img src="{wp_media_info["url"]}" alt="{title}"></p>')

                                    # Bucle para los vídeos
                                    for asset_path in video_paths:
                                        st.info(f"Subiendo vídeo para incrustar: {os.path.basename(asset_path)}...")
                                        wp_video_info = upload_media(asset_path)

                                        if wp_video_info and 'url' in wp_video_info:
                                            # Shortcode [video] de WordPress
                                            embedded_media_html.append(f'<p>[video src="{wp_video_info["url"]}"]</p>')

                                    # Construir contenido final y crear el post
                                    final_content = text + "\n\n" + "\n".join(embedded_media_html)

                                    st.info("Creando el post en WordPress...")

                                    wp_post = create_post_wordpress(
                                        title=title,
                                        content=final_content,
                                        status='publish'
                                    )

                                    if wp_post and 'id' in wp_post:
                                        st.success(f"¡Publicación en WordPress creada con éxito! ID: {wp_post['id']}")
                                        st.markdown(f"**Ver post:** [Enlace]({wp_post.get('link')})")
                                    else:
                                        st.error("Fallo al crear la publicación en WordPress.")
                                except Exception as e:
                                    st.error(f"Error al publicar en WordPress: {str(e)}")

                            elif platform_lower.startswith("whatsapp"):
                                st.error("Publicar directamente en WhatsApp no está soportado actualmente.")

                            elif platform_lower.startswith("linkedin"):
                                try:
                                    st.info("Iniciando publicación en LinkedIn...")
                                    linkedin_client = LinkedInClient()

                                    # Se prioriza vídeo sobre imágenes
                                    video_to_post = video_paths[0] if video_paths else None
                                    images_to_post = image_paths if not video_to_post and image_paths else None

                                    linkedin_client.post(
                                        text=text,
                                        video_path=video_to_post,
                                        image_paths=images_to_post
                                    )
                                    st.success("¡Publicación en LinkedIn realizada con éxito!")
                                except Exception as e:
                                    st.error(f"Error al publicar en LinkedIn: {str(e)}")

    else:
        st.warning("No hay publicaciones que coincidan con los filtros aplicados.")


def create_image_carousel(images, platform):
    # Verificar si realmente hay imágenes para mostrar
    if not images:
        st.info("No hay imágenes adjuntas.")
        return

    # Crear el expander para mostrar las imágenes
    with st.expander("📸 Imágenes adjuntas", expanded=True):
        # Mostrar información sobre las imágenes
        num_images = len(images)
        st.markdown(f"**{num_images} {'imagen' if num_images == 1 else 'imágenes'} adjuntas:**")

        # Calcular cuántas columnas se necesitan
        cols = st.columns(min(4, num_images))

        for i, img in enumerate(images):
            with cols[i % len(cols)]:
                try:
                    # Comprobrar de que se puede procesar este tipo de imagen
                    if hasattr(img, 'seek'):
                        img.seek(0)  # Reiniciar el puntero del archivo

                    # Obtener y mostrar la imagen
                    if hasattr(img, 'name'):
                        caption = f"Imagen {i+1}: {img.name}"
                    else:
                        caption = f"Imagen {i+1}"

                    st.image(img, caption=caption, width='stretch')

                    # Asegurarse de que el cursor vuelva al inicio para futuros usos
                    if hasattr(img, 'seek'):
                        img.seek(0)
                except Exception as e:
                    st.error(f"Error al mostrar la imagen {i+1}: {str(e)}")
