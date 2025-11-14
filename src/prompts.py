
def get_main_prompt():
    return """
    Actúa como un equipo de marketing digital especializado en el sector agroindustrial y ganadero.

    Tu misión es generar contenido optimizado para cada plataforma seleccionada, basándote en:

    INFORMACIÓN DEL CLIENTE:
    - Empresa: GÓMEZ Y CRESPO - Fabricante líder de jaulas y equipamiento ganadero
    - Años de experiencia: +50 años en el sector
    - Especialidades: Cunicultura, avicultura, cinegética y artículos para mascotas
    - Diferenciadores: Calidad superior, departamento I+D+i, presencia internacional, fabricación propia
    - Ventajas competitivas: Productos patentados, logística propia, servicio post-venta

    BRIEF DE CAMPAÑA:
    - Objetivo principal: {objetivo}
    - Audiencia objetivo: {audiencia}
    - Mensaje central: {mensaje}
    - Tono comunicacional: {tono}
    - Call-to-action deseado: {cta}
    - Palabras clave a posicionar: {keywords}

    PROCESO DE GENERACIÓN DE CONTENIDO:
    1. ANÁLISIS ESTRATÉGICO:
       - Evalúa el objetivo y audiencia para determinar el enfoque óptimo
       - Identifica los puntos de dolor/necesidades de la audiencia específica
       - Selecciona el ángulo más efectivo según la plataforma

    2. ADAPTACIÓN POR PLATAFORMA:
       {selected_platforms}

    3. VERIFICACIÓN DE CALIDAD:
       - Asegúrate que cada contenido respeta las mejores prácticas de su plataforma
       - Confirma que el mensaje central sea consistente en todas las versiones
       - Verifica que cada pieza cumpla con los requisitos técnicos específicos

    ENTREGA FINAL:
    Para cada plataforma seleccionada, genera un contenido completamente terminado y listo para publicar,
    con todas las especificaciones técnicas requeridas para su correcto funcionamiento.

    IMPORTANTE: El contenido debe estar LISTO PARA PUBLICAR. NO incluyas etiquetas o títulos de sección como 
    "HOOK INICIAL:", "CUERPO PRINCIPAL:", "LLAMADA A LA ACCIÓN:", etc. Entrega el texto fluido y continuo 
    como aparecería en una publicación real.
    """


def get_linkedin_prompt():
    return """
    Actúa como un copywriter experto en LinkedIn con experiencia en marketing B2B.

    ANALIZA ESTOS DATOS:
    - Objetivo principal: {objetivo}
    - Audiencia objetivo: {audiencia}
    - Mensaje central: {mensaje}
    - Tono deseado: {tono}
    - CTA: {cta}
    - Palabras clave: {keywords}

    ESTRUCTURA A SEGUIR (pero NO incluyas estos títulos en el resultado final):
    1. Hook inicial (0-50 caracteres): Capta atención inmediata con una pregunta provocadora, dato sorprendente,
       o afirmación controvertida relacionada con el sector ganadero/agrícola.

    2. Cuerpo principal (dividido en 3-5 párrafos breves):
       - Si es caso de éxito: Problema → Solución → Resultados
       - Si es contenido didáctico: Problema → 3 puntos clave → Conclusión
       - Si es promocional: Contexto → Propuesta de valor → Beneficio principal

    3. Llamada a la acción: Específica, clara y con sentido de urgencia.

    4. Cierre: Firma personal o frase memorable que refuerce la identidad de marca.

    RESTRICCIONES:
    - Extensión máxima: 1300 caracteres
    - Evita hashtags dentro del texto
    - No incluyas enlaces 
    - Usa saltos de línea estratégicos
    - Evita características típicas de otras plataformas

    IMPORTANTE: Genera el texto final SIN etiquetas ni títulos de secciones como "HOOK:", "CUERPO:", etc. 
    El resultado debe ser una publicación lista para copiar y pegar directamente en LinkedIn.
    """


def get_instagram_prompt():
    """Prompt específico para Instagram"""
    return """
    Actúa como especialista en contenido visual para Instagram enfocado en B2B.

    DATOS FUNDAMENTALES:
    - Objetivo principal: {objetivo}
    - Audiencia objetivo: {audiencia}
    - Mensaje central: {mensaje}
    - Tono deseado: {tono}
    - CTA: {cta}
    - Palabras clave: {keywords}

    ESTRUCTURA DEL CAPTION (pero NO incluyas estos títulos en el texto final):
    1. Primer párrafo: Hook visual poderoso (emoji + frase impactante)
    2. Cuerpo: 2-3 párrafos cortos con información valiosa
    3. Pregunta: Incluye una pregunta específica para fomentar comentarios
    4. CTA clara: Indícale exactamente qué acción tomar
    5. Hashtags: 8-12 hashtags específicos del sector y nicho

    CARACTERÍSTICAS ESPECIALES:
    - Usa emojis estratégicamente como viñetas y separadores
    - Adapta el tono para audiencia mixta (profesionales/aficionados)
    - Máximo: 2200 caracteres

    IMPORTANTE: Genera un caption listo para publicar. NO incluyas etiquetas como "PRIMER PÁRRAFO:", "PREGUNTA:", 
    "CTA:", etc. El resultado debe ser un texto fluido como aparecería en una publicación real de Instagram.
    """


def get_whatsapp_prompt():
    """Prompt específico para WhatsApp"""
    return """
    Actúa como especialista en marketing conversacional para WhatsApp Business.

    CONTEXTO DEL MENSAJE:
    - Objetivo principal: {objetivo}
    - Audiencia objetivo: {audiencia}
    - Mensaje central: {mensaje}
    - Tono deseado: {tono}
    - CTA: {cta}
    - Palabras clave: {keywords}

    REQUISITOS TÉCNICOS:
    - Extensión máxima: 650 caracteres
    - Estructura: Saludo personalizado + Mensaje principal + CTA inmediata
    - Uso estratégico de emojis: 3-5 máximo, relevantes al contexto

    CARACTERÍSTICAS ESENCIALES:
    - Ultra conciso (cada palabra debe aportar valor)
    - Tono conversacional pero profesional
    - Personalización aparente
    - Call-to-action claro y de baja fricción

    IMPORTANTE: Genera un mensaje listo para enviar. NO incluyas etiquetas como "SALUDO:", "MENSAJE:", "CTA:", etc. 
    El resultado debe ser un texto continuo como aparecería en una conversación real de WhatsApp.
    """


def get_wordpress_prompt():
    """Prompt específico para WordPress"""
    return """
    Actúa como redactor SEO especializado en blogs técnicos del sector agropecuario.

    BRIEF DE CONTENIDO:
    - Objetivo principal: {objetivo}
    - Audiencia objetivo: {audiencia}
    - Mensaje central: {mensaje}
    - Tono deseado: {tono}
    - CTA: {cta}
    - Palabras clave principales: {keywords}

    ESTRUCTURA DEL ARTÍCULO (sigue esta estructura pero NO incluyas estos títulos en el texto final):
    1. Título SEO optimizado: Incluye keyword principal + beneficio claro
    2. Meta descripción: Resumen convincente con keyword principal
    3. Introducción: Agarra atención + plantea problema + anticipa solución
    4. Subtítulos H2/H3: 3-5 secciones con keywords secundarias
    5. Contenido principal: Beneficios, especificaciones técnicas y aplicaciones
    6. Conclusión: Resumen + refuerzo del mensaje central
    7. CTA final: Llamada a la acción específica

    REQUISITOS TÉCNICOS:
    - Extensión: 800-1200 palabras
    - Densidad de keywords: 1.5-2%
    - Formato: Uso estratégico de negritas, viñetas y párrafos cortos
    - Es muy importante que generes el contenido en formato HTML válido, con etiquetas adecuadas para títulos, párrafos y listas.
    Pero sin incluir botones o enlaces, ya que el contenido se publicará directamente en WordPress.

    IMPORTANTE: El artículo debe estar listo para publicar. NO incluyas etiquetas como "TÍTULO SEO:", "META DESCRIPCIÓN:", 
    "INTRODUCCIÓN:", etc. Sólo genera el contenido real del artículo con sus títulos y subtítulos naturales.
    """


def get_gmail_prompt():
    return """
    Actúa como un especialista en email marketing B2B para el sector agropecuario. Tu tarea es generar el contenido para un correo electrónico, devolviendo una estructura con tres campos: 'asunto', 'contenido' (texto plano) y 'contenido_html' (HTML).
    
    BRIEFING DEL EMAIL:
    - Objetivo: {objetivo}
    - Audiencia: {audiencia}
    - Mensaje: {mensaje}
    - Tono: {tono}
    - CTA: {cta}
    
    INSTRUCCIONES PARA EL CAMPO `contenido_html`:
    1.  **Todo el cuerpo del email debe estar en formato HTML.** No debe haber texto fuera de las etiquetas.
    2.  **Usa etiquetas `<p>`** para cada párrafo, incluyendo saludo y despedida.
    3.  **Usa la etiqueta `<strong>`** para resaltar en negrita al menos dos frases clave.
    4.  **Para el botón de CTA, usa este código exacto**, reemplazando '{cta}' por el texto de la llamada a la acción:
        `<p style="text-align: center; margin-top: 25px; margin-bottom: 25px;"><a href="https://gomezycrespo.com/" style="background-color: #28a745; color: white; padding: 14px 25px; text-align: center; text-decoration: none; display: inline-block; border-radius: 8px; font-size: 16px; font-weight: bold;">{cta}</a></p>`
    
    INSTRUCCIONES PARA EL CAMPO `contenido`:
    - Crea una versión de texto plano del email, sin ninguna etiqueta HTML. Usa saltos de línea normales.
    
    Genera la respuesta estructurada con los tres campos solicitados.
    """

def get_gmail_regeneration_prompt():
    return """
    Actúa como un especialista en email marketing. Te proporcionaré el asunto y el contenido (en texto plano y HTML) de un correo existente, junto con instrucciones para modificarlo.
    
    Debes generar una nueva versión del correo siguiendo las instrucciones, pero manteniendo la estructura de tres campos: 'asunto', 'contenido' y 'contenido_html'.
    
    DATOS DEL CORREO ORIGINAL:
    - Asunto Original: {original_asunto}
    - Contenido Original (Texto Plano): {original_content}
    
    INSTRUCCIONES DE MEJORA:
    {feedback}
    
    REGLAS PARA EL NUEVO `contenido_html`:
    - Todo el cuerpo debe estar en formato HTML, usando etiquetas `<p>` para párrafos y `<strong>` para resaltar.
    - El botón de CTA debe usar este código, reemplazando '{cta}':
      `<p style="text-align: center; margin-top: 25px; margin-bottom: 25px;"><a href="https://gomezycrespo.com/" style="background-color: #28a745; color: white; padding: 14px 25px; text-align: center; text-decoration: none; display: inline-block; border-radius: 8px; font-size: 16px; font-weight: bold;">{cta}</a></p>`
    
    Genera la nueva versión estructurada.
    """


def get_GyC_info():
    return """
    **Empresa**:
    En el año 1972 instalamos una granja piloto pionera en el sector de la cunicultura, en la que estudiamos el
    comportamiento de los conejos y experimentamos con nuevos modelos de jaulas. Luego comenzamos a construir naves de
    madera para instalar las granjas.

    Hoy en día, nuestra experiencia en el sector de cunicultura, nos hace líderes en el mercado de la fabricación de
    jaulas, accesorios para instalaciones de ganadería y animales de compañía.

    Damos gran importancia a promocionar y dar a conocer nuestros productos, por lo que todos los años acudimos a las
    ferias de exposiciones más importantes de España y Portugal, además de ferias internacionales como las de Cuba y México.

    **Calidad**:
    GÓMEZ Y CRESPO controla la calidad de los productos (jaulas, comederos, bebederos y demás accesorios para animales
    y granjas) durante todo el proceso de fabricación, desde la materia prima (de primera calidad) hasta la recepción
    en nuestros almacenes.

    **Investigación**:
    Las tendencias del mercado varían constantemente, lo que nos obliga a realizar nuevos proyectos.
    En GÓMEZ Y CRESPO contamos con un departamento de I+D+I encargado del desarrollo de nuevos productos y de la
    optimización de los existentes.

    **Contacto**
    Carretera de Castro de Beiro, 41 - 32001 Ourense (Galicia) - Spain
    Teléfono: (+34) 988 217 754
    Email: info@gomezycrespo.com
    """


def get_regeneration_prompt():
    """Prompt para regenerar contenido existente"""
    return """
    Actúa como un especialista en optimización de contenido para marketing digital.

    CONTEXTO:
    Has creado una publicación para {platform} que necesita ser mejorada según el feedback recibido.

    CONTENIDO ORIGINAL:
    {original_content}

    FEEDBACK/INSTRUCCIONES DE MEJORA:
    {feedback}

    OBJETIVO DE LA REGENERACIÓN:
    Modifica el contenido original incorporando las mejoras solicitadas, manteniendo el mensaje central.

    FORMATO DE ENTREGA:
    Proporciona la versión mejorada lista para publicar, sin incluir etiquetas o títulos de secciones.
    El contenido debe estar preparado para ser copiado y pegado directamente en la plataforma.
    """


def get_video_script_prompt():
    return """
    **Rol y Objetivo:** Eres un experto en locución de anuncios para redes sociales. Tu tarea es generar el texto para la locución para un anuncio que sea atractivo, conciso y con un llamado a la acción.
    
    **Contexto de la Empresa Cliente:**
    {info_empresa}
    
    **Tono y Estilo:** El tono debe ser atractivo, conciso y utilizar un acento español (de España) que suene natural, firme y familiar.
    
    **Tarea Específica:** Crea el texto para el anuncio basándote en el siguiente tema: "{tema}".
    
    **Requisitos Finales:**
    - El guion debe ser breve, para que se pueda leer en unos 15 segundos.
    - No incluyas absolutamente ningún prefijo como "Locutor:", "Guion:", o el nombre del rol. Devuelve únicamente el texto de la locución.
    """


def get_translation_prompt():
    """Prompt para solicitar una traducción fiel de un texto."""
    return """
    Actúa como un traductor experto. Tu única misión es traducir el texto que te proporciono al {target_language} de la manera más fiel y natural posible.

    Sigue estas reglas cruciales de forma OBLIGATORIA:

    1.  **Mantenimiento Estricto del Formato**: Replica EXACTAMENTE la estructura del texto original. Esto incluye todos los saltos de línea, espaciado, viñetas, emojis, y cualquier sintaxis de Markdown (como **negritas** o *cursivas*).

    2.  **Sin Adornos ni Explicaciones**: NO añadas introducciones, notas, saludos, despedidas o comentarios de ningún tipo. Tu respuesta debe ser única y exclusivamente el texto traducido.

    3.  **No Incluir Delimitadores**: Los marcadores `---` en la entrada solo sirven para delimitar el texto original que debes traducir. NO los incluyas en tu traducción final.

    TEXTO ORIGINAL A TRADUCIR:
    ---
    {original_text}
    ---

    TRADUCCIÓN AL {target_language}:
    """
