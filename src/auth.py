import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

def login_form():
    """Muestra un formulario de inicio de sesión y oculta la navegación."""
    st.markdown("""
        <style>
        /* Ocultar barra lateral y cabecera cuando no está autenticado */
        [data-testid="stSidebar"] {
            display: none;
        }
        [data-testid="stHeader"] {
            display: none;
        }
        #MainMenu {
            display: none;
        }
        footer {
            display: none;
        }
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 30px;
            background-color: var(--background-color);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border: 1px solid var(--border-color);
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.title("🔐 Acceso al Sistema")
        
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")

        
        if st.button("Iniciar Sesión", use_container_width=True):
            correct_username = os.getenv("APP_USERNAME", "admin")
            correct_password = os.getenv("APP_PASSWORD")
            
            if not correct_password:
                st.error("⚠️ Configuración de seguridad incompleta. Falta APP_PASSWORD en el archivo .env")
                return
            
            if username == correct_username and password == correct_password:
                st.session_state.authenticated = True
                st.success("Acceso concedido")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

def check_password():
    """
    Devuelve True si el usuario está autenticado, de lo contrario muestra el formulario de login y devuelve False.
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        login_form()
        return False
    
    return True
