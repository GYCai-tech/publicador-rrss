import os
from openai import OpenAI
from dotenv import load_dotenv
from termcolor import colored
from . import prompts

# Lista de voces disponibles en OpenAI TTS
VOICES = ['alloy', 'ash', 'ballad', 'coral', 'echo', 'fable', 'nova', 'onyx', 'sage', 'shimmer']

# Variable global para el cliente de la API
client = None


def configurar_openai():
    """Configura el cliente de la API de OpenAI."""
    global client
    # Carga las variables de entorno desde el fichero .env
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(colored("Error: La variable de entorno OPENAI_API_KEY no está configurada.", "red"))
        return False
    try:
        client = OpenAI(api_key=api_key)
        print(colored("Cliente de OpenAI configurado con éxito.", "green"))
        return True
    except Exception as e:
        print(colored(f"Error al configurar el cliente de OpenAI: {e}", "red"))
        return False


def generar_guion_con_openai(tema: str, info_empresa: str, idioma: str = "español") -> str:
    """Genera un guion usando un modelo de chat de OpenAI."""
    if not client:
        print(colored("Error: El cliente de OpenAI no está configurado.", "red"))
        return None

    print(colored(f"[+] Generando guion con OpenAI para el tema: '{tema}'...", "blue"))
    try:
        model_name = 'gpt-5'
        prompt_template = prompts.get_video_script_prompt()
        prompt_final = prompt_template.format(tema=tema, info_empresa=info_empresa, idioma=idioma)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt_final}
            ]
        )

        guion = response.choices[0].message.content.strip().replace('"', '')
        print(colored(f"[+] Guion generado:\n--- {guion} ---", "cyan"))
        return guion

    except Exception as e:
        print(colored(f"Error en generación de texto con OpenAI: {e}", "red"))
        return None


def generar_tts_con_openai(texto_a_voz: str, ruta_guardado: str, voz: str = "nova", usar_prompt_complejo: bool = True, modelo: str = "gpt-4o-mini-tts") -> bool:
    """Genera audio a partir de texto usando la API de OpenAI."""
    if not client:
        print(colored("Error: El cliente de OpenAI no está configurado.", "red"))
        return False

    print(colored(f"[+] Generando audio con el modelo '{modelo}' y la voz '{voz}'...", "blue"))

    try:
        if usar_prompt_complejo:
            print(colored("  [INFO] Usando prompt complejo para locución de anuncio.", "yellow"))
            instrucciones = f"""
                Eres un experto en locución de anuncios para redes sociales. Tu tarea es generar la locución de un anuncio que sea atractivo, 
                conciso y con un llamado a la acción, utilizando un acento español (de España). Lee el siguiente texto con tono firme y familiar
            """
        else:
            print(colored("  [INFO] Usando texto literal para preview de voz.", "yellow"))
            instrucciones = f"Lee el siguiente texto con acento español de España"

        with client.audio.speech.with_streaming_response.create(
                model=modelo,
                voice=voz,
                input=texto_a_voz,
                instructions=instrucciones,
                response_format="mp3"
        ) as response:
            response.stream_to_file(ruta_guardado)

        print(colored(f"[+] Audio guardado correctamente en: {ruta_guardado}", "green"))
        return True
    except Exception as e:
        print(colored(f"Error en la generación de TTS con OpenAI: {e}", "red"))
        return False
