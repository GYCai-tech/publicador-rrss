import streamlit as st
from src.auth import check_password

# Verificar autenticación
if not check_password():
    st.stop()

import os
import time
import shutil
import tempfile
from uuid import uuid4
from streamlit_tags import st_tags
from datetime import datetime
import pandas as pd
import html2text
import re

from src.db_config import get_all_media_assets, create_media_asset, create_post, link_media_to_post, title_already_exists
from src.db_config import get_all_contacts, get_all_contact_lists, get_contacts_by_list
from src import models, prompts
from src.graph_mail import EMAIL_FOOTER, markdown_to_html
from src.openai_video_generator import generar_guion_con_openai, generar_tts_con_openai, VOICES
from src.video import create_video_from_media
from src.utils import save_uploaded_media, image_to_base64, get_image_preview, validar_contacto, get_logo_path
from src.state import init_states



init_states()
st.set_page_config(layout="wide")

st.title("✍️ Generación de Contenido")

col_form, empty_col, col_preview = st.columns([5, 0.1, 5])

with col_form:
    with st.container(border=True):
        st.markdown("### 📸 Gestión de Medios")
        st.markdown(
            "Sube imágenes o vídeos para añadirlos directamente a tu biblioteca de medios."
        )

        def add_files_to_stage():
            if 'temp_media_files' not in st.session_state:
                st.session_state.temp_media_files = []
            new_files = st.session_state.get("media_uploader_widget", [])
            if not new_files:
                return
            current_names = [f.name for f in st.session_state.temp_media_files]
            added_count = 0
            for file in new_files:
                if file.name not in current_names:
                    st.session_state.temp_media_files.append(file)
                    added_count += 1
            if added_count > 0:
                st.toast(f"Se han cargado {added_count} nuevos medios. Confirma para añadirlos.", icon="👍")

        st.file_uploader(
            "Sube una o más imágenes o vídeos",
            type=["jpg", "jpeg", "png", "mp4", "mov", "avi", "mkv", "webm"],
            accept_multiple_files=True,
            key="media_uploader_widget",
            on_change=add_files_to_stage
        )

        # Comprobar si hay archivos en preparación
        if 'temp_media_files' in st.session_state and st.session_state.temp_media_files:
            num_files = len(st.session_state.temp_media_files)

            button_text = f"✅ Confirmar y añadir {num_files} {'medio' if num_files == 1 else 'medios'} a la Biblioteca"

            if st.button(button_text, width='stretch', type="primary"):
                with st.spinner("Procesando y guardando medios..."):
                    saved_assets = save_uploaded_media(st.session_state.temp_media_files)

                    if saved_assets:
                        st.success(f"¡Se han añadido {len(saved_assets)} medios a la biblioteca!")

                    # Limpiar la lista de archivos temporales y refrescar
                    st.session_state.temp_media_files = []
                    time.sleep(1)
                    st.rerun()

    # Contenedor para la sección de Vídeos
    with st.container(border=True):
        st.markdown("### 🎬 Generador de Vídeos")
        st.markdown(
            "Crea un vídeo a partir de un tema, imágenes y/o vídeos cortos. Podrás previsualizar el resultado antes de añadirlo a tu biblioteca de medios."
        )

        # Si hay un vídeo para previsualizar, se muestra aquí
        if st.session_state.preview_video_path:
            st.markdown("#### Previsualización del Vídeo Generado")
            video_path = st.session_state.preview_video_path
            st.video(video_path)

            col1, col2, col3 = st.columns(3)

            # Botón 1: Añadir a la Biblioteca y mover vídeo a media
            with col1:
                if st.button("✅ Añadir a la Biblioteca", width='stretch', type="primary"):
                    with st.spinner("Moviendo y añadiendo a la biblioteca..."):
                        try:
                            MEDIA_DIR = "media"
                            os.makedirs(MEDIA_DIR, exist_ok=True)
                            video_filename = os.path.basename(video_path)
                            new_video_path = os.path.join(MEDIA_DIR, video_filename)

                            shutil.move(video_path, new_video_path)

                            create_media_asset(
                                file_path=new_video_path,
                                file_type='video',
                                original_filename=video_filename
                            )

                            st.success("¡Vídeo añadido a la biblioteca con éxito!")
                            st.session_state.preview_video_path = None
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al añadir el vídeo a la biblioteca: {e}")

            # Botón 2: Descargar sin Guardar
            with col2:
                # Primero, leer el archivo de vídeo en memoria
                try:
                    with open(video_path, "rb") as file:
                        video_bytes = file.read()

                    # Botón de descarga
                    st.download_button(
                        label="📥 Descargar sin guardar",
                        data=video_bytes,
                        file_name=os.path.basename(video_path),
                        mime="video/mp4",
                        width='stretch'
                    )
                except FileNotFoundError:
                    st.warning("El archivo de vídeo ya no existe para ser descargado.")

            # Botón 3: Descartar (con limpieza de archivo)
            with col3:
                if st.button("🗑️ Descartar Vídeo", width='stretch'):
                    try:
                        if video_path and os.path.exists(video_path):
                            os.remove(video_path)
                            st.toast("Vídeo descartado y archivo temporal eliminado.")
                        else:
                            st.toast("Vídeo descartado de la sesión.")
                    except OSError as e:
                        st.warning(f"Error al eliminar el archivo: {e}")

                    st.session_state.preview_video_path = None
                    st.rerun()

            st.markdown("---")

        media_files = st.file_uploader(
            "Sube las imágenes y/o vídeos cortos para el vídeo (el orden de subida será el orden en el vídeo)",
            type=["jpg", "png", "jpeg", "mp4", "mov"],
            accept_multiple_files=True,
            key="video_media_files"
        )

        col1_res, col2_voice = st.columns(2)
        with col1_res:
            RESOLUTIONS = {
                "Vertical 9:16 (1080x1920)": (1080, 1920),
                "Cuadrado 1:1 (1080x1080)": (1080, 1080),
                "Horizontal 16:9 (1920x1080)": (1920, 1080)
            }
            video_resolution = st.selectbox(
                "Elige la resolución:",
                options=RESOLUTIONS.keys(),
                key="video_standalone_resolution"
            )
        with col2_voice:
            video_voice = st.selectbox(
                "Elige una voz para la locución:",
                options=VOICES,
                index=VOICES.index("nova"),
                key="video_standalone_voice"
            )

            # Ruta al fichero de audio de la voz seleccionada
            preview_path = f"assets/audio_previews/{video_voice}.mp3"

            # Mostrar el reproductor de audio si el fichero existe
            if os.path.exists(preview_path):
                st.audio(preview_path, format="audio/mp3")
            else:
                st.caption("Vista previa no disponible para esta voz.")

        # Previsualización de los medios subidos
        if media_files:
            with st.expander("🖼️ Previsualizar medios subidos", expanded=True):
                st.info("Así se verán los medios en el vídeo final. Los vídeos se mostrarán sin audio y ajustados a la duración.")
                target_size = RESOLUTIONS[video_resolution]

                num_cols = min(len(media_files), 3)
                cols = st.columns(num_cols)

                for i, uploaded_file in enumerate(media_files):
                    with cols[i % num_cols]:
                        # Distinguir entre imagen y vídeo para la previsualización
                        if uploaded_file.type.startswith('image/'):
                            image_bytes = uploaded_file.getvalue()
                            preview = get_image_preview(image_bytes, target_size)
                            if preview:
                                st.image(preview, caption=f"Imagen: {uploaded_file.name}", width='stretch')
                            else:
                                st.warning(f"No se pudo previsualizar {uploaded_file.name}")
                        elif uploaded_file.type.startswith('video/'):
                            st.video(uploaded_file.getvalue())
                            st.caption(f"Vídeo: {uploaded_file.name}")

        with st.form("video_generation_form"):
            video_topic = st.text_area(
                "Tema principal para el guion del vídeo",
                placeholder="Ej: 'La importancia de la ventilación en granjas de conejos'",
                key="video_standalone_topic"
            )
            submit_video = st.form_submit_button("📹 Generar Vídeo", width='stretch', type="primary")

        if submit_video:
            if not video_topic or not media_files:
                st.error("Para generar el vídeo, se necesita un tema y al menos una imagen o vídeo.")
            else:
                with st.status("Iniciando generación de vídeo...", expanded=True) as status:
                    try:
                        status.update(label="Paso 1/3: Generando guion con IA...")
                        info_empresa = prompts.get_GyC_info()
                        guion = generar_guion_con_openai(tema=video_topic, info_empresa=info_empresa)
                        if not guion: raise Exception("Fallo al generar el guion.")
                        st.success(f"Guion generado: '{guion}'")

                        status.update(label="Paso 2/3: Creando locución de audio...")
                        os.makedirs("temp", exist_ok=True)
                        tts_path = f"temp/{uuid4()}.mp3"

                        if not generar_tts_con_openai(guion, tts_path, voz=video_voice, usar_prompt_complejo=True): raise Exception("Fallo al generar el audio TTS.")
                        st.success("Locución guardada.")

                        status.update(label="Paso 3/3: Renderizando vídeo final... (este paso puede tardar)")
                        # Guardar temporalmente tanto imágenes como vídeos
                        temp_media_paths = []
                        for uploaded_file in media_files:
                            # Extraer la extensión original para guardarla correctamente
                            file_extension = os.path.splitext(uploaded_file.name)[1]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
                                tmp.write(uploaded_file.getvalue())
                                temp_media_paths.append(tmp.name)

                        os.makedirs("output", exist_ok=True)
                        video_final_path = f"output/video_{uuid4()}.mp4"
                        target_size = RESOLUTIONS[video_resolution]

                        create_video_from_media(
                            media_paths=temp_media_paths, audio_path=tts_path,
                            output_path=video_final_path, threads=8, target_size=target_size
                        )

                        st.session_state.preview_video_path = video_final_path

                        for path in temp_media_paths: os.remove(path)
                        os.remove(tts_path)

                        status.update(label="¡Vídeo listo para revisión!", state="complete", expanded=False)
                        time.sleep(0.5)
                        st.rerun()

                    except Exception as e:
                        status.update(label=f"Error durante la generación: {e}", state="error")

    # Contenedor para la sección de Publicaciones de Texto
    with st.container(border=True):
        st.markdown("### ✍️ Generador de Publicaciones de Texto")
        st.markdown("Selecciona las plataformas y define el contenido de texto que deseas crear.")

        # Selección de plataformas
        st.markdown("##### 1. Selecciona las plataformas")
        cols = st.columns(5)
        platform_names = ["LinkedIn", "Instagram", "WordPress", "Gmail", "WhatsApp"]
        platform_colors = ["#0A66C2", "#E4405F", "#21759B", "#EA4335", "#25D366"]

        st.session_state.selected_platforms = []
        for i, name in enumerate(platform_names):
            with cols[i]:
                logo_path = f"assets/logos/{name.lower()}.png"
                logo_base64 = image_to_base64(logo_path)
                st.markdown(
                    f'<div style="display: flex; align-items: center; justify-content: center; flex-direction: column; text-align: center;">'
                    f'<img src="data:image/png;base64,{logo_base64}" style="width: 32px; height: 32px; margin-bottom: 8px;">'
                    f'<span style="color: {platform_colors[i]}; font-weight: bold;">{name}</span>'
                    '</div>', unsafe_allow_html=True)

                is_selected = st.checkbox(name, key=f"platform_select_{name.lower()}", label_visibility="collapsed")

                if is_selected:
                    st.session_state.selected_platforms.append(name)

        # Formulario para los detalles del contenido de texto
        with st.form("content_form"):
            st.markdown("##### 2. Define los detalles de la publicación")
            col1, col2 = st.columns(2)
            with col1:
                objetivo = st.selectbox("Objetivo Principal 🎯",
                                        ["Generar leads", "Vender", "Informar", "Branding", "Interactuar", "Educar",
                                         "Entretener", "Fidelizar clientes", "Aumentar seguidores",
                                         "Generar tráfico web", "Posicionamiento SEO", "Lanzamiento de producto",
                                         "Servicio al cliente", "Gestión de crisis", "Encuestas y feedback"],
                                        help="¿Qué buscas lograr? Es la brújula del contenido")
            with col2:
                audiencia = st.multiselect("Audiencia Clave 👥", ["Empresarios", "Emprendedores", "Directivos",
                                                                 "Profesionales independientes",
                                                                 "Estudiantes universitarios", "Millennials",
                                                                 "Generación Z", "Baby Boomers",
                                                                 "Padres de familia",
                                                                 "Pequeñas empresas", "Medianas empresas",
                                                                 "Grandes corporaciones", "Sector público", "ONGs",
                                                                 "Instituciones educativas"],
                                           help="Selecciona uno o más perfiles de tu audiencia objetivo",
                                           placeholder="Selecciona tu audiencia objetivo...")

            mensaje = st.text_area("Mensaje Central 💡",
                                   placeholder="Resume brevemente la idea clave que quieres transmitir... \nPor defecto: 'Con la información que tienes, elige una temática que consideres acertada para las publicaciones'",
                                   help="El corazón del contenido", height=100, key="mensaje_area")

            col1, col2 = st.columns(2)
            with col1:
                tono = st.selectbox("Tono Deseado 🎭",
                                    ["Profesional", "Cercano", "Formal", "Informal", "Divertido", "Urgente",
                                     "Educativo", "Inspirador"], help="Define la personalidad del contenido")
            with col2:
                cta = st.selectbox("Llamada a la Acción (CTA) 🎯",
                                   ["Comprar ahora", "Registrarse", "Más información", "Contactar",
                                    "Agendar una cita",
                                    "Descargar gratis", "Suscribirse al newsletter", "Ver catálogo completo",
                                    "Solicitar demostración", "Unirse al grupo", "Seguirnos en redes",
                                    "Compartir publicación", "Comentar experiencia", "Participar en sorteo",
                                    "Visitar tienda física", "Llamar ahora", "Enviar mensaje",
                                    "Realizar consulta gratuita"],
                                   help="Selecciona la acción principal que deseas que realice tu audiencia")

            keywords = st_tags(label="Palabras Clave Principales 🔑",
                               text="Presiona enter para agregar más palabras",
                               value=[], maxtags=8, key="keywords_tags")

            submit_text = st.form_submit_button("✍️ Generar Publicaciones de Texto", width='stretch')

            if submit_text:
                if not st.session_state.selected_platforms:
                    st.warning("Por favor, selecciona al menos una plataforma para generar el contenido.")
                else:
                    st.session_state.form_data = {"mensaje": mensaje, "objetivo": objetivo, "audiencia": audiencia,
                                                  "tono": tono, "cta": cta, "keywords": keywords}
                    st.session_state.results = {}
                    with st.spinner("Generando contenido de texto..."):
                        common_data = {k: v for k, v in st.session_state.form_data.items()}
                        st.session_state.results = models.generate_content(st.session_state.selected_platforms, common_data)
                    st.toast("Contenido de texto generado. ¡Revisa la columna derecha!", icon="🎉")

with empty_col:
    st.markdown("""
                    <div style="border-left: 2px solid #e6e6e6; height: 100vh; margin: 0 auto;"></div>
                """, unsafe_allow_html=True)

# Columna derecha (previsualizaciones)
with col_preview:
    if 'content_history' not in st.session_state:
        st.session_state.content_history = {}
    # Unir plataformas seleccionadas y plataformas con contenido para mostrar
    platforms_to_show = sorted(st.session_state.get('results', {}).keys())

    if platforms_to_show:
        tabs = st.tabs([f"{plat}" for plat in platforms_to_show])

        # Obtener todos los medios de la biblioteca
        all_media_assets = get_all_media_assets()
        asset_options = {
            asset['id']: f"[{asset['file_type'].upper()}] - {asset.get('original_filename', os.path.basename(asset['file_path']))}"
            for asset in all_media_assets
        }

        for i, (platform, tab) in enumerate(zip(platforms_to_show, tabs)):
            with tab:
                # st.write(f"DEBUG: Plataforma actual: '{platform}'") # Descomentar si es necesario depurar
                content = st.session_state.results[platform]["content"]
                asunto = st.session_state.results[platform].get("asunto", "")

                # Inicialización de variables de estado
                if f"title_{platform}" not in st.session_state:
                    st.session_state[f"title_{platform}"] = f"Publicación para {platform}"
                if platform not in st.session_state.content_history:
                    st.session_state.content_history[platform] = [content]
                if f"editing_{platform}" not in st.session_state:
                    st.session_state[f"editing_{platform}"] = False
                if f"edited_content_{platform}" not in st.session_state:
                    st.session_state[f"edited_content_{platform}"] = content
                if f"edited_asunto_{platform}" not in st.session_state:
                    st.session_state[f"edited_asunto_{platform}"] = asunto
                # Inicialización de contactos
                if f"contacts_{platform}" not in st.session_state:
                    st.session_state[f"contacts_{platform}"] = []

                # Contenedor con icono de plataforma
                c1, c2, c3 = st.columns([1, 8, 2])
                with c1:
                    image_path = get_logo_path(platform)
                    if os.path.exists(image_path):
                        st.image(image_path, width=70)

                with c2:
                    title = st.text_input(
                        "Título",
                        value=st.session_state[f"title_{platform}"],
                        key=f"title_input_{platform}",
                        label_visibility="collapsed"
                    )
                    st.session_state[f"title_{platform}"] = title

                # MODO EDICIÓN
                if st.session_state[f"editing_{platform}"]:
                    if platform.lower().startswith("gmail"):
                        st.session_state[f"edited_asunto_{platform}"] = st.text_input(
                            "Asunto",
                            value=st.session_state.get(f"edited_asunto_{platform}", ""),
                            key=f"asunto_input_edit_{platform}"
                        )

                        # Botones de formato para Gmail
                        st.markdown("##### 🎨 Formato de texto:")
                        fmt_col1, fmt_col2, fmt_col3, fmt_col4, fmt_col5 = st.columns(5)

                        with fmt_col1:
                            if st.button("**B** Negrita", key=f"bold_{platform}", help="Envuelve el texto seleccionado con **", use_container_width=True):
                                st.info("💡 Para negrita: Escribe **tu texto aquí** en el editor")
                        with fmt_col2:
                            if st.button("*I* Cursiva", key=f"italic_{platform}", help="Envuelve el texto seleccionado con *", use_container_width=True):
                                st.info("💡 Para cursiva: Escribe *tu texto aquí* en el editor")
                        with fmt_col3:
                            if st.button("📝 Lista", key=f"list_{platform}", help="Agrega viñetas", use_container_width=True):
                                st.info("💡 Para lista: Escribe\n- Elemento 1\n- Elemento 2")
                        with fmt_col4:
                            if st.button("1️⃣ Numerada", key=f"numlist_{platform}", help="Agrega lista numerada", use_container_width=True):
                                st.info("💡 Para lista numerada: Escribe\n1. Primero\n2. Segundo")
                        with fmt_col5:
                            if st.button("🔗 Enlace", key=f"link_{platform}", help="Añadir hipervínculo", use_container_width=True):
                                st.session_state[f"show_link_form_{platform}"] = not st.session_state.get(f"show_link_form_{platform}", False)

                        # Formulario de hipervínculo
                        if st.session_state.get(f"show_link_form_{platform}", False):
                            with st.container(border=True):
                                st.caption("🔗 Convertir texto en hipervínculo")
                                st.markdown(
                                    "<small>Escribe en el editor el texto que quieres enlazar, "
                                    "luego cópialo aquí y añade la URL.</small>",
                                    unsafe_allow_html=True
                                )
                                lc1, lc2 = st.columns(2)
                                with lc1:
                                    link_text = st.text_input(
                                        "Texto a enlazar",
                                        placeholder="p.ej. visita nuestra web",
                                        key=f"link_text_{platform}",
                                        help="Debe aparecer exactamente así en el texto del editor"
                                    )
                                with lc2:
                                    link_url = st.text_input(
                                        "URL de destino",
                                        placeholder="https://gomezycrespo.com",
                                        key=f"link_url_{platform}"
                                    )
                                if st.button("✅ Aplicar enlace", key=f"insert_link_{platform}", use_container_width=True, type="primary"):
                                    if link_text and link_url:
                                        current = st.session_state.get(f"textarea_{platform}", st.session_state[f"edited_content_{platform}"])
                                        if link_text in current:
                                            updated = current.replace(link_text, f"[{link_text}]({link_url})", 1)
                                            st.session_state[f"edited_content_{platform}"] = updated
                                            if f"textarea_{platform}" in st.session_state:
                                                del st.session_state[f"textarea_{platform}"]
                                            st.session_state[f"show_link_form_{platform}"] = False
                                            st.rerun()
                                        else:
                                            st.error(f'No se encontró el texto **"{link_text}"** en el editor. Cópialo exactamente como aparece.')
                                    else:
                                        st.warning("Rellena el texto y la URL")

                    edited = st.text_area(
                        'Modifique la publicación',
                        value=st.session_state[f"edited_content_{platform}"],
                        height=400,
                        key=f"textarea_{platform}",
                        help="Usa **texto** para negrita, *texto* para cursiva, [texto](url) para enlaces"
                    )

                    # Botones de acción para edición
                    col1, col2 = st.columns(2)
                    
                    # --- VISTA PREVIA EN TIEMPO REAL (MODO EDICIÓN) ---
                    if platform.lower().startswith("gmail"):
                        st.markdown("---")
                        st.caption("👀 Vista previa en tiempo real:")
                        # Intentamos coger el valor del widget (lo que estás escribiendo ahora mismo)
                        # Si no existe (primera carga), cogemos el guardado.
                        live_text = st.session_state.get(f"textarea_{platform}", st.session_state[f"edited_content_{platform}"])
                        # Convertir markdown a HTML
                        formatted_html = markdown_to_html(live_text)
                        preview_html = f"<div style='font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;'>{formatted_html}</div>{EMAIL_FOOTER}"
                        st.markdown(preview_html, unsafe_allow_html=True)
                        st.markdown("---")
                    # --------------------------------------------------
                    if col1.button("💾 Guardar", key=f"save_edit_{platform}", width='stretch'):
                        st.session_state[f"editing_{platform}"] = False
                        # Limpiar espacios y saltos de línea al final del texto
                        cleaned_text = edited.rstrip()
                        # Guardar el texto limpio
                        st.session_state[f"edited_content_{platform}"] = cleaned_text
                        if cleaned_text != st.session_state.content_history[platform][-1]:
                            st.session_state.content_history[platform].append(cleaned_text)

                        # Para Gmail: actualizar también el content_html con el texto editado
                        if platform.lower().startswith("gmail"):
                            # Convertir markdown a HTML
                            formatted_body = markdown_to_html(cleaned_text)
                            # Regenerar HTML desde el texto editado
                            new_html = f"""
                            <html>
                            <body>
                                <div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;">
                                    {formatted_body}
                                </div>
                            </body>
                            </html>
                            """
                            # Actualizar el content_html en los resultados
                            st.session_state.results[platform]["content_html"] = new_html

                        st.rerun()

                    if col2.button("↻ Deshacer ediciones anteriores", key=f"undo_{platform}", width='stretch'):
                        if len(st.session_state.content_history[platform]) > 1:
                            st.session_state.content_history[platform].pop()
                            st.session_state[f"edited_content_{platform}"] = st.session_state.content_history[platform][-1]
                            st.toast("Cambios deshechos")
                            st.rerun()
                        else:
                            st.toast("No hay más cambios para deshacer")

                # MODO VISUALIZACIÓN
                else:
                    with c3:
                        # Botón para descartar contenido
                        if st.button("🗑️ Descartar", key=f"discard_{platform}", type='primary', width='stretch'):
                            if platform in st.session_state.results:
                                del st.session_state.results[platform]

                            # Limpiamos variables específicas
                            keys_to_delete = [
                                f"title_{platform}",
                                f"editing_{platform}",
                                f"edited_content_{platform}",
                                f"edited_asunto_{platform}",
                                f"contacts_{platform}",
                                f"platform_images_{platform}"
                            ]
                            for key in keys_to_delete:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.success(f"Contenido para {platform} descartado")
                            st.rerun()

                    # Contenido
                    if platform.lower().startswith("gmail"):
                        st.markdown(f"**Asunto:** {st.session_state[f'edited_asunto_{platform}']}")
                        st.markdown("---")
                        st.caption("📧 Vista previa del mensaje final (incluyendo footer):")

                        # Obtener contenido actual editado
                        current_text = st.session_state[f'edited_content_{platform}']

                        # SIEMPRE convertir el texto actual a HTML para mostrar el formato markdown
                        formatted_text = markdown_to_html(current_text)
                        preview_html = f"<div style='font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;'>{formatted_text}</div>{EMAIL_FOOTER}"
                        st.markdown(preview_html, unsafe_allow_html=True)
                            
                    else:
                        st.markdown(f"<div class='theme-adaptable-container'>{st.session_state[f'edited_content_{platform}']}</div>", unsafe_allow_html=True)

                    # Botón de edición
                    st.button("✏️ Editar", key=f"start_edit_{platform}", on_click=lambda p=platform: st.session_state.update({f"editing_{p}": True}), width='stretch')
                    st.divider()

                    # Inicializar el estado para los adjuntos si no existe
                    if 'attachments' not in st.session_state:
                        st.session_state.attachments = {}

                    # Mostrar selector para adjuntar vídeo si hay vídeos generados
                    if st.session_state.get('video_results'):
                        st.markdown("---")
                        video_options = ["No adjuntar vídeo"] + [f"Vídeo de {p}" for p in st.session_state.video_results.keys()]

                        selected_video = st.selectbox(
                            "🎬 Adjuntar un vídeo a esta publicación",
                            options=video_options,
                            key=f"video_attachment_{platform}"
                        )
                        # Guardar la selección en el estado
                        st.session_state.attachments[platform] = selected_video

                    # Selector de contactos (Gmail y WhatsApp)
                    if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp"):
                        with st.expander("👥 Seleccionar Destinatarios"):
                            tipo_contacto_plural = "emails" if platform.lower().startswith("gmail") else "phones"
                            contact_label = "Direcciones de correo 📧" if platform.lower().startswith("gmail") else "Números de teléfono 📱"

                            # Asegurarse de que las listas para las selecciones existan en el estado de la sesión.
                            list_selection_key = f"selected_list_ids_{platform}"
                            contact_selection_key = f"selected_contact_ids_{platform}"
                            manual_contacts_key = f"manual_contacts_{platform}"

                            if list_selection_key not in st.session_state:
                                st.session_state[list_selection_key] = []
                            if contact_selection_key not in st.session_state:
                                st.session_state[contact_selection_key] = []
                            if manual_contacts_key not in st.session_state:
                                st.session_state[manual_contacts_key] = []

                            all_lists = get_all_contact_lists()
                            all_contacts_data = get_all_contacts()
                            valid_contacts = [c for c in all_contacts_data if c.get(tipo_contacto_plural)]

                            st.markdown("##### 1. Selecciona desde tus contactos guardados")
                            sc1, sc2 = st.columns(2)
                            with sc1:
                                list_options = {lst['id']: lst['name'] for lst in all_lists}
                                st.multiselect(
                                    "Desde Listas",
                                    options=list(list_options.keys()),
                                    format_func=lambda x: list_options.get(x, x),
                                    key=list_selection_key
                                )
                            with sc2:
                                contact_options = {c['id']: f"{c['name']}" for c in valid_contacts}
                                st.multiselect(
                                    "Desde Contactos Individuales",
                                    options=list(contact_options.keys()),
                                    format_func=lambda x: contact_options.get(x, x),
                                    key=contact_selection_key
                                )

                            # Calcular la lista de destinatarios en cada ejecución
                            destinations_from_selection = set()
                            
                            def clean_contact_list(raw_list):
                                """Ayuda a limpiar listas de contactos que puedan venir mal serializadas"""
                                cleaned = []
                                for item in raw_list:
                                    if isinstance(item, str):
                                        item = item.strip()
                                        # Si parece una lista serializada '["email"]'
                                        if item.startswith('[') and item.endswith(']'):
                                            try:
                                                # Intentar limpiar caracteres comunes de listas stringificadas
                                                inner = item.strip("[]").replace('"', '').replace("'", "").split(',')
                                                cleaned.extend([x.strip() for x in inner if x.strip()])
                                            except:
                                                cleaned.append(item)
                                        else:
                                            cleaned.append(item)
                                    else:
                                        cleaned.append(str(item))
                                return cleaned

                            # Obtener de las listas seleccionadas
                            if st.session_state[list_selection_key]:
                                for list_id in st.session_state[list_selection_key]:
                                    contacts_in_list = get_contacts_by_list(list_id)
                                    for contact in contacts_in_list:
                                        raw_contacts = contact.get(tipo_contacto_plural, [])
                                        destinations_from_selection.update(clean_contact_list(raw_contacts))

                            # Obtener de los contactos individuales seleccionados
                            if st.session_state[contact_selection_key]:
                                contacts_map = {c['id']: c for c in all_contacts_data}
                                for contact_id in st.session_state[contact_selection_key]:
                                    contact = contacts_map.get(contact_id)
                                    if contact:
                                        raw_contacts = contact.get(tipo_contacto_plural, [])
                                        destinations_from_selection.update(clean_contact_list(raw_contacts))

                            # Mostrar los destinatarios seleccionados para dar feedback visual al usuario
                            if destinations_from_selection:
                                st.markdown("###### Destinatarios añadidos desde tus selecciones:")
                                st.text_area(
                                    "Destinatarios seleccionados",
                                    value="\n".join(sorted(list(destinations_from_selection))),
                                    height=100,
                                    disabled=True,
                                    label_visibility="collapsed"
                                )

                            st.markdown("##### 2. Añade destinatarios manualmente (opcional)")
                            
                            # Obtener el valor actual del session state si existe
                            current_manual = ", ".join(st.session_state.get(manual_contacts_key, []))
                            
                            manual_text = st.text_input(
                                "Correos separados por coma",
                                value=current_manual,
                                placeholder="correo1@ejemplo.com, correo2@ejemplo.com",
                                key=f"manual_emails_{platform}"
                            )
                            if manual_text:
                                st.session_state[manual_contacts_key] = [e.strip() for e in manual_text.split(",") if e.strip()]
                            else:
                                st.session_state[manual_contacts_key] = []

                            # Combinar los destinatarios de las selecciones y los manuales.
                            final_destinations = destinations_from_selection.union(set(st.session_state[manual_contacts_key]))

                            contactos_validos, contactos_invalidos = [], []
                            for c in final_destinations:
                                es_valido, error = validar_contacto(c, "email" if platform.lower().startswith("gmail") else "telefono")
                                if es_valido:
                                    contactos_validos.append(c)
                                else:
                                    contactos_invalidos.append((c, error))

                            if contactos_invalidos:
                                st.warning("Algunos destinatarios manuales tienen un formato incorrecto y no se añadirán:")
                                for c, error in contactos_invalidos:
                                    st.caption(f"• '{c}': {error} (será eliminado)")

                    # Adjuntar Medios
                    with st.expander("📚 Adjuntar Medios de la Biblioteca"):
                        if not asset_options:
                            st.info("No hay medios en la biblioteca. Sube imágenes o genera vídeos para poder adjuntarlos.")
                        else:
                            # Comprobar que el estado para esta plataforma existe
                            # Nota: El key del multiselect maneja automáticamente el session state
                            multiselect_key = f"selected_media_ids_{platform}"

                            # Inicializar con lista vacía si no existe
                            if multiselect_key not in st.session_state:
                                st.session_state[multiselect_key] = []

                            st.multiselect(
                                "Selecciona imágenes o vídeos para esta publicación:",
                                options=list(asset_options.keys()),
                                format_func=lambda asset_id: asset_options.get(asset_id, "Medio no encontrado"),
                                key=multiselect_key
                            )

                            # Opción para incrustar imágenes (solo Gmail)
                            if platform.lower().startswith("gmail"):
                                inline_checked = st.checkbox(
                                    "Incrustar imágenes en el cuerpo del correo",
                                    key=f"inline_pref_{platform}",
                                    help="Si se marca, las imágenes aparecerán dentro del correo (antes del pie de página) en lugar de como adjuntos descargables.",
                                    value=False
                                )
                                if inline_checked:
                                    st.selectbox(
                                        "Tamaño de las imágenes",
                                        options=["Pequeño (300px)", "Mediano (600px)", "Grande (100%)"],
                                        index=1, # Por defecto Mediano
                                        key=f"img_size_pref_{platform}",
                                        help="Define el ancho máximo de las imágenes incrustadas."
                                    )

                            # DEBUG: Mostrar selección actual (leer directamente después del widget)
                            current_selection = st.session_state.get(multiselect_key, [])

                            # Logging adicional para debugging
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"DEBUG Multiselect - Platform: {platform}")
                            logger.info(f"DEBUG Multiselect - Key: {multiselect_key}")
                            logger.info(f"DEBUG Multiselect - Current value: {current_selection}")
                            logger.info(f"DEBUG Multiselect - Asset options available: {list(asset_options.keys())}")

                            if current_selection:
                                st.caption(f"✅ {len(current_selection)} archivo(s) seleccionado(s) - Se adjuntarán al programar/guardar")
                            else:
                                st.caption("ℹ️ No hay archivos seleccionados")

                            if platform.lower().startswith("instagram"):
                                st.info(
                                    """
                                    ℹ️ **Consejo para Carruseles:** La primera imagen que selecciones determinará el formato 
                                    (cuadrado, vertical, etc.) de todas las demás. Para evitar recortes no deseados,
                                    asegúrate de que todas las imágenes tengan la misma orientación.
                                    """
                                )

                            if platform.lower().startswith("linkedin"):
                                st.info(
                                    """
                                    ℹ️ **Reglas para adjuntar en LinkedIn:**
                                    - **Imágenes:** Puedes seleccionar una o varias imágenes para crear un carrusel.
                                    - **Vídeo:** Solo puedes seleccionar **un único vídeo**. Si seleccionas un vídeo, se ignorarán las imágenes.
                                    - No se pueden mezclar imágenes y vídeos en la misma publicación.
                                    """
                                )
                            # Vista previa
                            selected_assets = []
                            if st.session_state[f"selected_media_ids_{platform}"]:
                                st.markdown("##### Vista Previa de Medios Seleccionados")
                                selected_assets = [asset for asset in all_media_assets if asset['id'] in st.session_state[f"selected_media_ids_{platform}"]]

                            num_cols = min(4, len(selected_assets)) if selected_assets else 1
                            preview_cols = st.columns(num_cols)
                            col_idx = 0
                            for asset in selected_assets:
                                with preview_cols[col_idx % 4]:
                                    if os.path.exists(asset['file_path']):
                                        if asset['file_type'] == 'image':
                                            st.image(asset['file_path'], width='stretch')
                                        elif asset['file_type'] == 'video':
                                            st.video(asset['file_path'])
                                        col_idx += 1

                    # Botón de regeneración
                    with st.expander("🔄 Regenerar Contenido"):
                        instrucciones = st.text_area('Instrucciones para regenerar el contenido', placeholder="Ej: Hazlo más corto y directo", key=f"instrucciones_{platform}", height=75)

                        if st.button("Regenerar", key=f"regen_{platform}", width='stretch'):
                            try:
                                if instrucciones:
                                    # Función de regeneración
                                    new_content_data = models.regenerate_post(
                                        platform=platform,
                                        content=st.session_state[f"edited_content_{platform}"],
                                        prompt=instrucciones,
                                        asunto=st.session_state.get(f"edited_asunto_{platform}")
                                    )

                                    # Actualizar el contenido de texto plano
                                    st.session_state[f"edited_content_{platform}"] = new_content_data["content"]
                                    st.session_state.content_history[platform].append(new_content_data["content"])

                                    # Si es un email, actualizar también el asunto y el HTML
                                    if platform.lower().startswith("gmail"):
                                        st.session_state[f"edited_asunto_{platform}"] = new_content_data.get("asunto")
                                        # Actualizar el HTML en el diccionario de resultados para que la vista previa se actualice
                                        st.session_state.results[platform]["content_html"] = new_content_data.get("content_html")

                                    st.success("Contenido regenerado exitosamente")
                                    st.rerun()
                                else:
                                    st.warning("Por favor, ingresa instrucciones para modificar el contenido")
                            except Exception as e:
                                st.error(f"Error al regenerar el contenido: {str(e)}")

                    with st.expander("🌍 Traducir Publicación"):
                        LANGUAGES = {"Inglés": "inglés", "Francés": "francés", "Alemán": "alemán",
                            "Portugués": "portugués", "Polaco": "polaco", "Italiano": "italiano"}

                        selected_languages = st.multiselect(
                            "Selecciona uno o más idiomas para traducir:",
                            options=list(LANGUAGES.keys()),
                            key=f"translate_langs_{platform}"
                        )

                        if st.button("Traducir y Crear Nuevas Publicaciones", key=f"translate_btn_{platform}", width='stretch', type="secondary"):
                            if not selected_languages:
                                st.warning("Por favor, selecciona al menos un idioma.")
                            else:
                                # Obtenemos el contenido actual para traducirlo
                                original_title = st.session_state[f"title_{platform}"]
                                original_content = st.session_state[f"edited_content_{platform}"]
                                original_asunto = st.session_state.get(f"edited_asunto_{platform}")

                                # Para WordPress/Gmail, es mejor traducir la versión HTML si existe
                                is_html_platform = platform.lower().startswith("gmail") or platform.lower().startswith("wordpress")
                                if is_html_platform:
                                    content_to_translate = st.session_state.results[platform].get("content_html", original_content)
                                else:
                                    content_to_translate = original_content

                                with st.spinner(f"Traduciendo a {len(selected_languages)} idioma(s)..."):
                                    for lang_key in selected_languages:
                                        lang_name = LANGUAGES[lang_key]
                                        new_platform_key = f"{platform} ({lang_key})"

                                        # Llamamos a la función de traducción
                                        translated_data = models.translate_post(
                                            content=content_to_translate,
                                            target_language=lang_name,
                                            asunto=original_asunto
                                        )

                                        # La respuesta del modelo es el contenido principal (HTML o texto plano)
                                        translated_main_content = translated_data["content"]
                                        translated_plain_text = ""
                                        translated_html_content = None  # Por defecto no hay HTML

                                        if is_html_platform:
                                            # Si es una plataforma HTML, el contenido principal es HTML
                                            translated_html_content = translated_main_content

                                            # Generar la versión de texto plano a partir del HTML traducido
                                            h = html2text.HTML2Text()
                                            h.ignore_links = False
                                            h.body_width = 0
                                            translated_plain_text = h.handle(translated_html_content)
                                        else:
                                            # Si no es una plataforma HTML, el contenido ya es texto plano
                                            translated_plain_text = translated_main_content

                                        # Añadimos la nueva publicación traducida a los resultados
                                        st.session_state.results[new_platform_key] = {
                                            "content": translated_plain_text,
                                            "asunto": translated_data.get("asunto", ""),
                                            "content_html": translated_html_content
                                        }

                                        # Preparamos el estado inicial para la nueva pestaña
                                        st.session_state[f"title_{new_platform_key}"] = f"{original_title} ({lang_key})"
                                        st.session_state[f"edited_content_{new_platform_key}"] = translated_plain_text
                                        if "asunto" in translated_data:
                                            st.session_state[f"edited_asunto_{new_platform_key}"] = translated_data["asunto"]

                                        # Inicializamos su historial de contenido
                                        if new_platform_key not in st.session_state.content_history:
                                            st.session_state.content_history[new_platform_key] = [translated_plain_text]

                                st.toast(f"¡{len(selected_languages)} traduccion(es) generada(s)!", icon="🌐")
                                time.sleep(1)
                                st.rerun()

                    # Programación
                    st.markdown("---")
                    st.markdown("#### ⏰ Programar o Guardar")
                    col1, col2 = st.columns(2)
                    with col1:
                        fecha_programada = st.date_input(
                            "Fecha de publicación",
                            value=datetime.now().date() + pd.Timedelta(days=1),
                            min_value=datetime.now().date(),
                            key=f"fecha_prog_{platform}"
                        )
                    with col2:
                        hora_programada = st.time_input(
                            "Hora de publicación, puedes escribir una hora específica",
                            value=datetime.now().time().replace(second=0, microsecond=0),
                            key=f"hora_prog_{platform}",
                            step=60*5
                        )
                    fecha_hora_programada = datetime.combine(fecha_programada, hora_programada)

                    # Botones de acción para guardar y programar
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Programar publicación", key=f"prog_btn_{platform}", width='stretch'):
                            try:
                                # VALIDACIONES
                                if title_already_exists(st.session_state[f"title_{platform}"]):
                                    st.warning(f"🚧 Ya existe una publicación con el título '{st.session_state[f'title_{platform}']}'")
                                elif platform.lower().startswith("instagram") and not st.session_state.get(f"selected_media_ids_{platform}"):
                                    st.warning("🚧 Para Instagram, debes adjuntar al menos un medio de la biblioteca.")
                                else:
                                    tiempo_minimo = datetime.now() + pd.Timedelta(minutes=1)
                                    if fecha_hora_programada <= tiempo_minimo:
                                        st.error("La fecha de programación debe ser al menos 1 minuto posterior a la hora actual")
                                    else:
                                        # Para Gmail, generar HTML con formato markdown + footer
                                        final_content_html = None
                                        if platform.lower().startswith("gmail"):
                                            current_text = st.session_state[f"edited_content_{platform}"]
                                            formatted_body = markdown_to_html(current_text)
                                            final_content_html = f"""
                                            <html>
                                            <body>
                                                <div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;">
                                                    {formatted_body}
                                                </div>
                                                {EMAIL_FOOTER}
                                            </body>
                                            </html>
                                            """
                                            
                                            # Añadir marcador de preferencia si se seleccionó incrustar imágenes
                                            if st.session_state.get(f"inline_pref_{platform}", False):
                                                final_content_html = "<!-- PREF:INLINE_IMAGES -->" + final_content_html
                                                
                                                # Añadir marcador de tamaño
                                                size_selection = st.session_state.get(f"img_size_pref_{platform}", "Grande (100%)")
                                                width_val = "100%"
                                                if "300px" in size_selection: width_val = "300px"
                                                elif "600px" in size_selection: width_val = "600px"
                                                
                                                final_content_html = f"<!-- PREF:IMG_SIZE:{width_val} -->" + final_content_html

                                        # Crear el post (solo texto) para obtener su ID
                                        post_id = create_post(
                                            title=st.session_state[f"title_{platform}"],
                                            content=st.session_state[f"edited_content_{platform}"],
                                            content_html=final_content_html,
                                            asunto=st.session_state.get(f"edited_asunto_{platform}") if platform.lower().startswith("gmail") else None,
                                            platform=platform,
                                            contacts=contactos_validos if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp") else [],
                                            fecha_hora=fecha_hora_programada.isoformat()
                                        )

                                        # Obtener IDs de los medios seleccionados
                                        media_ids_to_link = st.session_state.get(f"selected_media_ids_{platform}", [])

                                        # DEBUG: Mostrar info de medios
                                        import logging
                                        logger = logging.getLogger(__name__)
                                        logger.info(f"DEBUG Programar - Platform: {platform}")
                                        logger.info(f"DEBUG Programar - Media IDs: {media_ids_to_link}")
                                        logger.info(f"DEBUG Programar - Session state keys: {[k for k in st.session_state.keys() if 'selected_media' in k]}")

                                        # Enlazar medios al post
                                        if media_ids_to_link:
                                            link_media_to_post(post_id, media_ids_to_link)
                                            st.success(f"¡Publicación programada con {len(media_ids_to_link)} archivo(s) adjunto(s)!")
                                        else:
                                            st.success(f"¡Publicación programada! (Sin adjuntos)")
                                            if platform.lower().startswith("gmail"):
                                                st.info("💡 Consejo: Puedes adjuntar imágenes desde 'Adjuntar Medios de la Biblioteca' antes de programar.")

                            except Exception as e:
                                st.error(f"Error al programar la publicación: {str(e)}")

                    with col2:
                        if st.button("💾 Guardar sin programar", key=f"save_btn_{platform}", width='stretch'):
                            try:
                                if title_already_exists(st.session_state[f"title_{platform}"]):
                                    st.warning(f"🚧 Ya existe una publicación con el título '{st.session_state[f'title_{platform}']}'")
                                else:
                                    # Para Gmail, generar HTML con formato markdown + footer
                                    final_content_html = None
                                    if platform.lower().startswith("gmail"):
                                        current_text = st.session_state[f"edited_content_{platform}"]
                                        formatted_body = markdown_to_html(current_text)
                                        final_content_html = f"""
                                        <html>
                                        <body>
                                            <div style="font-family: Arial, sans-serif; font-size: 14px; line-height: 1.6;">
                                                {formatted_body}
                                            </div>
                                            {EMAIL_FOOTER}
                                        </body>
                                        </html>
                                        """

                                        # Añadir marcador de preferencia si se seleccionó incrustar imágenes
                                        if st.session_state.get(f"inline_pref_{platform}", False):
                                            final_content_html = "<!-- PREF:INLINE_IMAGES -->" + final_content_html

                                            # Añadir marcador de tamaño
                                            size_selection = st.session_state.get(f"img_size_pref_{platform}", "Grande (100%)")
                                            width_val = "100%"
                                            if "300px" in size_selection: width_val = "300px"
                                            elif "600px" in size_selection: width_val = "600px"
                                            
                                            final_content_html = f"<!-- PREF:IMG_SIZE:{width_val} -->" + final_content_html

                                    # Crear el post de texto para obtener su ID
                                    post_id = create_post(
                                        title=st.session_state[f"title_{platform}"],
                                        content=st.session_state[f"edited_content_{platform}"],
                                        content_html=final_content_html,
                                        asunto=st.session_state.get(f"edited_asunto_{platform}") if platform.lower().startswith("gmail") else None,
                                        platform=platform,
                                        contacts=contactos_validos if platform.lower().startswith("gmail") or platform.lower().startswith("whatsapp") else [],
                                        fecha_hora=None
                                    )
                                    # Obtener IDs de los medios seleccionados
                                    media_ids_to_link = st.session_state.get(f"selected_media_ids_{platform}", [])

                                    # DEBUG: Mostrar info de medios
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    logger.info(f"DEBUG Guardar - Platform: {platform}")
                                    logger.info(f"DEBUG Guardar - Media IDs: {media_ids_to_link}")
                                    logger.info(f"DEBUG Guardar - Session state keys: {[k for k in st.session_state.keys() if 'selected_media' in k]}")

                                    # Enlazar medios al post
                                    if media_ids_to_link:
                                        link_media_to_post(post_id, media_ids_to_link)
                                        st.success(f"¡Publicación guardada con {len(media_ids_to_link)} archivo(s) adjunto(s)!")
                                    else:
                                        st.success(f"¡Publicación guardada! (Sin adjuntos)")
                                        if platform.lower().startswith("gmail"):
                                            st.info("💡 Consejo: Puedes adjuntar imágenes desde 'Adjuntar Medios de la Biblioteca' antes de guardar.")
                            except Exception as e:
                                st.error(f"Error al guardar la publicación: {str(e)}")
    else:
        st.info("Completa el formulario y haz clic en '✨ Generar Contenido' para ver los resultados aquí.")
