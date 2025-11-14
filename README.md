# Generador y Publicador Automático de Contenido

Este generador y publicador automático es una plataforma integral de marketing de contenidos diseñada para automatizar la creación y distribución de publicaciones en múltiples redes sociales y plataformas digitales. Usando el poder de la inteligencia artificial generativa, esta herramienta te permite definir una estrategia y obtener contenido optimizado para LinkedIn, Instagram, WordPress, Gmail y más, todo desde una única interfaz.

La aplicación no solo genera texto, sino que también cuenta con un completo **pipeline de creación de vídeo**: genera guiones, los convierte a audio con voces neuronales (TTS) y ensambla vídeos listos para publicar a partir de las imágenes que proporciones.

## ✨ Características Principales

  * **✍️ Generación de Contenido con IA**: Crea textos optimizados para **LinkedIn, Instagram, WordPress y Gmail** a partir de un brief de campaña (objetivo, audiencia, tono, etc.).
  * **🎬 Creación de Vídeos Automatizada**:
      * Genera guiones para vídeos cortos basados en un tema.
      * Convierte los guiones en locuciones de audio de alta calidad (Text-to-Speech).
      * Ensambla las imágenes proporcionadas y el audio generado en un fichero de vídeo final, adaptado a diferentes resoluciones (vertical, cuadrado, horizontal).
  * **🚀 Publicación Multiplataforma**: Publica el contenido generado directamente en tus perfiles de redes sociales.
  * **📅 Calendario y Planificador de Contenido**:
      * Guarda tus publicaciones para editarlas más tarde.
      * Programa tus posts para que se publiquen automáticamente en la fecha y hora que elijas.
      * Visualiza todas tus publicaciones programadas en un calendario interactivo.
  * **📚 Biblioteca de Medios Centralizada**: Sube y gestiona todas tus imágenes y vídeos en un solo lugar y reutilízalos fácilmente en diferentes publicaciones.
  * **⚙️ Prompts 100% Configurables**: Modifica directamente desde la aplicación las instrucciones que recibe la IA para adaptar su estilo y enfoque a las necesidades de tu marca.

## 📂 Estructura del Proyecto

La estructura del proyecto está organizada para separar la lógica, la interfaz de usuario y los scripts.

```
.
├── 📁 assets/                       # Recursos estáticos para la UI (logos, previsualizaciones de audio)
├── 📁 pages/                        # Cada fichero .py aquí es una página de la aplicación Streamlit.
├── 📁 scripts/                      # Scripts de utilidad y tareas de fondo (workers).
    ├── publish_programmed_posts.py     # El worker que publica los posts.
    ├── iniciar_sesion_instagram.py     # Script de ayuda para generar la sesión de Instagram.
    └── ...                             # Otros scripts de utilidad.

├── 📁 src/                          # Contiene toda la lógica de negocio principal de la aplicación.
    ├── db_config.py                    # Define el esquema y las funciones para interactuar con la base de datos (SQLAlchemy).
    ├── state.py                        # Centraliza la inicialización del estado de la sesión de Streamlit.
    └── ...                             # Módulos para Instagram, Gmail, LinkedIn, WordPress, generación de texto y vídeo, etc.

├── 📄 .env                          # Fichero crítico donde se almacenan todas las credenciales y claves de API (ignorado por Git).
├── 📄 Dockerfile                    # Instrucciones para construir la imagen de Docker.
├── 📄 docker-compose.yml            # Orquesta los servicios de la aplicación (web y scheduler).
├── 📄 requirements.txt              # Lista de las dependencias de Python.
├── 📄 Inicio.py                     # Punto de entrada principal de la aplicación Streamlit.
└── 📄 README.md                     # Este fichero.

# Carpetas generadas al ejecutar la aplicación (ignoradas por Git)
├── 📁 data/                         # Contiene la base de datos SQLite (posts.db).
├── 📁 media/                        # Biblioteca central para todas las imágenes y vídeos subidos.
├── 📁 output/                       # Directorio de salida de los vídeos generados.
├── 📁 sessions/                     # Guarda los ficheros de sesión (ej. para Instagram).
└── 📁 temp/                         # Directorio para ficheros temporales.
```

-----

## 🛠️ Instalación y Puesta en Marcha

**Opción 1 (Método Recomendado con Docker)**

La aplicación está diseñada para funcionar con Docker, lo que simplifica enormemente la instalación.

### Prerrequisitos

  * **Docker**
  * **Docker Compose**

### Paso 1: Clonar el Repositorio

Abre una terminal y clona este repositorio en tu máquina local:

```bash
git clone https://github.com/Redflexion/Herramienta_RRSS.git
cd Herramienta_RRSS
```

### Paso 2: Configurar las Variables de Entorno

Este es el paso **más importante**. La aplicación necesita varias claves de API y credenciales para funcionar.

1.  En la raíz del proyecto, crea un fichero llamado `.env`.
2.  Copia el contenido de abajo y pégalo en tu nuevo fichero `.env`.
3.  Rellena **todas** las variables con tus propias credenciales.

```ini
# --- API KEY (Obligatoria) ---
# Necesaria para la generación de texto y vídeo
OPENAI_API_KEY="sk-..."

# --- Credenciales de Gmail ---
# Para enviar correos desde la aplicación
GMAIL_USERNAME="tu-correo@gmail.com"
# ¡IMPORTANTE! No es tu contraseña normal. Debes generar una "Contraseña de aplicación"
# desde la configuración de seguridad de tu cuenta de Google.
GMAIL_APP_PASSWORD="abcd efgh ijkl mnop"

# --- Credenciales de Instagram ---
INSTAGRAM_USERNAME="tu_usuario_de_instagram"
INSTAGRAM_PASSWORD="tu_password_de_instagram"

# --- Credenciales de LinkedIn ---
# Token de acceso de una App de la API de LinkedIn v2
ACCESS_TOKEN_LINKEDIN="AQU..."
# Visibilidad de las publicaciones. Opciones: PUBLIC, CONNECTIONS
POST_VISIBILITY="PUBLIC"

# --- Credenciales de WordPress ---
# URL completa de tu sitio de WordPress
WP_SITE="https://tudominio.com"
WP_USER="tu_usuario_wp"
# Debes generar una "Contraseña de Aplicación" en WordPress desde "Usuarios > Perfil"
WP_APP_PASS="xxxx xxxx xxxx xxxx xxxx xxxx"

# --- Credenciales de WhatsApp (Funcionalidad Parcial) ---
# Token de la API de WhatsApp Cloud (Meta for Developers)
WHATSAPP_TOKEN="EAA..."
# ID del número de teléfono de empresa de WhatsApp
WHATSAPP_BUSINESS_ID="123456789012345"
```

> **Nota sobre Contraseñas de Aplicación**: Tanto para **Gmail** como para **WordPress**, no debes usar tu contraseña principal. En su lugar, genera una "Contraseña de Aplicación" específica desde la configuración de seguridad de cada plataforma. Esto es más seguro y evita problemas con la autenticación de dos factores.

### Paso 3: Construir y Ejecutar los Contenedores

Una vez configurado el fichero `.env`, levanta los servicios con Docker Compose. Este comando construirá la imagen de Docker (si no existe) e iniciará la aplicación y el planificador en segundo plano.

```bash
docker-compose up --build
```

### Paso 4: ¡Accede a la Aplicación!

¡Listo! Abre tu navegador web y navega a la siguiente dirección:

**[http://localhost:8501](http://localhost:8501)**

La primera vez que se inicie, el contenedor puede tardar un tiempo en crear la base de datos y arrancar completamente.

-----

**Opción 2 (Local, no recomendada)**

Abre una terminal y ejecuta:

```bash
git clone https://github.com/Redflexion/Herramienta_RRSS.git
cd Herramienta_RRSS

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

python -m scripts.iniciar_sesion_instagram (si es necesario)
python -m src.db_config (si es necesario)

streamlit run Inicio.py

python -m scripts.publish_programmed_posts (en otra terminal)
```

---

## 🚀 Cómo Usar la Aplicación

La interfaz se divide en varias secciones accesibles desde la barra lateral:

#### ✏️ Generación

Es la página principal. Aquí puedes:

1.  **Generar Publicaciones de Texto**: Selecciona las plataformas (LinkedIn, Instagram, etc.), rellena el formulario con los detalles de tu campaña y haz clic en "Generar Publicaciones". Los resultados aparecerán en la columna derecha.
2.  **Generar Vídeos**: Sube las imágenes que quieres usar, escribe el tema para el guion, elige una voz y la resolución. La aplicación generará el vídeo y te mostrará una vista previa para que decidas si quieres añadirlo a tu Biblioteca de Medios.
3.  **Gestionar Medios**: Sube imágenes y vídeos directamente a tu biblioteca central para usarlos más tarde en tus publicaciones.

#### 📝 Publicaciones

En esta sección puedes ver y gestionar todas las publicaciones que has guardado:

  * **Programadas**: Las que tienen una fecha y hora de publicación futuras.
  * **Guardadas**: Las que has guardado como borrador sin una fecha específica.
    Desde aquí puedes editar, eliminar, desprogramar o publicar manualmente cualquier post.

#### 📅 Calendario

Un calendario visual donde puedes ver todas tus publicaciones programadas. Es ideal para tener una vista general de tu estrategia de contenidos.

#### ⚙️ Configuración

Esta es una de las partes más potentes. Aquí puedes editar directamente los **prompts** (instrucciones) que la IA utiliza para generar el contenido de cada plataforma. ¡Puedes ajustar el tono, el estilo y la estructura para que se adapten perfectamente a tu marca!

#### 👥 Contactos

Esta página aloja los contactos y las listas de contactos que se hayan guardado. Te permite crear nuevos contactos y listas, editar los ya existentes y eliminarlos.
Además puedes añadir contactos a partir de ficheros CSV o Excel. Los contactos tienen nombre, número de teléfono, email y listas asociadas.

-----

## 🏛️ Arquitectura del Sistema

El proyecto funciona con una arquitectura de dos contenedores Docker que se comunican a través de una base de datos y un sistema de ficheros compartidos:

1.  **`streamlit_app`**:
      * Este contenedor ejecuta la aplicación web principal con Streamlit.
      * Gestiona todas las interacciones del usuario: generación de contenido, subida de ficheros, programación, etc.
      * En su primer inicio, es responsable de crear la base de datos SQLite en el volumen persistente `data/`.

2.  **`scheduler`**:
      * Este es un servicio en segundo plano (worker) que ejecuta el script `publish_programmed_posts.py` en un bucle infinito.
      * Cada 60 segundos, consulta la base de datos para ver si hay alguna publicación cuya fecha de programación ya ha pasado.
      * Si encuentra una, la publica en la plataforma correspondiente y, si tiene éxito, la elimina de la base de datos.

-----

## ⚠️ Notas Importantes

  * **Inicio de Sesión en Instagram**: La primera vez que la aplicación se conecte a Instagram, puede tardar más y es más susceptible a fallos. Después del primer inicio de sesión exitoso, se guardará un fichero de sesión en `sessions/ig_session.json` para agilizar las futuras conexiones. Si Instagram requiere una verificación de seguridad, puede que necesites intervenir manualmente.

Si es la primera vez que ejecutas el proyecto, o si la sesión de Instagram ha caducado, debes generar este archivo **antes de iniciar la aplicación principal**. Asegúrate de que los contenedores estén detenidos (`docker-compose down` si están corriendo) y luego ejecuta:

    ```bash
    docker-compose run --rm streamlit_app python -m scripts.iniciar_sesion_instagram
    ```
    Sigue las instrucciones en la terminal. Una vez que se genere el fichero `sessions/ig_session.json`, puedes iniciar la aplicación normalmente con `docker-compose up`.

  * **Funcionalidad de WhatsApp**: La integración con WhatsApp está implementada pero con una limitación clave: **el envío de imágenes o vídeos no funcionará por defecto**. La API de WhatsApp requiere que los ficheros multimedia estén alojados en una URL pública. Es necesario modificar la lógica en `src/whatsapp.py` para subir los ficheros a tu propio servidor (ej. Amazon S3) y devolver la URL pública.

  * **Costes de API**: Ten en cuenta que el uso de la API de OpenAI tiene costes asociados. Monitoriza tu consumo en sus respectivas plataformas.
