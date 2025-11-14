import streamlit as st
import time
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar
import os
from streamlit_autorefresh import st_autorefresh

from src.state import init_states
from src.db_config import get_programmed_posts, get_unprogrammed_posts, update_post

st.set_page_config(layout="wide")
init_states()

# Auto-refresco para sincronización con el scheduler en segundo plano.
st_autorefresh(interval=60000, key="calendar_autorefresh")

st.title("📅 Calendario de Publicaciones")
st.markdown('')

# Carga de datos centralizada: se ejecuta en cada carga/refresco/rerun.
programmed_posts = get_programmed_posts()
unprogrammed_posts = get_unprogrammed_posts()

st.session_state.programmed_posts_cache = programmed_posts

# Definir colores por plataforma
platform_colors = {
    "LinkedIn": "#0A66C2",
    "Instagram": "#E4405F",
    "WordPress": "#21759B",
    "Gmail": "#EA4335",
    "WhatsApp": "#25D366"
}

# Crear las columnas para la interfaz
col1, col2 = st.columns([7, 3])

# --- COLUMNA IZQUIERDA: CALENDARIO ---
with col1:
    if st.button("🔄 Actualizar Calendario", key="refresh_calendar_btn", width='stretch', type="primary"):
        get_programmed_posts.clear()
        get_unprogrammed_posts.clear()
        st.toast("Calendario actualizado.")
        st.rerun()

    calendar_events = []
    for post in programmed_posts:
        if post['fecha_hora']:
            try:
                fecha_hora = datetime.fromisoformat(post['fecha_hora'])
                fecha_fin = fecha_hora + pd.Timedelta(minutes=30)
                event = {
                    "id": str(post['id']),
                    "title": post['title'],
                    "start": fecha_hora.isoformat(),
                    "end": fecha_fin.isoformat(),
                    "backgroundColor": platform_colors.get(post['platform'], "#1E88E5"),
                    "borderColor": platform_colors.get(post['platform'], "#1E88E5"),
                    "textColor": "#ffffff",
                    "extendedProps": {"platform": post['platform']}
                }
                calendar_events.append(event)
            except Exception as e:
                st.warning(f"Error al procesar publicación {post['id']}: {str(e)}")

    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay,listMonth"
        },
        "initialView": "dayGridMonth",
        "editable": False,
        "selectable": True,
        "selectMirror": True,
        "dayMaxEvents": True,
        "weekNumbers": True,
        "navLinks": True,
        "resourceGroupField": "platform",
        "resources": [
            {"id": "linkedin", "title": "LinkedIn"},
            {"id": "instagram", "title": "Instagram"},
            {"id": "wordpress", "title": "WordPress"},
            {"id": "gmail", "title": "Gmail"},
            {"id": "whatsapp", "title": "WhatsApp"}
        ],
    }

    custom_css = """
        .fc-event-past { opacity: 0.8; }
        .fc-event-time { font-style: italic; }
        .fc-event-title { font-weight: 700; }
        .fc-toolbar-title { font-size: 1.75rem; }
        .fc-event:hover {
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            transform: scale(1.02);
            transition: transform 0.2s ease;
        }
    """

    calendar_result = calendar(
        events=calendar_events,
        options=calendar_options,
        custom_css=custom_css,
        key="calendar_main"
    )

    if calendar_result and "callback" in calendar_result:
        callback = calendar_result["callback"]

        if callback == "eventClick":
            post_id = int(calendar_result["eventClick"]["event"]["id"])
            st.session_state.selected_event_id = post_id
            st.rerun()

# LISTA DE PUBLICACIONES
with col2:
    tab_unprogrammed, tab_programmed = st.tabs(["💾 Sin programar", "📅 Programadas"])

    with tab_unprogrammed:
        all_platforms = ["Todas"] + list(platform_colors.keys())
        selected_platform = st.selectbox(
            "Filtrar por plataforma:",
            all_platforms,
            key="platform_filter_unprogrammed"
        )

        # Filtrar los posts originales
        if selected_platform != "Todas":
            filtered_posts_unprogrammed = [p for p in unprogrammed_posts if p['platform'] == selected_platform]
        else:
            filtered_posts_unprogrammed = unprogrammed_posts

        if not filtered_posts_unprogrammed:
            st.info("No hay publicaciones sin programar para la plataforma seleccionada.")
        else:
            filtered_posts = sorted(filtered_posts_unprogrammed, key=lambda x: x['created_at'], reverse=True)
            for post in filtered_posts:
                with st.expander(post['title']):
                    col_date, col_time = st.columns(2)
                    with col_date:
                        fecha = st.date_input("Fecha", value=datetime.now().date() + pd.Timedelta(days=1),
                                              key=f"date_input_{post['id']}")
                    with col_time:
                        hora = st.time_input("Hora", value=datetime.now().time().replace(second=0, microsecond=0),
                                             key=f"time_input_{post['id']}", step=300)

                    if st.button("📅 Programar", key=f"program_btn_{post['id']}", width='stretch'):
                        fecha_hora_programada = datetime.combine(fecha, hora)
                        if fecha_hora_programada <= datetime.now():
                            st.error("La fecha y hora de programación deben ser futuras.")
                        else:
                            success = update_post(post['id'], fecha_hora=fecha_hora_programada.isoformat())
                            if success:
                                st.toast("Publicación programada con éxito.")
                                get_programmed_posts.clear()
                                get_unprogrammed_posts.clear()
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("No se pudo programar la publicación.")

                    st.markdown("---")
                    if post.get('contacts'):
                        st.markdown(f"#### 👥 {len(post['contacts'])} Destinatarios")
                        contact_cols = st.columns(2)
                        for i, contacto in enumerate(post['contacts']):
                            with contact_cols[i % 2]:
                                icon = "✉️" if post['platform'].lower().startswith("gmail") else "📱"
                                st.markdown(f"{icon} `{contacto}`", unsafe_allow_html=True)

                    st.markdown("#### 📄 Vista previa del contenido")
                    if post['platform'].lower().startswith("gmail"):
                        st.markdown(f"**Asunto:** {post.get('asunto', 'Sin asunto')}")

                    # Limpiar el contenido de los delimitadores '---' que añade la IA
                    content_to_display = post['content'].strip()
                    if content_to_display.startswith("---"):
                        content_to_display = content_to_display[3:].lstrip()
                    if content_to_display.endswith("---"):
                        content_to_display = content_to_display[:-3].rstrip()

                    st.markdown(content_to_display, unsafe_allow_html=True)

                    if post.get('media_assets'):
                        with st.expander("🖼️ Ver Medios Adjuntos"):
                            images = [a for a in post['media_assets'] if a['file_type'] == 'image']
                            videos = [a for a in post['media_assets'] if a['file_type'] == 'video']

                            if images:
                                st.markdown("##### Imágenes")
                                cols = st.columns(min(len(images), 4))
                                for i, asset in enumerate(images):
                                    file_path = asset['file_path']
                                    if os.path.exists(file_path):
                                        try:
                                            # Leer el fichero en modo binario ('rb')
                                            with open(file_path, 'rb') as f:
                                                image_bytes = f.read()
                                            cols[i % 4].image(image_bytes, width='stretch')
                                        except Exception as e:
                                            cols[i % 4].error(f"Error al cargar imagen.")

                            if videos:
                                st.markdown("##### Vídeos")
                                for asset in videos:
                                    file_path = asset['file_path']
                                    if os.path.exists(file_path):
                                        try:
                                            # Leer el fichero en modo binario ('rb')
                                            with open(file_path, 'rb') as f:
                                                video_bytes = f.read()
                                            st.video(video_bytes)
                                        except Exception as e:
                                            st.error(f"No se pudo cargar el vídeo: {file_path}. Error: {e}")

    with tab_programmed:
        all_platforms_prog = ["Todas"] + list(platform_colors.keys())
        selected_platform_prog = st.selectbox(
            "Filtrar por plataforma:",
            all_platforms_prog,
            key="platform_filter_programmed"
        )

        # Filtrar los posts originales
        if selected_platform_prog != "Todas":
            filtered_posts_programmed = [p for p in programmed_posts if p['platform'] == selected_platform_prog]
        else:
            filtered_posts_programmed = programmed_posts

        if not filtered_posts_programmed:
            st.info("No hay publicaciones programadas para la plataforma seleccionada.")
        else:
            filtered_posts = sorted(filtered_posts_programmed, key=lambda x: datetime.fromisoformat(x['fecha_hora']))
            for post in filtered_posts:
                dt_actual = datetime.fromisoformat(post['fecha_hora'])
                expander_title = f"{post['title']} ({dt_actual.strftime('%d/%m %H:%M')})"

                # Lógica para expandir el expander si su ID coincide con el del evento clickeado
                is_selected = (st.session_state.selected_event_id == post['id'])

                with st.expander(expander_title, expanded=is_selected):
                    col_date, col_time = st.columns(2)
                    with col_date:
                        nueva_fecha = st.date_input("Nueva fecha", value=dt_actual.date(), key=f"reprogram_date_{post['id']}")
                    with col_time:
                        nueva_hora = st.time_input("Nueva hora", value=dt_actual.time(), key=f"reprogram_time_{post['id']}", step=300)

                    if st.button("🔄 Reprogramar", key=f"reprogram_btn_{post['id']}", width='stretch'):
                        fecha_hora_reprogramada = datetime.combine(nueva_fecha, nueva_hora)
                        if fecha_hora_reprogramada <= datetime.now():
                            st.error("La fecha y hora de reprogramación deben ser futuras.")
                        else:
                            success = update_post(post['id'], fecha_hora=fecha_hora_reprogramada.isoformat())
                            if success:
                                st.toast("Publicación reprogramada con éxito.")
                                get_programmed_posts.clear()
                                get_unprogrammed_posts.clear()
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("No se pudo reprogramar la publicación.")

                    if st.button("❌ Cancelar programación", key=f"cancel_btn_{post['id']}", width='stretch'):
                        success = update_post(post['id'], fecha_hora=None)
                        if success:
                            st.toast("Programación cancelada.")
                            get_programmed_posts.clear()
                            get_unprogrammed_posts.clear()
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("No se pudo cancelar la programación.")

                    st.markdown("---")
                    if post.get('contacts'):
                        st.markdown(f"#### 👥 {len(post['contacts'])} Destinatarios")
                        contact_cols = st.columns(2)
                        for i, contacto in enumerate(post['contacts']):
                            with contact_cols[i % 2]:
                                icon = "✉️" if post['platform'].lower().startswith("gmail") else "📱"
                                st.markdown(f"<small>{icon} `{contacto}`</small>", unsafe_allow_html=True)

                    st.markdown("#### 📄 Vista previa del contenido")
                    if post['platform'].lower().startswith("gmail"):
                        st.markdown(f"**Asunto:** {post.get('asunto', 'Sin asunto')}")

                    # Limpiar el contenido de los delimitadores '---' que añade la IA
                    content_to_display = post['content'].strip()
                    if content_to_display.startswith("---"):
                        content_to_display = content_to_display[3:].lstrip()
                    if content_to_display.endswith("---"):
                        content_to_display = content_to_display[:-3].rstrip()

                    st.markdown(content_to_display, unsafe_allow_html=True)

                    if post.get('media_assets'):
                        with st.expander("🖼️ Ver Medios Adjuntos"):
                            images = [a for a in post['media_assets'] if a['file_type'] == 'image']
                            videos = [a for a in post['media_assets'] if a['file_type'] == 'video']
                            if images:
                                st.markdown("##### Imágenes")
                                cols = st.columns(min(len(images), 4))
                                for i, asset in enumerate(images):
                                    file_path = asset['file_path']
                                    if os.path.exists(file_path):
                                        try:
                                            # Leer el fichero en modo binario ('rb')
                                            with open(file_path, 'rb') as f:
                                                image_bytes = f.read()
                                            cols[i % 4].image(image_bytes, width='stretch')
                                        except Exception as e:
                                            cols[i % 4].error(f"Error al cargar imagen.")
                            if videos:
                                st.markdown("##### Vídeos")
                                for asset in videos:
                                    file_path = asset['file_path']
                                    if os.path.exists(file_path):
                                        try:
                                            # Leer el fichero en modo binario ('rb')
                                            with open(file_path, 'rb') as f:
                                                video_bytes = f.read()
                                            st.video(video_bytes)
                                        except Exception as e:
                                            st.error(f"No se pudo cargar el vídeo: {file_path}. Error: {e}")


if "selected_event_id" in st.session_state:
    st.session_state.selected_event_id = None
