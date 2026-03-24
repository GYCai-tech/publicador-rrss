"""
Módulo para envío de correos usando Microsoft Graph API.
Ideal para organizaciones con Microsoft 365 que tienen SMTP AUTH deshabilitado.
"""

import os
import re
import time
import uuid
import base64
from typing import List, Optional

import requests
from dotenv import load_dotenv

try:
    import dns.resolver
    _DNS_AVAILABLE = True
except ImportError:
    _DNS_AVAILABLE = False
    print("Advertencia: dnspython no instalado. La validación de dominio de correo estará desactivada.")

try:
    from msal import ConfidentialClientApplication
except ImportError:
    ConfidentialClientApplication = None
    print("Advertencia: msal no está instalado. Ejecuta: pip install msal")

# -----------------------------
# DB logging (opcional)
# -----------------------------
try:
    from .db_config import create_email_send_log, add_email_send_result, complete_email_send_log
except Exception:
    create_email_send_log = None
    add_email_send_result = None
    complete_email_send_log = None


# Cargar variables de entorno
load_dotenv()

# --------------------------------------------------------------------
# Logo en base64 para el footer de correo
# --------------------------------------------------------------------
_LOGO_SRC = "https://gomezycrespo.com/wp-content/uploads/2025/10/PIES-DE-EMAIL-scaled.png"

# --------------------------------------------------------------------
# FOOTER
# --------------------------------------------------------------------
FOOTER_MARKER_TEXT = "PIES-DE-EMAIL"
FOOTER_MARKER_HTML = "<!-- PIES-DE-EMAIL -->"

_LOGO_IMG = (
    f'<a href="https://www.gomezycrespo.com" style="text-decoration:none;">'
    f'<img src="{_LOGO_SRC}" alt="GÓMEZ Y CRESPO" '
    f'style="display:block; width:420px; height:auto; border:0;">'
    f'</a>'
)

EMAIL_FOOTER = f"""
<br><br>
<!-- PIES-DE-EMAIL -->
<table
  width="600"
  cellpadding="0"
  cellspacing="0"
  border="0"
  style="font-family: Arial, sans-serif; font-size:14px; color:#4F764D; background-color:#fafafa;"
>
  <tr>
    <td style="padding:15px; vertical-align:top; width:60%;">
      <strong style="font-size:18px; color:#234926;">Victoria Ábalos</strong><br>
      <span style="color:#4F764D;">International Sales Manager</span><br>
      <a href="mailto:Sales@gomezycrespo.com" style="color:#4F764D; text-decoration:none;">Sales@gomezycrespo.com</a><br>
      <a href="https://linkedin.com/in/victoria-abalos-diaz" style="color:#4F764D; text-decoration:none;">linkedin.com/in/victoria-abalos-diaz</a><br><br>
      <strong style="color:#234926;">Gómez y Crespo S.A.</strong><br>
      <span style="color:#4F764D;">
        Crta. Castro de Beiro nº41<br>
        32001 Ourense, SPAIN<br>
        <a href="https://www.gomezycrespo.com" style="color:#4F764D; text-decoration:none;">www.gomezycrespo.com</a><br>
        Tlf.: 988 21 77 54 Ext. 114
      </span>
    </td>
    <td style="padding:15px; vertical-align:middle; text-align:right; width:40%;">
      {_LOGO_IMG}
    </td>
  </tr>
  <tr>
    <td colspan="2" style="padding:15px; border-top:1px solid #e0e0e0;">
      <span style="font-size:11px; line-height:1.5; color:#4F764D;">
        Este mensaje y sus archivos adjuntos van dirigidos exclusivamente a su destinatario, pudiendo contener información confidencial sometida a secreto profesional. No está permitida su reproducción o distribución sin la autorización expresa de GOMEZ Y CRESPO S.A. Si usted no es el destinatario final por favor elimínelo e infórmenos por esta vía.<br><br>
        En cumplimiento de la Ley Orgánica 15/1999, de 13 de diciembre, de Protección de Datos de carácter personal, y del REGLAMENTO (UE) 2016/679 DEL PARLAMENTO EUROPEO Y DEL CONSEJO de 27 abril de 2016, le informamos que sus datos serán tratados por GOMEZ Y CRESPO S.A. Pueden ejercer los derechos de acceso, rectificación, cancelación, oposición u otros derechos, poniéndose en contacto con GOMEZ Y CRESPO S.A. Utilizamos sus datos para prestarle los servicios que nos ha solicitado así como enviarle comunicaciones comerciales que sean de su interés legitimados en el consentimiento del interesado. No se cederán sus datos a terceros salvo obligación legal. Puede consultar información adicional y detallada sobre protección de datos dirigiéndose al correo electrónico <a href="mailto:info@gomezycrespo.com" style="color:#4F764D;">info@gomezycrespo.com</a>.
      </span>
    </td>
  </tr>
</table>
"""



# --------------------------------------------------------------------
# Helpers para HTML (footer e imágenes inline) - ANTI DUPLICADOS
# --------------------------------------------------------------------
def ensure_html_string(content_text: str, content_html: Optional[str]) -> str:
    """Garantiza que tenemos HTML base."""
    if content_html and isinstance(content_html, str) and content_html.strip():
        return content_html
    # Si no hay HTML, convertimos el texto plano a HTML simple
    safe = (content_text or "").replace("\n", "<br>")
    return f"<div>{safe}</div>"


def ensure_footer_once(html: str) -> str:
    """Añade el footer SOLO si no existe el marcador."""
    if FOOTER_MARKER_TEXT in (html or ""):
        return html
    # Insertar antes de </body> si existe; si no, al final
    if re.search(r"</body>", html, re.IGNORECASE):
        return re.sub(r"(</body>)", rf"{EMAIL_FOOTER}\1", html, flags=re.IGNORECASE, count=1)
    return html + EMAIL_FOOTER


def insert_inline_images_before_footer(html: str, img_tags: str) -> str:
    """Inserta las imágenes inline ANTES del footer usando el marcador; si no hay footer, al final/antes de </body>."""
    if not img_tags:
        return html

    # Si el footer ya existe, insertamos justo antes del marcador HTML
    if FOOTER_MARKER_HTML in html:
        return html.replace(FOOTER_MARKER_HTML, img_tags + FOOTER_MARKER_HTML, 1)

    # Si no hay footer todavía, inserta antes de </body> o al final
    if re.search(r"</body>", html, re.IGNORECASE):
        return re.sub(r"(</body>)", rf"{img_tags}\1", html, flags=re.IGNORECASE, count=1)
    return html + img_tags


def extract_inline_preferences(content_html: Optional[str]) -> tuple[Optional[str], bool, str]:
    """
    Lee preferencias en el HTML:
    - <!-- PREF:INLINE_IMAGES -->  => inline_images = True
    - <!-- PREF:IMG_SIZE:... -->   => ancho de imagen
    Devuelve (html_sin_marcadores, inline_images, img_width)
    """
    inline_images = False
    img_width = "100%"

    if not content_html:
        return content_html, inline_images, img_width

    html = content_html

    if "<!-- PREF:INLINE_IMAGES -->" in html:
        inline_images = True
        html = html.replace("<!-- PREF:INLINE_IMAGES -->", "")

    size_match = re.search(r"<!--\s*PREF:IMG_SIZE:(.*?)\s*-->", html)
    if size_match:
        img_width = size_match.group(1).strip()
        html = html.replace(size_match.group(0), "")

    return html, inline_images, img_width


# --------------------------------------------------------------------
# Conversión Markdown → HTML para cuerpo de correos
# --------------------------------------------------------------------
def _format_inline(text: str) -> str:
    """Aplica formato inline (negrita, cursiva, enlaces) al texto."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" style="color:#234926; text-decoration:underline;">\1</a>', text)
    return text


def markdown_to_html(text: str) -> str:
    """Convierte markdown básico a HTML para correos electrónicos."""
    if not text:
        return ""
    text = text.replace('\r\n', '\n')
    blocks = text.split('\n\n')
    html_blocks = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith('- ') or re.match(r'^\d+\.\s', block):
            lines = block.split('\n')
            is_ordered = re.match(r'^\d+\.\s', lines[0])
            tag = 'ol' if is_ordered else 'ul'
            html_list = f'<{tag} style="margin-bottom: 15px; padding-left: 20px; margin-top: 0;">'
            for line in lines:
                content = re.sub(r'^(- |\d+\.\s)', '', line.strip())
                content = _format_inline(content)
                html_list += f'<li style="margin-bottom: 5px;">{content}</li>'
            html_list += f'</{tag}>'
            html_blocks.append(html_list)
        else:
            content = _format_inline(block)
            content = content.replace('\n', '<br>')
            html_blocks.append(f'<p style="margin-bottom: 15px; margin-top: 0; line-height: 1.6;">{content}</p>')
    return '\n'.join(html_blocks)


def build_attachments_payload(
    attachments: Optional[List[str]],
    inline_images: bool,
    img_width: str
) -> tuple[list, str]:
    """
    Prepara payload de adjuntos para Graph y, si inline_images=True,
    genera etiquetas <img src="cid:..."> para insertar en el HTML.
    """
    processed_attachments = []
    img_tags_to_add = ""

    if not attachments:
        return processed_attachments, img_tags_to_add

    print(f"📎 Procesando {len(attachments)} adjuntos (Inline: {inline_images})...")

    for filepath in attachments:
        if not os.path.exists(filepath):
            print(f"❌ Archivo no encontrado: {filepath}")
            continue

        try:
            with open(filepath, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")

            filename = os.path.basename(filepath)
            ext = filename.lower()

            content_type = "application/octet-stream"
            is_image = False
            if ext.endswith((".jpg", ".jpeg")):
                content_type = "image/jpeg"
                is_image = True
            elif ext.endswith(".png"):
                content_type = "image/png"
                is_image = True
            elif ext.endswith(".gif"):
                content_type = "image/gif"
                is_image = True
            elif ext.endswith(".pdf"):
                content_type = "application/pdf"

            attachment_payload = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": filename,
                "contentType": content_type,
                "contentBytes": content
            }

            if inline_images and is_image:
                cid = str(uuid.uuid4())
                attachment_payload["isInline"] = True
                attachment_payload["contentId"] = cid
                img_tags_to_add += (
                    f'<br><img src="cid:{cid}" alt="{filename}" style="width:{img_width}; height:auto;"><br>'
                )
                print(f"✅ Imagen INLINE: {filename} (CID: {cid})")
            else:
                attachment_payload["isInline"] = False
                print(f"✅ Adjunto: {filename}")

            processed_attachments.append(attachment_payload)

        except Exception as e:
            print(f"❌ Error al procesar adjunto {filepath}: {e}")

    return processed_attachments, img_tags_to_add


# --------------------------------------------------------------------
# Config / Auth Microsoft Graph
# --------------------------------------------------------------------
def get_graph_config() -> Optional[dict]:
    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    tenant_id = os.getenv("MICROSOFT_TENANT_ID")
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
    sender_email = os.getenv("MICROSOFT_SENDER_EMAIL")

    if not all([client_id, tenant_id, client_secret, sender_email]):
        return None

    return {
        "client_id": client_id,
        "tenant_id": tenant_id,
        "client_secret": client_secret,
        "sender_email": sender_email
    }


def get_access_token() -> Optional[str]:
    if ConfidentialClientApplication is None:
        print("Error: msal no está instalado. Ejecuta: pip install msal")
        return None

    config = get_graph_config()
    if not config:
        print("Error: Configuración de Microsoft Graph incompleta.")
        return None

    authority = f"https://login.microsoftonline.com/{config['tenant_id']}"

    app = ConfidentialClientApplication(
        config["client_id"],
        authority=authority,
        client_credential=config["client_secret"]
    )

    scopes = ["https://graph.microsoft.com/.default"]
    result = app.acquire_token_for_client(scopes=scopes)

    if "access_token" in result:
        return result["access_token"]

    print(f"Error obteniendo token: {result.get('error', 'Unknown error')}")
    print(f"Descripción: {result.get('error_description', '')}")
    return None


# --------------------------------------------------------------------
# Envío simple (1 mensaje a varios destinatarios)
# --------------------------------------------------------------------
def validate_email_domain(email: str) -> tuple[bool, str]:
    """
    Comprueba que el dominio del email tiene registros MX válidos.
    Devuelve (True, '') si es válido, (False, mensaje_error) si no.
    Si dnspython no está disponible, devuelve (True, '') para no bloquear envíos.
    """
    if not _DNS_AVAILABLE:
        return True, ''
    try:
        domain = email.strip().lower().split('@')[-1]
        dns.resolver.resolve(domain, 'MX')
        return True, ''
    except dns.resolver.NXDOMAIN:
        return False, f"El dominio '{email.split('@')[-1]}' no existe"
    except dns.resolver.NoAnswer:
        return False, f"El dominio '{email.split('@')[-1]}' no tiene servidor de correo (sin registros MX)"
    except dns.resolver.Timeout:
        return True, ''  # En caso de timeout no bloqueamos el envío
    except Exception:
        return True, ''  # Ante cualquier error DNS no bloqueamos


def send_mail_graph(
    receivers: List[str],
    subject: str,
    content_text: str,
    content_html: Optional[str] = None,
    attachments: Optional[List[str]] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    inline_images: bool = False
) -> bool:
    config = get_graph_config()
    if not config:
        print("Error: Configuración de Microsoft Graph incompleta.")
        print("Variables requeridas en .env:")
        print("  MICROSOFT_CLIENT_ID")
        print("  MICROSOFT_TENANT_ID")
        print("  MICROSOFT_CLIENT_SECRET")
        print("  MICROSOFT_SENDER_EMAIL")
        return False

    if not receivers:
        print("Advertencia: No hay destinatarios para enviar el correo.")
        return False

    access_token = get_access_token()
    if not access_token:
        return False

    # Preferencias embebidas en HTML
    content_html, pref_inline, img_width = extract_inline_preferences(content_html)
    if pref_inline:
        inline_images = True
        print("✅ Preferencia inline_images detectada en HTML.")
    if content_html:
        print(f"✅ Preferencia de tamaño de imagen: {img_width}")

    # HTML base
    html = ensure_html_string(content_text, content_html)

    # Adjuntos + imágenes inline
    processed_attachments, img_tags_to_add = build_attachments_payload(
        attachments=attachments,
        inline_images=inline_images,
        img_width=img_width
    )

    # Insertar imágenes inline antes del footer (por marcador) o al final
    html = insert_inline_images_before_footer(html, img_tags_to_add)

    # Asegurar footer una sola vez
    html = ensure_footer_once(html)

    print("🧪 FOOTER count:", html.count(FOOTER_MARKER_TEXT))

    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html},
            "toRecipients": [{"emailAddress": {"address": email}} for email in receivers],
        },
        "saveToSentItems": "true"
    }

    if cc:
        message["message"]["ccRecipients"] = [{"emailAddress": {"address": email}} for email in cc]
    if bcc:
        message["message"]["bccRecipients"] = [{"emailAddress": {"address": email}} for email in bcc]
    if processed_attachments:
        message["message"]["attachments"] = processed_attachments

    sender_email = config["sender_email"]
    endpoint = f"https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    try:
        response = requests.post(endpoint, json=message, headers=headers)
        if response.status_code == 202:
            print(f"Correo enviado exitosamente via Graph API a: {', '.join(receivers)}")
            return True

        print(f"Error al enviar correo: {response.status_code}")
        print(f"Respuesta: {response.text}")

        if response.status_code == 401:
            print("\nPosible solución: Verifica que el Client Secret no haya expirado.")
        elif response.status_code == 403:
            print("\nPosible solución: Verifica que la app tenga el permiso 'Mail.Send' (APLICACIÓN) en Azure.")
        elif response.status_code == 404:
            print(f"\nPosible solución: Verifica que el email '{sender_email}' exista y sea válido.")

        return False

    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")
        return False


# --------------------------------------------------------------------
# Envío masivo individual (un correo por destinatario)
# --------------------------------------------------------------------
def send_mail_graph_bulk(
    receivers: List[str],
    subject: str,
    content_text: str,
    content_html: Optional[str] = None,
    attachments: Optional[List[str]] = None,
    inline_images: bool = False,
    progress_callback=None,
    delay_between_emails: float = 2.0
) -> dict:
    if not receivers:
        return {'total': 0, 'successful': 0, 'failed': 0, 'successful_emails': [], 'failed_emails': []}

    config = get_graph_config()
    if not config:
        return {
            'total': len(receivers),
            'successful': 0,
            'failed': len(receivers),
            'successful_emails': [],
            'failed_emails': [{'email': e, 'error': 'Configuración incompleta'} for e in receivers]
        }

    access_token = get_access_token()
    if not access_token:
        return {
            'total': len(receivers),
            'successful': 0,
            'failed': len(receivers),
            'successful_emails': [],
            'failed_emails': [{'email': e, 'error': 'No se pudo obtener token de acceso'} for e in receivers]
        }

    # Log BD (opcional)
    send_log_id = None
    if create_email_send_log:
        try:
            send_log_id = create_email_send_log(platform='Gmail', subject=subject, total_recipients=len(receivers))
        except Exception as e:
            print(f"⚠️ No se pudo crear log en BD: {e}")

    # Preferencias HTML
    content_html, pref_inline, img_width = extract_inline_preferences(content_html)
    if pref_inline:
        inline_images = True

    # HTML base
    html = ensure_html_string(content_text, content_html)

    # Adjuntos (una vez) + imágenes inline
    processed_attachments, img_tags_to_add = build_attachments_payload(
        attachments=attachments,
        inline_images=inline_images,
        img_width=img_width
    )

    # Insertar imágenes y footer (una vez) para TODOS
    html = insert_inline_images_before_footer(html, img_tags_to_add)
    html = ensure_footer_once(html)

    print("🧪 FOOTER count:", html.count(FOOTER_MARKER_TEXT))

    sender_email = config["sender_email"]
    endpoint = f"https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    successful_emails = []
    failed_emails = []

    total = len(receivers)

    for idx, receiver_email in enumerate(receivers, 1):
        if progress_callback:
            progress_callback(idx, total, receiver_email)

        message = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html},
                "toRecipients": [{"emailAddress": {"address": receiver_email}}]
            },
            "saveToSentItems": "true"
        }

        if processed_attachments:
            message["message"]["attachments"] = processed_attachments

        try:
            response = requests.post(endpoint, json=message, headers=headers)
            if response.status_code == 202:
                successful_emails.append(receiver_email)
                print(f"✅ [{idx}/{total}] Enviado a: {receiver_email}")

                if send_log_id and add_email_send_result:
                    try:
                        add_email_send_result(send_log_id=send_log_id, recipient_email=receiver_email, success=True)
                    except Exception as e:
                        print(f"⚠️ No se pudo registrar éxito en BD: {e}")
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                failed_emails.append({'email': receiver_email, 'error': error_msg})
                print(f"❌ [{idx}/{total}] Error: {receiver_email} - {error_msg}")

                if send_log_id and add_email_send_result:
                    try:
                        add_email_send_result(
                            send_log_id=send_log_id,
                            recipient_email=receiver_email,
                            success=False,
                            error_code=f"HTTP {response.status_code}",
                            error_message=response.text[:500]
                        )
                    except Exception as e:
                        print(f"⚠️ No se pudo registrar fallo en BD: {e}")

        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión: {e}"
            failed_emails.append({'email': receiver_email, 'error': error_msg})
            print(f"❌ [{idx}/{total}] {receiver_email} - {error_msg}")

            if send_log_id and add_email_send_result:
                try:
                    add_email_send_result(
                        send_log_id=send_log_id,
                        recipient_email=receiver_email,
                        success=False,
                        error_code="CONNECTION_ERROR",
                        error_message=str(e)[:500]
                    )
                except Exception as ex:
                    print(f"⚠️ No se pudo registrar error en BD: {ex}")

        if idx < total:
            time.sleep(delay_between_emails)

    result = {
        'total': total,
        'successful': len(successful_emails),
        'failed': len(failed_emails),
        'successful_emails': successful_emails,
        'failed_emails': failed_emails
    }

    if send_log_id and complete_email_send_log:
        try:
            complete_email_send_log(send_log_id=send_log_id,
                                   successful_count=result['successful'],
                                   failed_count=result['failed'])
        except Exception as e:
            print(f"⚠️ No se pudo completar log en BD: {e}")

    return result


# --------------------------------------------------------------------
# Envío Batch API (hasta 20 operaciones por batch)
# --------------------------------------------------------------------
def send_mail_graph_batch(
    receivers: List[str],
    subject: str,
    content_text: str,
    content_html: Optional[str] = None,
    attachments: Optional[List[str]] = None,
    inline_images: bool = False,
    progress_callback=None,
    batch_size: int = 20
) -> dict:
    if not receivers:
        return {'total': 0, 'successful': 0, 'failed': 0, 'successful_emails': [], 'failed_emails': []}

    config = get_graph_config()
    if not config:
        return {
            'total': len(receivers),
            'successful': 0,
            'failed': len(receivers),
            'successful_emails': [],
            'failed_emails': [{'email': e, 'error': 'Configuración incompleta'} for e in receivers]
        }

    access_token = get_access_token()
    if not access_token:
        return {
            'total': len(receivers),
            'successful': 0,
            'failed': len(receivers),
            'successful_emails': [],
            'failed_emails': [{'email': e, 'error': 'No se pudo obtener token'} for e in receivers]
        }

    # Validación de dominio DNS antes de enviar
    valid_receivers = []
    pre_failed = []
    for email in receivers:
        ok, err = validate_email_domain(email)
        if ok:
            valid_receivers.append(email)
        else:
            pre_failed.append({'email': email, 'error': err})
            print(f"❌ Dominio inválido: {email} — {err}")

    # Log BD (opcional) — total incluye los pre-fallidos
    send_log_id = None
    if create_email_send_log:
        try:
            send_log_id = create_email_send_log(platform='Gmail', subject=subject, total_recipients=len(receivers))
        except Exception as e:
            print(f"⚠️ No se pudo crear log en BD: {e}")

    # Registrar los pre-fallidos (dominio inválido) en BD
    if send_log_id and add_email_send_result:
        for pf in pre_failed:
            try:
                add_email_send_result(
                    send_log_id=send_log_id,
                    recipient_email=pf['email'],
                    success=False,
                    error_code='INVALID_DOMAIN',
                    error_message=pf['error']
                )
            except Exception as e:
                print(f"⚠️ No se pudo registrar dominio inválido en BD: {e}")

    # Si no quedan correos válidos, devolver resultado directamente
    if not valid_receivers:
        result = {
            'total': len(receivers),
            'successful': 0,
            'failed': len(pre_failed),
            'successful_emails': [],
            'failed_emails': pre_failed
        }
        if send_log_id and complete_email_send_log:
            try:
                complete_email_send_log(send_log_id=send_log_id, successful_count=0, failed_count=len(pre_failed))
            except Exception:
                pass
        return result

    # Preferencias HTML
    content_html, pref_inline, img_width = extract_inline_preferences(content_html)
    if pref_inline:
        inline_images = True

    # HTML base
    html = ensure_html_string(content_text, content_html)

    # Adjuntos (una vez) + imágenes inline
    processed_attachments, img_tags_to_add = build_attachments_payload(
        attachments=attachments,
        inline_images=inline_images,
        img_width=img_width
    )

    # Insertar imágenes y footer (una vez) para TODOS
    html = insert_inline_images_before_footer(html, img_tags_to_add)
    html = ensure_footer_once(html)

    print("🧪 FOOTER count:", html.count(FOOTER_MARKER_TEXT))

    sender_email = config["sender_email"]
    batch_endpoint = "https://graph.microsoft.com/v1.0/$batch"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    total = len(receivers)
    successful_emails = []
    failed_emails = list(pre_failed)  # incluir los pre-fallidos por dominio inválido

    valid_total = len(valid_receivers)
    batches_needed = (valid_total + batch_size - 1) // batch_size
    email_index = 0

    for batch_num in range(batches_needed):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, valid_total)
        batch_receivers = valid_receivers[batch_start:batch_end]

        batch_requests = []
        for i, receiver_email in enumerate(batch_receivers):
            email_index += 1
            if progress_callback:
                progress_callback(email_index, total, receiver_email)

            message = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "HTML", "content": html},
                    "toRecipients": [{"emailAddress": {"address": receiver_email}}]
                },
                "saveToSentItems": "true"
            }

            if processed_attachments:
                message["message"]["attachments"] = processed_attachments

            batch_requests.append({
                "id": str(batch_start + i),
                "method": "POST",
                "url": f"/users/{sender_email}/sendMail",
                "body": message,
                "headers": {"Content-Type": "application/json"}
            })

        batch_payload = {"requests": batch_requests}

        try:
            print(f"📦 Enviando batch {batch_num + 1}/{batches_needed} ({len(batch_receivers)} correos)...")
            response = requests.post(batch_endpoint, json=batch_payload, headers=headers)

            if response.status_code == 200:
                batch_response = response.json()

                for resp in batch_response.get("responses", []):
                    request_id = int(resp["id"])
                    receiver_email = valid_receivers[request_id]
                    status_code = resp.get("status", 500)

                    if status_code == 202:
                        successful_emails.append(receiver_email)
                        if send_log_id and add_email_send_result:
                            try:
                                add_email_send_result(send_log_id=send_log_id, recipient_email=receiver_email, success=True)
                            except Exception as e:
                                print(f"⚠️ No se pudo registrar éxito en BD: {e}")
                    else:
                        error_body = resp.get("body", {})
                        error_msg = error_body.get("error", {}).get("message", f"HTTP {status_code}")
                        failed_emails.append({"email": receiver_email, "error": error_msg})

                        if send_log_id and add_email_send_result:
                            try:
                                add_email_send_result(
                                    send_log_id=send_log_id,
                                    recipient_email=receiver_email,
                                    success=False,
                                    error_code=f"HTTP {status_code}",
                                    error_message=str(error_msg)[:500]
                                )
                            except Exception as e:
                                print(f"⚠️ No se pudo registrar fallo en BD: {e}")
            else:
                error_msg = f"Batch falló: HTTP {response.status_code} - {response.text[:200]}"
                print(f"❌ {error_msg}")
                for receiver_email in batch_receivers:
                    failed_emails.append({"email": receiver_email, "error": error_msg})

        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conexión en batch: {e}"
            print(f"❌ {error_msg}")
            for receiver_email in batch_receivers:
                failed_emails.append({"email": receiver_email, "error": error_msg})

        if batch_num < batches_needed - 1:
            time.sleep(0.5)

    result = {
        'total': total,
        'successful': len(successful_emails),
        'failed': len(failed_emails),
        'successful_emails': successful_emails,
        'failed_emails': failed_emails
    }

    if send_log_id and complete_email_send_log:
        try:
            complete_email_send_log(send_log_id=send_log_id,
                                   successful_count=result['successful'],
                                   failed_count=result['failed'])
        except Exception as e:
            print(f"⚠️ No se pudo completar log en BD: {e}")

    return result


# --------------------------------------------------------------------
# Test conexión
# --------------------------------------------------------------------
def test_graph_connection() -> bool:
    config = get_graph_config()
    if not config:
        print("Error: Configuración de Microsoft Graph incompleta.")
        return False

    print("Probando conexión con Microsoft Graph API...")
    print(f"  Client ID: {config['client_id'][:8]}...")
    print(f"  Tenant ID: {config['tenant_id'][:8]}...")
    print(f"  Sender: {config['sender_email']}")

    token = get_access_token()
    if token:
        print("Conexión exitosa con Microsoft Graph API")
        return True

    print("Error: No se pudo obtener el token de acceso")
    return False


if __name__ == "__main__":
    print("Test del módulo Microsoft Graph API")
    print("=" * 50)

    if get_graph_config():
        test_graph_connection()
    else:
        print("Configura las siguientes variables en tu .env:")
        print("  MICROSOFT_CLIENT_ID=tu-client-id")
        print("  MICROSOFT_TENANT_ID=tu-tenant-id")
        print("  MICROSOFT_CLIENT_SECRET=tu-client-secret")
        print("  MICROSOFT_SENDER_EMAIL=correo@tudominio.com")
