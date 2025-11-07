import logging
from src.instagram import get_instagram_client
import os

# Logger básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def iniciar_sesion_instagram():
    """
    Inicia sesión en Instagram de forma interactiva para guardar
    un archivo de sesión válido.
    """
    print("Iniciando el proceso para establecer la sesión de Instagram...")
    print("     Este script podría pedirte un código de verificación.")
    print("     Revisa tu email y escríbelo en la terminal cuando se te pida.")
    print("-" * 50)
    os.makedirs("sessions", exist_ok=True)  # Crea la carpeta 'sessions' si no existe.
    try:
        client = get_instagram_client()

        if client and client.user_id:
            print("-" * 50)
            print(f"✅ ¡Éxito! Sesión guardada con éxito para el usuario {client.user_id}.")
            print(f"   El archivo 'sessions/ig_session.json' ha sido creado/actualizado.")
        else:
            print("❌ Fallo al iniciar sesión. Revisa las credenciales o el código de verificación.")

    except Exception as e:
        print(f"❌ Ocurrió un error: {e}")


if __name__ == "__main__":
    iniciar_sesion_instagram()
