import streamlit as st
from datetime import datetime
import pandas as pd

from src.db_config import get_programmed_posts, get_unprogrammed_posts, get_programmed_posts_by_platform, get_unprogrammed_posts_by_platform
from src.ui_components import display_posts, display_post_editor
from src.state import init_states

init_states()
st.set_page_config(layout="wide")

if st.session_state.get('force_page_rerun', False):
    st.session_state.force_page_rerun = False

    get_programmed_posts.clear()
    get_unprogrammed_posts.clear()

    st.rerun()

st.title("📝 Gestión de Publicaciones")
st.markdown("Edita, programa o elimina las publicaciones que has creado.")

# Estado inicial
if 'selected_pub_id' not in st.session_state:
    st.session_state.selected_pub_id = None

# Crear estructura de dos columnas
col_left, empty_col, col_right = st.columns([5, 0.1, 5])

# Columna izquierda: listado de publicaciones
with col_left:
    # Tabs principales
    tab_scheduled, tab_saved = st.tabs(["📅 Programadas", "💾 Guardadas"])

    # Tab de publicaciones programadas
    with tab_scheduled:
        programmed_posts = get_programmed_posts()

        if not programmed_posts:
            st.info("No hay publicaciones programadas. Programa alguna publicación desde la sección 'Publicaciones Guardadas'.")
        else:

            # Buscador por título
            titles = [post['title'] for post in programmed_posts if post['title']]
            selected_title = st.selectbox(
                "🔍 Buscar publicación por título",
                options=[""] + titles,
                key="title_filter_scheduled"
            )

            # Filtrar por título si se seleccionó uno
            if selected_title:
                programmed_posts = [post for post in programmed_posts if post['title'] == selected_title]

            # Contenedor de filtros con estilo
            with st.container():
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    usar_filtro_fecha = st.checkbox("Filtrar por fechas", value=False,
                                                  key="usar_filtro_fecha_scheduled")

                with col2:
                    date_range = st.date_input(
                        "Rango de fechas",
                        value=(datetime.now().date(), datetime.now().date() + pd.Timedelta(days=30)),
                        min_value=datetime.now().date() - pd.Timedelta(days=1),
                        max_value=datetime.now().date() + pd.Timedelta(days=90),
                        key="date_range_scheduled",
                        disabled=not usar_filtro_fecha
                    )

                with col3:
                    platform_filter = st.multiselect(
                        "Filtrar por plataforma",
                        options=["LinkedIn", "Instagram", "WordPress", "Gmail", "WhatsApp"],
                        default=[],
                        key="platform_filter_scheduled"
                    )
                with col4:
                    sort_by = st.selectbox(
                        "Ordenar por",
                        options=["Fecha (ascendente)", "Fecha (descendente)", "Plataforma"],
                        key="sort_by_scheduled"
                    )

            # Filtrar según plataforma
            if platform_filter:
                filtered_posts = []
                for platform in platform_filter:
                    filtered_posts.extend(get_programmed_posts_by_platform(platform))
            else:
                filtered_posts = programmed_posts

            # Mostrar publicaciones
            display_posts(filtered_posts, date_range, sort_by, 'scheduled', usar_filtro_fecha)

    # Tab de publicaciones guardadas
    with tab_saved:
        unprogrammed_posts = get_unprogrammed_posts()

        if not unprogrammed_posts:
            st.info("No hay publicaciones guardadas. Crea publicaciones desde la página principal.")
        else:
            # Buscador por título
            titles = [post['title'] for post in unprogrammed_posts if post['title']]
            selected_title = st.selectbox(
                "🔍 Buscar publicación por título",
                options=[""] + titles,
                key="title_filter_saved"
            )

            # Filtrar por título si se seleccionó uno
            if selected_title:
                unprogrammed_posts = [post for post in unprogrammed_posts if post['title'] == selected_title]

            # Contenedor de filtros con estilo
            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    platform_filter = st.multiselect(
                        "Filtrar por plataforma",
                        options=["LinkedIn", "Instagram", "WordPress", "Gmail", "WhatsApp"],
                        default=[],
                        key="platform_filter_saved"
                    )
                with col2:
                    sort_by = st.selectbox(
                        "Ordenar por",
                        options=["Fecha de creación (reciente primero)", "Fecha de creación (antiguo primero)", "Plataforma"],
                        key="sort_by_saved"
                    )

            # Filtrar según plataforma
            if platform_filter:
                filtered_posts = []
                for platform in platform_filter:
                    filtered_posts.extend(get_unprogrammed_posts_by_platform(platform))
            else:
                filtered_posts = unprogrammed_posts

            # Mostrar publicaciones
            display_posts(filtered_posts, None, sort_by, 'saved')

with empty_col:
    st.markdown("""
        <div style="border-left: 2px solid #e6e6e6; height: 140vh; margin: 0 auto;"></div>
    """, unsafe_allow_html=True)

# Columna derecha: editor de publicación
with col_right:
    st.markdown("""
    <div style="border-left: 2px solid #e6e6e6; height: 100%; position: absolute; left: 0; top: 0;"></div>
    """, unsafe_allow_html=True)

    if st.session_state.selected_pub_id is not None:
        display_post_editor(st.session_state.selected_pub_id)
    else:
        st.markdown("""
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 70vh; color: #888;">
            <div style="font-size: 60px; margin-bottom: 20px;">👈</div>
            <h3>Selecciona una publicación para editar</h3>
            <p>Haz clic en una publicación de la lista para comenzar a editarla</p>
        </div>
        """, unsafe_allow_html=True)
