import os
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_gemini():
    """
    Script simple para probar la conexión con la API de Google Gemini.
    Requiere que la variable GOOGLE_API_KEY esté definida en el archivo .env
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ Error: La variable 'GOOGLE_API_KEY' no fue encontrada en el archivo .env")
        print("Por favor, añade tu API Key en el archivo .env así:")
        print("GOOGLE_API_KEY=tu_api_key_aqui")
        return

    try:
        print("🔄 Configurando cliente de Gemini...")
        genai.configure(api_key=api_key)
        
        # Seleccionar el modelo (gemini-1.5-flash es rápido y eficiente, o gemini-pro)
        model_name = 'gemini-1.5-flash'
        print(f"🤖 Usando modelo: {model_name}")
        model = genai.GenerativeModel(model_name)

        # Prompt de prueba
        prompt = "Escribe una frase motivadora corta para un programador Python."
        print(f"📤 Enviando prompt: '{prompt}'")
        
        # Generar contenido
        response = model.generate_content(prompt)
        
        print("\n✅ Respuesta recibida de Gemini:")
        print("-" * 40)
        print(response.text)
        print("-" * 40)
        
    except Exception as e:
        print(f"\n❌ Error al conectar con la API de Gemini: {e}")

if __name__ == "__main__":
    test_gemini()
