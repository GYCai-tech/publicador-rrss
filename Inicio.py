import streamlit as st
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from src.state import init_states
from src.utils import check_env_vars

st.set_page_config(
    page_title="Generador IA de Contenido",
    page_icon="🤖",
    layout="wide"
)

# Validar variables de entorno
try:
    if 'env_vars_checked' not in st.session_state:
        check_env_vars()
        st.session_state.env_vars_checked = True
except SystemExit as e:
    st.error(str(e))
    st.stop()

# Inicializar estados de sesión
init_states()

# Página de bienvenida. Streamlit creará la barra lateral automáticamente a partir de los ficheros en la carpeta /pages.
st.title("Bienvenid@ al Generador de Contenido con IA")
st.markdown("---")
st.image('assets/logos/logo.png', width=400)
st.header("Usa el menú de la izquierda para navegar entre las secciones.")
st.info(
    """
    - **Generación**: Crea nuevo contenido de texto, vídeo o sube medios.
    - **Publicaciones**: Edita y gestiona tus publicaciones guardadas.
    - **Calendario**: Visualiza y organiza tus posts programados.
    - **Configuración**: Personaliza los prompts de la IA.
    """
)
