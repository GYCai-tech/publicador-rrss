import os
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from sqlalchemy import create_engine, Column, Integer, String, Text, Table, ForeignKey, CheckConstraint
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, joinedload
from sqlalchemy.exc import IntegrityError
import logging
from contextlib import contextmanager
import streamlit as st


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("programmed_posts.log", encoding='utf-8'),
        # StreamHandler intenta usar la mejor codificación para la consola
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración de la base de datos
DB_DIR = "data"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DB_URL = f"sqlite:///{os.path.join(DB_DIR, 'posts.db')}"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tabla de asociación para la relación Muchos-a-Muchos entre Posts y MediaAssets
post_media_association = Table(
    'post_media_association', Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id'), primary_key=True),
    Column('media_id', Integer, ForeignKey('media_assets.id'), primary_key=True)
)

# Tabla de asociación para la relación Muchos-a-Muchos entre Contactos y Listas de Contactos
contact_list_association = Table(
    'contact_list_association', Base.metadata,
    Column('contact_id', Integer, ForeignKey('contacts.id'), primary_key=True),
    Column('list_id', Integer, ForeignKey('contact_lists.id'), primary_key=True)
)


class ContactList(Base):
    __tablename__ = "contact_lists"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    contacts = relationship("Contact", secondary=contact_list_association, back_populates="lists")


class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    lists = relationship("ContactList", secondary=contact_list_association, back_populates="contacts")
    __table_args__ = (CheckConstraint('phone IS NOT NULL OR email IS NOT NULL', name='check_phone_or_email'),)


class MediaAsset(Base):
    """
    Representa un activo multimedia (imagen o vídeo) en la biblioteca central.
    """
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False, unique=True)
    file_type = Column(String, nullable=False)  # 'image' o 'video'
    original_filename = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().isoformat())


class Post(Base):
    """
    Representa una entrada de publicación en la aplicación.

    Almacena el contenido textual de una publicación (título, contenido, etc.) y se
    relaciona con los activos multimedia a través de la tabla de asociación.

    Attributes:
        id (int): Identificador único del post.
        title (str): Título del post.
        content (str): Contenido principal del post.
        asunto (str, optional): Asunto para correos electrónicos.
        platform (str): Plataforma de destino (ej. "Instagram", "WordPress").
        contacts (str, optional): Lista de contactos en formato JSON.
        fecha_hora (str, optional): Fecha y hora de programación para la publicación.
        created_at (str): Timestamp de creación.
        updated_at (str): Timestamp de la última actualización.
        media_assets (relationship): Relación con los MediaAsset asociados a este post.
    """
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    content_html = Column(Text, nullable=True)
    asunto = Column(String, nullable=True)
    platform = Column(String, nullable=False)
    contacts = Column(Text, nullable=True)
    fecha_hora = Column(String, nullable=True)
    sent_at = Column(String, nullable=True)  # Timestamp de cuando se envió la publicación
    created_at = Column(String, nullable=False, default=lambda: datetime.now().isoformat())
    updated_at = Column(String, nullable=False, default=lambda: datetime.now().isoformat())

    media_assets = relationship(
        "MediaAsset",
        secondary=post_media_association,
        back_populates="posts"
    )


# Añadir una back_populates a MediaAsset para una relación bidireccional explícita
MediaAsset.posts = relationship(
    "Post",
    secondary=post_media_association,
    back_populates="media_assets"
)


def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    """
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session():
    """
    Provee una sesión de base de datos transaccional.
    Cualquier cambio es confirmado si no hay errores, o revertido si los hay.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# --- Funciones Auxiliares ---
def serialize_list(data: Optional[List[str]]) -> Optional[str]:
    if data is None:
        return None
    return json.dumps(sorted(list(set(data))))


def deserialize_list(json_string: Optional[str]) -> List[str]:
    if not json_string:
        return []
    try:
        data = json.loads(json_string)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def model_to_dict(model_instance: Base) -> Dict[str, Any]:
    """
    Convierte una instancia de un modelo SQLAlchemy a un diccionario.
    """
    if not model_instance:
        return {}

    d = {c.name: getattr(model_instance, c.name) for c in model_instance.__table__.columns}

    if isinstance(model_instance, Post):
        d['media_assets'] = [
            {"id": asset.id, "file_path": asset.file_path, "file_type": asset.file_type, "original_filename": asset.original_filename}
            for asset in model_instance.media_assets
        ]
        d['contacts'] = deserialize_list(d.get('contacts'))

    if isinstance(model_instance, Contact):
        d['lists'] = [{"id": l.id, "name": l.name} for l in model_instance.lists]

    d['emails'] = deserialize_list(d.get('email'))
    d['phones'] = deserialize_list(d.get('phone'))

    return d


# --- Funciones de Contactos y Listas ---
def create_contact_list(name: str) -> Dict[str, Any]:
    with get_db_session() as session:
        try:
            if not name.strip():
                return {"success": False, "message": "El nombre de la lista no puede estar vacío."}
            new_list = ContactList(name=name)
            session.add(new_list)
            session.commit()
            return {"success": True, "message": "Lista creada con éxito."}
        except IntegrityError:
            return {"success": False, "message": f"La lista '{name}' ya existe."}
        except Exception as e:
            return {"success": False, "message": f"Error inesperado: {str(e)}"}


@st.cache_data(ttl=60)
def get_all_contact_lists() -> List[Dict[str, Any]]:
    with get_db_session() as session:
        lists = session.query(ContactList).order_by(ContactList.name).all()
        return [model_to_dict(l) for l in lists]


def delete_contact_list(list_id: int) -> bool:
    with get_db_session() as session:
        list_to_delete = session.query(ContactList).filter(ContactList.id == list_id).first()
        if not list_to_delete:
            return False
        session.delete(list_to_delete)
        return True


def format_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    phone_digits = re.sub(r'[\s()-]', '', str(phone))
    if phone_digits.startswith('+'):
        return phone_digits
    if phone_digits.startswith('00'):
        return '+' + phone_digits[2:]
    if len(phone_digits) == 9 and phone_digits.startswith(('6', '7')):
        return f"+34{phone_digits}"
    return phone


def _is_duplicate(session: SessionLocal, new_phones: Set[str], new_emails: Set[str], exclude_contact_id: Optional[int] = None) -> bool:
    query = session.query(Contact)
    if exclude_contact_id:
        query = query.filter(Contact.id != exclude_contact_id)

    all_contacts = query.all()
    for contact in all_contacts:
        existing_phones = set(deserialize_list(contact.phone))
        existing_emails = set(deserialize_list(contact.email))
        if new_phones == existing_phones and new_emails == existing_emails:
            return True
    return False


def _clean_and_filter_phones(phones: Optional[List[str]]) -> List[str]:
    """
    Toma una lista de teléfonos, ignora los fijos españoles y formatea los restantes.
    """
    if not phones:
        return []

    sendable_phones = []
    for p in phones:
        if not p or not p.strip():
            continue

        # Comprobar si es un fijo español antes de formatear
        clean_p = re.sub(r'[\s()-]', '', p.strip())
        if len(clean_p) == 9 and (clean_p.startswith('8') or clean_p.startswith('9')):
            # Es un fijo, lo ignoramos y continuamos con el siguiente.
            continue

        # Si no es un fijo, lo formateamos y lo añadimos a la lista.
        formatted_p = format_phone(p)
        if formatted_p:
            sendable_phones.append(formatted_p)

    # Devolver una lista única y ordenada
    return sorted(list(set(sendable_phones)))


def create_contact(name: str, phones: Optional[List[str]], emails: Optional[List[str]], list_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    with get_db_session() as session:
        if not name.strip():
            return {"success": False, "message": "El nombre del contacto es obligatorio."}

        norm_phones = _clean_and_filter_phones(phones)
        norm_emails = sorted(list(set(e.strip().lower() for e in emails if e and e.strip()))) if emails else []
        if not norm_phones and not norm_emails:
            return {"success": False, "message": "Debe proporcionar al menos un teléfono móvil o un email válido."}

        if _is_duplicate(session, set(norm_phones), set(norm_emails)):
            return {"success": False, "message": "Ya existe un contacto con la misma combinación de teléfonos y emails."}

        try:
            new_contact = Contact(name=name.strip(), phone=serialize_list(norm_phones), email=serialize_list(norm_emails))
            if list_ids:
                lists = session.query(ContactList).filter(ContactList.id.in_(list_ids)).all()
                new_contact.lists.extend(lists)
            session.add(new_contact)
            session.flush()
            return {"success": True, "message": "Contacto añadido con éxito."}

        except Exception as e:
            session.rollback()
            logger.error(f"Error inesperado al crear contacto: {e}")
            return {"success": False, "message": f"Error inesperado: {str(e)}"}


def create_contacts_bulk(contacts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    added_count = 0
    errors = []
    seen_in_file = set()
    logger.info(f"Iniciando importación masiva de {len(contacts_data)} filas.")

    with get_db_session() as session:
        # Pre-cargar todos los contactos existentes para una comprobación eficiente
        existing_contacts = [
            (set(deserialize_list(c.phone)), set(deserialize_list(c.email)))
            for c in session.query(Contact).all()
        ]

        for i, data in enumerate(contacts_data):
            row_num = i + 2
            name = data.get('name', '').strip()
            phones = _clean_and_filter_phones(data.get('phones', []))
            emails = sorted(list(set(e.strip().lower() for e in data.get('emails', []) if e and e.strip())))

            # Validación básica
            if not name or not (phones or emails):
                errors.append(f"Fila {row_num} ('{name}'): omitida por faltar nombre, email o teléfono.")
                continue

            phones_set = set(phones)
            emails_set = set(emails)

            # Comprobar duplicados en el propio archivo
            contact_signature = (frozenset(phones_set), frozenset(emails_set))
            if contact_signature in seen_in_file:
                errors.append(f"Fila {row_num} ('{name}'): Omitida por estar duplicada en el archivo.")
                continue

            # Comprobar duplicados con la base de datos
            is_db_duplicate = False
            for existing_phones, existing_emails in existing_contacts:
                if phones_set == existing_phones and emails_set == existing_emails:
                    is_db_duplicate = True
                    break

            if is_db_duplicate:
                errors.append(f"Fila {row_num} ('{name}'): Omitida. Ya existe un contacto con estos teléfonos y emails.")
                continue

            # Si pasa las validaciones, se añade
            try:
                new_contact = Contact(
                    name=name,
                    email=serialize_list(emails),
                    phone=serialize_list(phones)
                )
                if data.get('list_ids'):
                    lists = session.query(ContactList).filter(ContactList.id.in_(data['list_ids'])).all()
                    new_contact.lists.extend(lists)
                session.add(new_contact)

                # Añadir a los vistos para futuras comprobaciones en el mismo lote
                seen_in_file.add(contact_signature)
                existing_contacts.append((phones_set, emails_set))
                added_count += 1
            except Exception as e:
                errors.append(f"Fila {row_num} ('{name}'): Error inesperado al guardar: {e}")

    return {"success": True, "message": "Proceso de importación finalizado.", "added": added_count, "errors": errors}


def update_contact(contact_id: int, name: str, phones: Optional[List[str]], emails: Optional[List[str]], list_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    with get_db_session() as session:
        contact = session.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            return {"success": False, "message": "El contacto no fue encontrado."}

        # Normalizar y limpiar datos de entrada
        norm_phones = _clean_and_filter_phones(phones)
        norm_emails = sorted(list(set(e.strip().lower() for e in emails if e and e.strip()))) if emails else []

        if not name.strip():
            return {"success": False, "message": "El nombre del contacto es obligatorio."}
        if not norm_phones and not norm_emails:
            return {"success": False, "message": "Se requiere al menos un teléfono móvil o un email."}

        if _is_duplicate(session, set(norm_phones), set(norm_emails), exclude_contact_id=contact_id):
            return {"success": False, "message": "Ya existe otro contacto con la misma combinación de teléfonos y emails."}

        try:
            contact.name = name.strip()
            contact.phone = serialize_list(norm_phones)
            contact.email = serialize_list(norm_emails)

            contact.lists.clear()
            if list_ids:
                lists = session.query(ContactList).filter(ContactList.id.in_(list_ids)).all()
                contact.lists.extend(lists)

            session.commit()
            return {"success": True, "message": "Contacto actualizado con éxito."}

        except Exception as e:
            session.rollback()
            return {"success": False, "message": f"Error inesperado: {str(e)}"}


def get_contact_by_id(contact_id: int) -> Optional[Dict[str, Any]]:
    with get_db_session() as session:
        contact = session.query(Contact).options(joinedload(Contact.lists)).filter(Contact.id == contact_id).first()
        return model_to_dict(contact)


@st.cache_data(ttl=30)
def get_all_contacts() -> List[Dict[str, Any]]:
    with get_db_session() as session:
        contacts = session.query(Contact).options(joinedload(Contact.lists)).order_by(Contact.name).all()
        return [model_to_dict(c) for c in contacts]


def get_contacts_by_list(list_id: int) -> List[Dict[str, Any]]:
    with get_db_session() as session:
        contacts = session.query(Contact).filter(Contact.lists.any(id=list_id)).order_by(Contact.name).all()
        return [model_to_dict(c) for c in contacts]


def delete_contact(contact_id: int) -> bool:
    with get_db_session() as session:
        contact = session.query(Contact).filter(Contact.id == contact_id).first()
        if contact:
            session.delete(contact)
            return True
        return False


# --- Funciones de Posts y Media ---
def title_already_exists(title: str) -> bool:
    """
    Verifica si ya existe un post con el mismo título.
    """
    with get_db_session() as session:
        return session.query(Post).filter(Post.title == title).first() is not None


def get_all_posts() -> List[Dict[str, Any]]:
    """
    Obtiene todos los posts de la base de datos.
    """
    with get_db_session() as session:
        posts = session.query(Post).order_by(Post.id.desc()).all()
        return [model_to_dict(post) for post in posts]


def get_post_by_id(post_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene un post por su ID.
    """
    with get_db_session() as session:
        post = session.query(Post).filter(Post.id == post_id).first()
        return model_to_dict(post) if post else None


def create_post(title: Optional[str], content: str, platform: str, asunto: Optional[str] = None,
                content_html: Optional[str] = None, contacts: Optional[List[str]] = None, fecha_hora: Optional[str] = None) -> int:
    """
    Crea un nuevo post (solo texto). Los medios se enlazan por separado.
    """
    with get_db_session() as session:
        now = datetime.now().isoformat()
        post_title = title.strip() if title and title.strip() else f"Post sin título para {platform} - {now}"

        post = Post(
            title=post_title, content=content, asunto=asunto, platform=platform,
            content_html=content_html,
            contacts=serialize_list(contacts), fecha_hora=fecha_hora,
            created_at=now, updated_at=now
        )
        session.add(post)
        session.commit()
        session.refresh(post)
        return post.id


def update_post(post_id: int, **kwargs) -> bool:
    """
    Actualiza los campos de un post. La gestión de medios se hace por separado.
    """
    with get_db_session() as session:
        post = session.query(Post).filter(Post.id == post_id).first()
        if not post: return False

        for key, value in kwargs.items():
            if hasattr(post, key):
                if key == "contacts" and value is not None:
                    value = serialize_list(value)
                setattr(post, key, value)

        post.updated_at = datetime.now().isoformat()
        session.commit()
        return True


def delete_post(post_id: int) -> bool:
    """
    Elimina un post y sus activos de medios si ya no están en uso por otros posts.
    """
    with get_db_session() as session:
        post = session.query(Post).filter(Post.id == post_id).first()
        if not post: return False

        assets_to_check = list(post.media_assets)
        session.delete(post)
        session.commit()

        for asset in assets_to_check:
            asset_in_db = session.query(MediaAsset).filter(MediaAsset.id == asset.id).first()
            if asset_in_db and not asset_in_db.posts:
                session.delete(asset_in_db)
                logger.info(f"Registro de MediaAsset eliminado: ID {asset.id}")

        session.commit()
        return True


def create_media_asset(file_path: str, file_type: str, original_filename: str = None) -> Dict[str, Any]:
    """
    Añade un nuevo activo a la biblioteca de medios. Si ya existe, lo devuelve.
    Devuelve un diccionario con los datos.
    """
    with get_db_session() as session:
        existing_asset = session.query(MediaAsset).filter_by(file_path=file_path).first()
        if existing_asset:
            # Si ya existe, devolver sus datos como un diccionario
            return {
                "id": existing_asset.id,
                "file_path": existing_asset.file_path,
                "file_type": existing_asset.file_type,
                "original_filename": existing_asset.original_filename
            }

        # Si no existe, crear uno nuevo
        asset = MediaAsset(
            file_path=file_path,
            file_type=file_type,
            original_filename=original_filename
        )
        session.add(asset)
        session.flush()  # flush para obtener el ID asignado por la BD

        asset_data = {
            "id": asset.id,
            "file_path": asset.file_path,
            "file_type": asset.file_type,
            "original_filename": asset.original_filename
        }

        # El commit() se gestiona automáticamente al salir del 'with'.

        return asset_data


def link_media_to_post(post_id: int, media_ids: List[int]):
    """
    Asocia una lista de activos de medios a un post, reemplazando las asociaciones anteriores.
    """
    with get_db_session() as session:
        post = session.query(Post).filter(Post.id == post_id).first()
        if not post: return

        # Limpiar asociaciones antiguas
        post.media_assets.clear()

        # Añadir nuevas asociaciones
        if media_ids:
            assets = session.query(MediaAsset).filter(MediaAsset.id.in_(media_ids)).all()
            post.media_assets.extend(assets)

        session.commit()


def get_asset_ids_from_paths(file_paths: List[str]) -> List[int]:
    """
    Busca MediaAssets por su ruta y devuelve una lista de sus IDs.
    """

    if not file_paths: return []
    with get_db_session() as session:
        assets = session.query(MediaAsset).filter(MediaAsset.file_path.in_(file_paths)).all()
        return [asset.id for asset in assets]


def get_all_media_assets() -> List[Dict[str, Any]]:
    """
    Obtiene todos los activos de medios de la base de datos.
    """
    with get_db_session() as session:
        assets = session.query(MediaAsset).order_by(MediaAsset.created_at.desc()).all()
        return [
            {"id": asset.id, "file_path": asset.file_path, "file_type": asset.file_type,
             "original_filename": asset.original_filename}
            for asset in assets
        ]


def delete_media_asset(asset_id: int) -> bool:
    """
    Elimina un registro de MediaAsset de la base de datos por su ID.
    Esta función está diseñada para ser llamada por el script de limpieza,
    asumiendo que el fichero físico ya no existe.
    """
    with get_db_session() as session:
        try:
            # Buscar el activo por su ID
            asset = session.query(MediaAsset).filter(MediaAsset.id == asset_id).first()

            if not asset:
                logger.warning(f"Se intentó eliminar el MediaAsset con ID {asset_id}, pero no se encontró.")
                return False

            # Eliminar el registro de la base de datos
            session.delete(asset)
            # El commit se gestiona automáticamente por el context manager get_db_session

            return True
        except Exception as e:
            logger.error(f"Error al eliminar el MediaAsset con ID {asset_id}: {e}")
            # El rollback se gestiona automáticamente
            return False


def get_programmed_posts_raw() -> List[Dict[str, Any]]:
    """
    Obtiene los posts que tienen una fecha de programación y no han sido enviados.
    """
    with get_db_session() as session:
        posts = session.query(Post).filter(
            Post.fecha_hora.isnot(None),
            Post.sent_at.is_(None)
        ).order_by(Post.fecha_hora.asc()).all()
        return [model_to_dict(post) for post in posts]


def get_programmed_posts_by_platform(platform: str) -> List[Dict[str, Any]]:
    """
    Obtiene los posts programados para una plataforma específica.
    """
    with get_db_session() as session:
        posts = session.query(Post).filter(
            Post.platform == platform,
            Post.fecha_hora.isnot(None)
        ).order_by(Post.fecha_hora.asc()).all()
        return [model_to_dict(post) for post in posts]


def get_unprogrammed_posts_raw() -> List[Dict[str, Any]]:
    """
    Obtiene los posts guardados que no tienen fecha de programación.
    """
    with get_db_session() as session:
        posts = session.query(Post).filter(Post.fecha_hora.is_(None)).order_by(Post.updated_at.desc()).all()
        return [model_to_dict(post) for post in posts]


@st.cache_data(ttl=60)
def get_programmed_posts() -> List[Dict[str, Any]]:
    """Versión cacheada de get_programmed_posts_raw para la UI."""
    return get_programmed_posts_raw()


@st.cache_data(ttl=60)
def get_unprogrammed_posts() -> List[Dict[str, Any]]:
    """Versión cacheada de get_unprogrammed_posts_raw para la UI."""
    return get_unprogrammed_posts_raw()


def get_unprogrammed_posts_by_platform(platform: str) -> List[Dict[str, Any]]:
    """
    Obtiene los posts no programados para una plataforma específica.
    """
    with get_db_session() as session:
        posts = session.query(Post).filter(
            Post.platform == platform,
            Post.fecha_hora.is_(None)
        ).order_by(Post.updated_at.desc()).all()
        return [model_to_dict(post) for post in posts]


def get_sent_posts_raw() -> List[Dict[str, Any]]:
    """
    Obtiene todos los posts que han sido enviados (tienen sent_at no nulo).
    """
    with get_db_session() as session:
        posts = session.query(Post).filter(Post.sent_at.isnot(None)).order_by(Post.sent_at.desc()).all()
        return [model_to_dict(post) for post in posts]


@st.cache_data(ttl=60)
def get_sent_posts() -> List[Dict[str, Any]]:
    """Versión cacheada de get_sent_posts_raw para la UI."""
    return get_sent_posts_raw()


def get_sent_posts_by_platform(platform: str) -> List[Dict[str, Any]]:
    """
    Obtiene los posts enviados para una plataforma específica.
    """
    with get_db_session() as session:
        posts = session.query(Post).filter(
            Post.platform == platform,
            Post.sent_at.isnot(None)
        ).order_by(Post.sent_at.desc()).all()
        return [model_to_dict(post) for post in posts]



if __name__ == '__main__':
    # Ejecuta esta línea una vez para crear la base de datos y las tablas
    print("Inicializando la base de datos...")
    init_db()
    print("Base de datos inicializada correctamente.")
