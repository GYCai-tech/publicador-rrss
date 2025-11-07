import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


def send_mail(receivers: List[str], subject: str, content_text: str, content_html: Optional[str] = None, attachments: Optional[List[str]] = None) -> bool:
    """
    Envía un correo con adjuntos usando la lógica verificada por el usuario.
    """
    # Cargar credenciales de forma segura desde las variables de entorno
    sender_email = os.getenv("GMAIL_USERNAME")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        print("Error: No se encontraron las credenciales de Gmail (GMAIL_USERNAME, GMAIL_APP_PASSWORD)")
        return False

    if not receivers:
        print("Advertencia: No hay destinatarios para enviar el correo.")
        return False

    try:
        # Crear un único contenedor principal de tipo 'mixed'
        msg = MIMEMultipart('mixed')
        msg['From'] = sender_email
        msg['Subject'] = subject
        msg['To'] = ", ".join(receivers)

        # Crear un sub-contenedor 'alternative' para el cuerpo del mensaje
        body_part = MIMEMultipart('alternative')

        # Siempre adjuntar la versión de texto plano
        body_part.attach(MIMEText(content_text, 'plain'))
        # Si existe una versión HTML, adjuntarla también
        if content_html:
            body_part.attach(MIMEText(content_html, 'html'))

        # Adjuntar el bloque del cuerpo completo (con texto y/o html) al mensaje principal
        msg.attach(body_part)

        # Adjuntar los ficheros directamente al mensaje principal
        if attachments:
            for filepath in attachments:
                if not os.path.exists(filepath):
                    print(f"Advertencia: Fichero adjunto no encontrado y será omitido: {filepath}")
                    continue

                with open(filepath, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())

                encoders.encode_base64(part)
                filename = os.path.basename(filepath)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(part)
                print(f"Fichero adjuntado: {filename}")

        # Conectar y enviar el mensaje completo
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(sender_email, app_password)
            # El mensaje se convierte a string una única vez, justo antes de enviarlo
            server.sendmail(sender_email, receivers, msg.as_string())

        print(f"Correo enviado exitosamente a: {', '.join(receivers)}")
        return True

    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False
