import streamlit as st
import importlib

from src import prompts
from src.utils import update_prompt_function
from src.state import init_states

init_states()

st.set_page_config(layout="wide")

st.title("⚙️ Configuración de Prompts")
st.markdown("Personaliza las instrucciones que la IA utiliza para generar el contenido.")

PROMPTS_FILE_PATH = 'src/prompts.py'

# Inicialización de estados para todos los prompts
if "main_prompt_content" not in st.session_state:
    st.session_state.main_prompt_content = prompts.get_main_prompt()
if "company_info_content" not in st.session_state:
    st.session_state.company_info_content = prompts.get_GyC_info()
if "linkedin_prompt_content" not in st.session_state:
    st.session_state.linkedin_prompt_content = prompts.get_linkedin_prompt()
if "instagram_prompt_content" not in st.session_state:
    st.session_state.instagram_prompt_content = prompts.get_instagram_prompt()
if "whatsapp_prompt_content" not in st.session_state:
    st.session_state.whatsapp_prompt_content = prompts.get_whatsapp_prompt()
if "wordpress_prompt_content" not in st.session_state:
    st.session_state.wordpress_prompt_content = prompts.get_wordpress_prompt()
if "gmail_prompt_content" not in st.session_state:
    st.session_state.gmail_prompt_content = prompts.get_gmail_prompt()
if "video_script_prompt_content" not in st.session_state:
    st.session_state.video_script_prompt_content = prompts.get_video_script_prompt()

col_general, col_redes = st.columns(2)

with col_general:
    st.subheader("📝 Configuración General")
    tab_principal, tab_empresa = st.tabs([
        "Prompt Principal",
        "Información Empresa"
    ])

    with tab_principal:
        st.image('assets/logos/logo.png', width=270)
        main_prompt = st.text_area(
            "Editar prompt principal",
            value=st.session_state.main_prompt_content,
            height=500,
            key="main_prompt_editor"
        )

        if st.button("Guardar Prompt Principal"):
            try:
                success = update_prompt_function('get_main_prompt', main_prompt, file_path=PROMPTS_FILE_PATH)
                if success:
                    # Recargar el módulo manteniendo la referencia
                    try:
                        importlib.reload(prompts)
                    except Exception as e:
                        pass
                    # Actualizar el estado con el contenido actualizado
                    st.session_state.main_prompt_content = prompts.get_main_prompt()
                    st.success("Prompt principal guardado exitosamente")
                else:
                    st.error("Error al guardar el prompt principal")
            except Exception as e:
                st.error(f"Error inesperado: {str(e)}")

    with tab_empresa:
        st.image('assets/logos/logo.png', width=270)
        company_info = st.text_area(
            "Editar información de la empresa",
            value=st.session_state.company_info_content,
            height=500
        )
        if st.button("Guardar Información Empresa"):
            try:
                success = update_prompt_function('get_GyC_info', company_info, file_path=PROMPTS_FILE_PATH)
                if success:
                    try:
                        importlib.reload(prompts)
                    except Exception as e:
                        pass
                    st.session_state.company_info_content = prompts.get_GyC_info()
                    st.success("Información de la empresa guardada exitosamente")
                else:
                    st.error("Error al guardar la información de la empresa")
            except Exception as e:
                st.error(f"Error al actualizar: {str(e)}")

with col_redes:
    st.subheader("🌐 Configuración de Redes Sociales")
    tab_linkedin, tab_instagram, tab_whatsapp, tab_wordpress, tab_gmail, tab_video = st.tabs([
        "LinkedIn", "Instagram", "WhatsApp", "WordPress", "Gmail", "Vídeo"
    ])

    with tab_linkedin:
        st.image('assets/logos/linkedin.png', width=70)
        linkedin_prompt = st.text_area(
            "Editar prompt LinkedIn",
            value=st.session_state.linkedin_prompt_content,
            height=500
        )
        if st.button("Guardar Prompt LinkedIn"):
            try:
                success = update_prompt_function('get_linkedin_prompt', linkedin_prompt, file_path=PROMPTS_FILE_PATH)
                if success:
                    try:
                        importlib.reload(prompts)
                    except Exception as e:
                        pass
                    st.session_state.linkedin_prompt_content = prompts.get_linkedin_prompt()
                    st.success("Prompt de LinkedIn guardado exitosamente")
                else:
                    st.error("Error al guardar el prompt de LinkedIn")
            except Exception as e:
                st.error(f"Error al actualizar: {str(e)}")

    with tab_instagram:
        st.image('assets/logos/instagram.png', width=70)
        instagram_prompt = st.text_area(
            "Editar prompt Instagram",
            value=st.session_state.instagram_prompt_content,
            height=500
        )
        if st.button("Guardar Prompt Instagram"):
            try:
                success = update_prompt_function('get_instagram_prompt', instagram_prompt, file_path=PROMPTS_FILE_PATH)
                if success:
                    try:
                        importlib.reload(prompts)
                    except Exception as e:
                        pass
                    st.session_state.instagram_prompt_content = prompts.get_instagram_prompt()
                    st.success("Prompt de Instagram guardado exitosamente")
                else:
                    st.error("Error al guardar el prompt de Instagram")
            except Exception as e:
                st.error(f"Error al actualizar: {str(e)}")

    with tab_whatsapp:
        st.image('assets/logos/whatsapp.png', width=70)
        whatsapp_prompt = st.text_area(
            "Editar prompt WhatsApp",
            value=st.session_state.whatsapp_prompt_content,
            height=500
        )
        if st.button("Guardar Prompt WhatsApp"):
            try:
                success = update_prompt_function('get_whatsapp_prompt', whatsapp_prompt, file_path=PROMPTS_FILE_PATH)
                if success:
                    try:
                        importlib.reload(prompts)
                    except Exception as e:
                        pass
                    st.session_state.whatsapp_prompt_content = prompts.get_whatsapp_prompt()
                    st.success("Prompt de WhatsApp guardado exitosamente")
                else:
                    st.error("Error al guardar el prompt de WhatsApp")
            except Exception as e:
                st.error(f"Error al actualizar: {str(e)}")

    with tab_wordpress:
        st.image('assets/logos/wordpress.png', width=70)
        wordpress_prompt = st.text_area(
            "Editar prompt WordPress",
            value=st.session_state.wordpress_prompt_content,
            height=500
        )
        if st.button("Guardar Prompt WordPress"):
            try:
                success = update_prompt_function('get_wordpress_prompt', wordpress_prompt, file_path=PROMPTS_FILE_PATH)
                if success:
                    try:
                        importlib.reload(prompts)
                    except Exception as e:
                        pass
                    st.session_state.wordpress_prompt_content = prompts.get_wordpress_prompt()
                    st.success("Prompt de WordPress guardado exitosamente")
                else:
                    st.error("Error al guardar el prompt de WordPress")
            except Exception as e:
                st.error(f"Error al actualizar: {str(e)}")

    with tab_gmail:
        st.image('assets/logos/gmail.png', width=70)
        gmail_prompt = st.text_area(
            "Editar prompt Gmail",
            value=st.session_state.gmail_prompt_content,
            height=500
        )
        if st.button("Guardar Prompt Gmail"):
            try:
                success = update_prompt_function('get_gmail_prompt', gmail_prompt, file_path=PROMPTS_FILE_PATH)
                if success:
                    try:
                        importlib.reload(prompts)
                    except Exception as e:
                        pass
                    st.session_state.gmail_prompt_content = prompts.get_gmail_prompt()
                    st.success("Prompt de Gmail guardado exitosamente")
                else:
                    st.error("Error al guardar el prompt de Gmail")
            except Exception as e:
                st.error(f"Error al actualizar: {str(e)}")

    with tab_video:
        st.markdown("##### 📹 Prompt para Guion de Vídeo")
        video_prompt = st.text_area(
            "Editar prompt para Guion de Vídeo",
            value=st.session_state.video_script_prompt_content,
            height=500,
            key="video_script_editor"
        )
        if st.button("Guardar Prompt de Vídeo"):
            try:
                success = update_prompt_function('get_video_script_prompt', video_prompt, file_path=PROMPTS_FILE_PATH)
                if success:
                    importlib.reload(prompts)  # Recargar el módulo
                    st.session_state.video_script_prompt_content = prompts.get_video_script_prompt()
                    st.success("Prompt de Vídeo guardado exitosamente")
                else:
                    st.error("Error al guardar el prompt de Vídeo")
            except Exception as e:
                st.error(f"Error al actualizar: {str(e)}")
