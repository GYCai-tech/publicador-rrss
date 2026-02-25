#!/usr/bin/env python3
"""
Script para migrar datos de SQLite a PostgreSQL.
Uso: python scripts/migrate_sqlite_to_postgres.py
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from src.db_config import Base, Post, MediaAsset, Contact, ContactList, EmailSendLog, EmailSendResult
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_data():
    """Migra datos de SQLite a PostgreSQL."""

    load_dotenv()

    # Conexión a SQLite (origen)
    sqlite_path = os.path.join("data", "posts.db")

    if not os.path.exists(sqlite_path):
        logger.error(f"❌ No se encontró la base de datos SQLite en {sqlite_path}")
        return False

    sqlite_url = f"sqlite:///{sqlite_path}"
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    SqliteSession = sessionmaker(bind=sqlite_engine)

    # Conexión a PostgreSQL (destino)
    POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme123")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "publicador_rrss")

    postgres_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    try:
        postgres_engine = create_engine(postgres_url, pool_pre_ping=True)

        # Test de conexión
        with postgres_engine.connect() as conn:
            logger.info(f"✅ Conectado a PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

        PostgresSession = sessionmaker(bind=postgres_engine)

    except Exception as e:
        logger.error(f"❌ Error conectando a PostgreSQL: {e}")
        logger.error("Asegúrate de que PostgreSQL esté corriendo y las credenciales sean correctas")
        return False

    # Crear tablas en PostgreSQL
    logger.info("📊 Creando tablas en PostgreSQL...")
    Base.metadata.create_all(postgres_engine)
    logger.info("✅ Tablas creadas")

    # Inspeccionar tablas en SQLite
    inspector = inspect(sqlite_engine)
    tables = inspector.get_table_names()

    logger.info(f"📋 Tablas encontradas en SQLite: {tables}")

    sqlite_session = SqliteSession()
    postgres_session = PostgresSession()

    try:
        # Migrar MediaAssets primero (sin dependencias)
        logger.info("\n🖼️  Migrando MediaAssets...")
        media_assets = sqlite_session.query(MediaAsset).all()
        for media in media_assets:
            # Crear nuevo objeto sin ID (PostgreSQL lo generará)
            new_media = MediaAsset(
                file_path=media.file_path,
                file_type=media.file_type,
                original_filename=media.original_filename,
                created_at=media.created_at
            )
            postgres_session.add(new_media)
        postgres_session.commit()
        logger.info(f"✅ {len(media_assets)} MediaAssets migrados")

        # Migrar ContactLists
        logger.info("\n📋 Migrando ContactLists...")
        contact_lists = sqlite_session.query(ContactList).all()
        for lst in contact_lists:
            new_list = ContactList(
                name=lst.name,
                created_at=lst.created_at
            )
            postgres_session.add(new_list)
        postgres_session.commit()
        logger.info(f"✅ {len(contact_lists)} ContactLists migrados")

        # Migrar Contacts
        logger.info("\n👥 Migrando Contacts...")
        contacts = sqlite_session.query(Contact).all()
        for contact in contacts:
            new_contact = Contact(
                name=contact.name,
                phone=contact.phone,
                email=contact.email
            )
            # Copiar relaciones con listas
            for lst in contact.lists:
                # Buscar la lista correspondiente en PostgreSQL
                pg_list = postgres_session.query(ContactList).filter_by(name=lst.name).first()
                if pg_list:
                    new_contact.lists.append(pg_list)

            postgres_session.add(new_contact)
        postgres_session.commit()
        logger.info(f"✅ {len(contacts)} Contacts migrados")

        # Migrar Posts
        logger.info("\n📝 Migrando Posts...")
        posts = sqlite_session.query(Post).all()
        for post in posts:
            new_post = Post(
                title=post.title,
                content=post.content,
                content_html=post.content_html,
                asunto=post.asunto,
                platform=post.platform,
                fecha_hora=post.fecha_hora,
                sent_at=post.sent_at,
                contacts=post.contacts,
                created_at=post.created_at,
                updated_at=post.updated_at
            )

            # Copiar relaciones con media
            for media in post.media_assets:
                # Buscar el media correspondiente en PostgreSQL
                pg_media = postgres_session.query(MediaAsset).filter_by(
                    file_path=media.file_path
                ).first()
                if pg_media:
                    new_post.media_assets.append(pg_media)

            postgres_session.add(new_post)
        postgres_session.commit()
        logger.info(f"✅ {len(posts)} Posts migrados")

        # Migrar EmailSendLogs
        logger.info("\n📧 Migrando EmailSendLogs...")
        email_logs = sqlite_session.query(EmailSendLog).all()
        for log in email_logs:
            new_log = EmailSendLog(
                post_id=log.post_id,
                platform=log.platform,
                subject=log.subject,
                total_recipients=log.total_recipients,
                successful_count=log.successful_count,
                failed_count=log.failed_count,
                started_at=log.started_at,
                completed_at=log.completed_at
            )
            postgres_session.add(new_log)
        postgres_session.commit()
        logger.info(f"✅ {len(email_logs)} EmailSendLogs migrados")

        # Migrar EmailSendResults
        logger.info("\n📨 Migrando EmailSendResults...")
        email_results = sqlite_session.query(EmailSendResult).all()
        for result in email_results:
            # Buscar el log correspondiente en PostgreSQL
            pg_log = postgres_session.query(EmailSendLog).filter_by(
                started_at=result.send_log.started_at
            ).first()

            if pg_log:
                new_result = EmailSendResult(
                    send_log_id=pg_log.id,
                    recipient_email=result.recipient_email,
                    success=result.success,
                    error_code=result.error_code,
                    error_message=result.error_message,
                    sent_at=result.sent_at
                )
                postgres_session.add(new_result)
        postgres_session.commit()
        logger.info(f"✅ {len(email_results)} EmailSendResults migrados")

        logger.info("\n" + "="*60)
        logger.info("🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
        logger.info("="*60)
        logger.info(f"\n✅ Datos migrados de SQLite a PostgreSQL")
        logger.info(f"   SQLite: {sqlite_path}")
        logger.info(f"   PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        logger.info(f"\n📊 Resumen:")
        logger.info(f"   - {len(media_assets)} MediaAssets")
        logger.info(f"   - {len(contact_lists)} ContactLists")
        logger.info(f"   - {len(contacts)} Contacts")
        logger.info(f"   - {len(posts)} Posts")
        logger.info(f"   - {len(email_logs)} EmailSendLogs")
        logger.info(f"   - {len(email_results)} EmailSendResults")
        logger.info("\n💡 Próximos pasos:")
        logger.info("   1. Verifica que los datos estén correctos en PostgreSQL")
        logger.info("   2. Actualiza tu archivo .env con USE_POSTGRES='true'")
        logger.info("   3. Reinicia la aplicación Streamlit")
        logger.info("   4. Opcionalmente, haz backup de data/posts.db antes de eliminarlo\n")

        return True

    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        postgres_session.rollback()
        return False

    finally:
        sqlite_session.close()
        postgres_session.close()

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🔄 MIGRACIÓN DE SQLITE A POSTGRESQL")
    logger.info("="*60)
    logger.info("\n⚠️  IMPORTANTE: Asegúrate de que PostgreSQL esté corriendo")
    logger.info("   Docker: docker-compose up -d postgres")
    logger.info("   Local: sudo service postgresql start\n")

    input("Presiona ENTER para continuar...")

    success = migrate_data()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)
