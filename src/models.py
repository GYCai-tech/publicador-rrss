import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain.schema.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from . import prompts
from dotenv import load_dotenv
import openai

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('content_generator')

# Cargar variables de entorno
load_dotenv()
api_key = os.environ.get("OPENAI_API_KEY")
openai.api_key = api_key
logger.info("Variables de entorno cargadas")


class ContentRequest(BaseModel):
    objetivo: str = Field(..., description="Objetivo principal del contenido")
    audiencia: List[str] = Field(..., description="Perfiles de audiencia objetivo")
    mensaje: str = Field(..., description="Mensaje central del contenido")
    tono: str = Field(..., description="Tono deseado para el contenido")
    cta: str = Field(..., description="Llamada a la acción")
    keywords: List[str] = Field(..., description="Palabras clave principales")
    image_option: Optional[str] = Field(None, description="Opción de imagen seleccionada")


class Mail(BaseModel):
    asunto: str = Field(..., description="Asunto del correo electrónico")
    contenido: str = Field(..., description="Contenido del correo electrónico en texto plano")
    contenido_html: str = Field(..., description="Contenido del correo en formato HTML, usando etiquetas como <p>, <strong>, <em>, <br>, <ul> y <li> para darle formato.")


def generate_platform_content(platform: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Generando contenido para {platform} con datos: {request_data}")

    platform_config = {
        "LinkedIn": {
            "prompt_func": prompts.get_linkedin_prompt,
            "system_content": "Eres un experto en marketing digital especializado en LinkedIn."
        },
        "Instagram": {
            "prompt_func": prompts.get_instagram_prompt,
            "system_content": "Eres un experto en marketing digital especializado en Instagram."
        },
        "WordPress": {
            "prompt_func": prompts.get_wordpress_prompt,
            "system_content": "Eres un experto en marketing digital especializado en WordPress y SEO."
        },
        "Gmail": {
            "prompt_func": prompts.get_gmail_prompt,
            "system_content": "Eres un experto en marketing por email."
        },
        "WhatsApp": {
            "prompt_func": prompts.get_whatsapp_prompt,
            "system_content": "Eres un experto en marketing conversacional para WhatsApp."
        }
    }

    config = platform_config.get(platform)
    if not config:
        raise ValueError(f"Plataforma no soportada: {platform}")

    # Obtener información de la empresa
    empresa_info = prompts.get_GyC_info()

    # Crear un prompt enriquecido que incluya la información de la empresa
    prompt = f"""INFORMACIÓN DE CONTEXTO SOBRE LA EMPRESA:
        {empresa_info}
        
        DETALLES DE LA PUBLICACIÓN:
        {config["prompt_func"]().format(
            objetivo=request_data.get("objetivo", ""),
            audiencia=", ".join(request_data.get("audiencia", [])) if isinstance(request_data.get("audiencia"), list) else "",
            mensaje=request_data.get("mensaje", ""),
            tono=request_data.get("tono", ""),
            cta=request_data.get("cta", ""),
            keywords=", ".join(request_data.get("keywords", [])) if isinstance(request_data.get("keywords"), list) else ""
        )}"""

    try:
        logger.info(f"Realizando llamada a OpenAI para {platform}")

        if platform.lower().startswith("gmail"):
            llm = ChatOpenAI(
                model="gpt-5",
            ).with_structured_output(Mail)

            messages = [
                SystemMessage(content=config["system_content"]),
                HumanMessage(content=prompt)
            ]

            response = llm.invoke(messages)

            # Devolver un diccionario con todos los campos del modelo Mail
            return {
                "content": response.contenido,
                "asunto": response.asunto,
                "content_html": response.contenido_html,
                "metadata": {
                    "platform": platform,
                    "timestamp": datetime.now().isoformat(),
                    "prompt_used": prompt
                }
            }

        else:  # Resto de plataformas
            response = openai.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": config["system_content"]},
                    {"role": "user", "content": prompt}
                ]
            )

            content = response.choices[0].message.content
            logger.info(f"Respuesta recibida de OpenAI para {platform}")

            return {
                "content": content,
                "asunto": None,
                "content_html": None,
                "metadata": {
                    "platform": platform,
                    "timestamp": datetime.now().isoformat(),
                    "prompt_used": prompt
                }
            }

    except Exception as e:
        logger.error(f"Error al generar contenido para {platform}: {str(e)}")
        raise


def generate_content(platforms: List[str], common_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Iniciando generación de contenido para plataformas: {platforms}")

    results = {}
    for platform in platforms:
        try:
            response = generate_platform_content(platform, common_data)

            if platform.lower().startswith("wordpress"):
                # Comprueba si el contenido está envuelto en ```html ... ```
                if response['content'].strip().startswith("```html") and response['content'].strip().endswith("```"):
                    # Extrae solo el contenido HTML dentro de los marcadores
                    response['content'] = response['content'][response['content'].find("```html") + 7:response['content'].rfind("```")].strip()

            results[platform] = {
                "content": response["content"],
                "asunto": response.get("asunto"),
                "content_html": response.get("content_html"),
                "metadata": response["metadata"]
            }
        except Exception as e:
            logger.error(f"Error al generar contenido para {platform}: {str(e)}")
            results[platform] = {
                "content": f"Error: {str(e)}",
                "metadata": {
                    "platform": platform,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
            }

    return results


def regenerate_post(platform: str, content: str, prompt: str, asunto: Optional[str] = None) -> Dict[str, Any]:
    """
    Regenera contenido para plataformas específicas basándose en instrucciones.
    Para Gmail, regenera la estructura completa (asunto, contenido, content_html).
    """
    logger.info(f"Regenerando contenido para {platform}")

    # Lógica específica para regenerar un correo de Gmail
    if platform.lower().startswith("gmail"):
        try:
            # Prompt específico para regenerar correos de Gmail
            regeneration_prompt = prompts.get_gmail_regeneration_prompt().format(
                original_asunto=asunto,
                original_content=content,
                feedback=prompt,
                cta="Comprar ahora"
            )

            # Llamada para que devuelva una estructura Mail
            llm = ChatOpenAI(model="gpt-5").with_structured_output(Mail)

            messages = [
                SystemMessage(content="Eres un experto en email marketing que modifica correos existentes."),
                HumanMessage(content=regeneration_prompt)
            ]

            response = llm.invoke(messages)
            logger.info("Contenido de Gmail regenerado exitosamente.")

            # Devolver un diccionario completo con todos los campos del correo
            return {
                "content": response.contenido,
                "asunto": response.asunto,
                "content_html": response.contenido_html,
                "metadata": {
                    "platform": platform,
                    "timestamp": datetime.now().isoformat(),
                    "prompt_used": regeneration_prompt,
                    "is_regeneration": True
                }
            }
        except Exception as e:
            logger.error(f"Error al regenerar contenido de Gmail: {str(e)}")
            raise

    # Lógica para el resto de plataformas
    else:
        system_prompts = {
            "LinkedIn": "Eres un experto en marketing digital especializado en LinkedIn.",
            "Instagram": "Eres un experto en marketing digital especializado en Instagram.",
            "WordPress": "Eres un experto en marketing digital especializado en WordPress y SEO.",
            "WhatsApp": "Eres un experto en marketing conversacional para WhatsApp."
        }
        try:
            # Usar el prompt de regeneración genérico
            regeneration_prompt = prompts.get_regeneration_prompt().format(
                platform=platform,
                original_content=content,
                feedback=prompt
            )

            response = openai.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system",
                     "content": system_prompts.get(platform, "Eres un experto en marketing digital.")},
                    {"role": "user", "content": regeneration_prompt}
                ]
            )

            new_content = response.choices[0].message.content
            logger.info(f"Contenido regenerado exitosamente para {platform}")

            return {
                "content": new_content,
                "metadata": {
                    "platform": platform,
                    "timestamp": datetime.now().isoformat(),
                    "prompt_used": regeneration_prompt,
                    "is_regeneration": True
                }
            }
        except Exception as e:
            logger.error(f"Error al regenerar contenido para {platform}: {str(e)}")
            raise


def translate_post(content: str, target_language: str, asunto: str = None) -> dict:
    """
    Traduce el contenido de una publicación y, opcionalmente, su asunto.
    Devuelve un diccionario con el contenido y asunto traducidos.
    """
    translated_data = {}

    # 1. Traducir el contenido principal
    prompt_content = prompts.get_translation_prompt().format(
        target_language=target_language,
        original_text=content
    )
    # Usamos una función de llamada a la API que no espere JSON
    try:
        response_content = openai.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt_content}],
        )
        translated_content = response_content.choices[0].message.content.strip()

        # A veces el modelo envuelve el texto en comillas, las quitamos.
        if translated_content.startswith('"') and translated_content.endswith('"'):
            translated_content = translated_content[1:-1]

        translated_data["content"] = translated_content

    except Exception as e:
        logger.error(f"Error al traducir el contenido: {e}")
        translated_data["content"] = f"Error de traducción: {content}"

    # 2. Si hay un asunto, traducirlo también
    if asunto:
        prompt_asunto = prompts.get_translation_prompt().format(
            target_language=target_language,
            original_text=asunto
        )
        try:
            response_asunto = openai.chat.completions.create(
                model="gpt-5",
                messages=[{"role": "user", "content": prompt_asunto}],
            )
            translated_asunto = response_asunto.choices[0].message.content.strip()

            if translated_asunto.startswith('"') and translated_asunto.endswith('"'):
                translated_asunto = translated_asunto[1:-1]

            translated_data["asunto"] = translated_asunto

        except Exception as e:
            logger.error(f"Error al traducir el asunto: {e}")
            translated_data["asunto"] = f"Error: {asunto}"

    return translated_data


if __name__ == "__main__":
    request_data = {
        "objetivo": "Aumentar la visibilidad de la marca",
        "audiencia": ["Agricultores", "Productores agropecuarios"],
        "mensaje": "Presentamos nuestra nueva línea de fertilizantes orgánicos",
        "tono": "Profesional y amigable",
        "cta": "Descubre más en nuestro sitio web",
        "keywords": ["fertilizantes", "orgánicos", "agricultura sostenible"]
    }

    platforms = ["Gmail"]
    content = generate_content(platforms, request_data)
    print(content)
