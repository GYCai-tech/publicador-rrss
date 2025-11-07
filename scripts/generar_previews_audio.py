import os
from termcolor import colored
from src.openai_video_generator import configurar_openai, generar_tts_con_openai, VOICES


def main():
    """
    Genera un fichero de audio de previsualización para cada voz disponible de OpenAI.
    """
    print(colored("Configurando cliente de OpenAI...", "blue"))
    if not configurar_openai():
        exit()

    output_dir = "audio_previews"
    os.makedirs(output_dir, exist_ok=True)
    print(colored(f"Directorio de salida: '{output_dir}'", "blue"))

    texto_preview = "Esta es una prueba de mi voz para la generación de vídeo."

    for voz in VOICES:
        print(colored(f"\nGenerando preview para la voz: {voz}", "yellow"))

        output_path = os.path.join(output_dir, f"{voz}.mp3")

        success = generar_tts_con_openai(
            texto_a_voz=texto_preview,
            ruta_guardado=output_path,
            voz=voz,
            usar_prompt_complejo=False
        )

        if not success:
            print(colored(f"Fallo al generar la preview para la voz {voz}", "red"))

    print(colored("\nProceso de generación de previews completado.", "green"))


if __name__ == "__main__":
    main()
