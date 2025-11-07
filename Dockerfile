FROM python:3.11-slim

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app/src"

# Actualizar pip e instalar dependencias del sistema
RUN pip install --upgrade pip && \
    apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY ./src ./src
COPY ./pages ./pages
COPY ./assets ./assets
COPY ./scripts ./scripts
COPY Inicio.py .

# Exponer el puerto por defecto de Streamlit
EXPOSE 8501
