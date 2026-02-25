#!/usr/bin/env python3
"""
Script para actualizar automáticamente las métricas de LinkedIn en la base de datos.
Se ejecuta como servicio en Docker o puede correrse manualmente.

Uso:
    python scripts/auto_analytics.py
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.linkedin import LinkedInClient
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_analytics.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuración de base de datos
Base = declarative_base()

class LinkedInMetric(Base):
    """Tabla para almacenar métricas históricas de LinkedIn."""
    __tablename__ = 'linkedin_metrics'

    id = Column(Integer, primary_key=True)
    post_id = Column(String(255), nullable=False, index=True)
    post_date = Column(DateTime, nullable=True)
    post_text = Column(Text, nullable=True)
    post_type = Column(String(50), nullable=True)

    # Métricas
    impresiones = Column(Integer, default=0)
    clics = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comentarios = Column(Integer, default=0)
    compartidos = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)

    # Metadata
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<LinkedInMetric(post_id='{self.post_id}', impresiones={self.impresiones}, ER={self.engagement_rate}%)>"


class LinkedInFollowerMetric(Base):
    """Tabla para almacenar crecimiento de seguidores."""
    __tablename__ = 'linkedin_follower_metrics'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    ganancia_organica = Column(Integer, default=0)
    ganancia_pagada = Column(Integer, default=0)
    ganancia_total = Column(Integer, default=0)
    seguidores_totales = Column(Integer, nullable=True)

    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<LinkedInFollowerMetric(date='{self.date}', ganancia={self.ganancia_total})>"


def get_database_engine():
    """Obtiene el engine de la base de datos según configuración."""
    USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"

    if USE_POSTGRES:
        POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
        POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme123")
        POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
        POSTGRES_DB = os.getenv("POSTGRES_DB", "publicador_rrss")

        DB_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        engine = create_engine(DB_URL, pool_pre_ping=True)
        logger.info(f"✅ Conectado a PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    else:
        DB_DIR = "data"
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
        DB_URL = f"sqlite:///{os.path.join(DB_DIR, 'posts.db')}"
        engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
        logger.info(f"✅ Conectado a SQLite: {DB_URL}")

    return engine


def collect_linkedin_metrics(api_client, session, num_posts=50):
    """
    Recopila métricas de los posts recientes de LinkedIn y las guarda en la BD.

    Args:
        api_client: Instancia de LinkedInClient
        session: Sesión de SQLAlchemy
        num_posts: Número de posts recientes a analizar
    """
    logger.info(f"📊 Recopilando métricas de los últimos {num_posts} posts...")

    try:
        # Obtener posts recientes con detalles
        posts_data = api_client.get_recent_posts_details(count=num_posts)

        if not posts_data:
            logger.warning("⚠️  No se encontraron posts recientes")
            return 0

        post_ids = [p['post_id'] for p in posts_data]

        # Obtener métricas
        df_metrics = api_client.get_post_metrics(post_ids)

        if df_metrics is None or df_metrics.empty:
            logger.warning("⚠️  No se pudieron obtener métricas")
            return 0

        # Guardar cada métrica en la base de datos
        metrics_saved = 0
        metrics_updated = 0

        for post in posts_data:
            post_id = post['post_id']

            # Buscar métricas correspondientes
            metrics_row = df_metrics[df_metrics['post_id'] == post_id]

            if metrics_row.empty:
                continue

            metrics = metrics_row.iloc[0]

            # Verificar si ya existe este post en la BD
            existing_metric = session.query(LinkedInMetric).filter_by(
                post_id=post_id
            ).order_by(LinkedInMetric.collected_at.desc()).first()

            # Parsear fecha del post
            post_date = None
            if post.get('fecha'):
                try:
                    from datetime import datetime as dt
                    post_date = dt.strptime(post['fecha'], '%Y-%m-%d %H:%M')
                except:
                    pass

            # Crear nuevo registro de métrica
            new_metric = LinkedInMetric(
                post_id=post_id,
                post_date=post_date,
                post_text=post.get('texto_completo', post.get('texto_corto', '')),
                post_type=post.get('tipo', 'Desconocido'),
                impresiones=int(metrics.get('impresiones', 0)),
                clics=int(metrics.get('clics', 0)),
                likes=int(metrics.get('likes', 0)),
                comentarios=int(metrics.get('comentarios', 0)),
                compartidos=int(metrics.get('compartidos', 0)),
                engagement_rate=float(metrics.get('ER%', 0.0))
            )

            session.add(new_metric)
            metrics_saved += 1

            # Logging detallado
            if existing_metric:
                # Comparar con métrica anterior
                impr_diff = new_metric.impresiones - existing_metric.impresiones
                logger.info(
                    f"📝 Post {post_id[:20]}... actualizado: "
                    f"{new_metric.impresiones} impresiones (+{impr_diff}), "
                    f"ER: {new_metric.engagement_rate:.2f}%"
                )
                metrics_updated += 1
            else:
                logger.info(
                    f"✨ Nuevo post detectado: {post_id[:20]}... "
                    f"{new_metric.impresiones} impresiones, "
                    f"ER: {new_metric.engagement_rate:.2f}%"
                )

        session.commit()

        logger.info(f"✅ Métricas guardadas: {metrics_saved} nuevos registros")
        logger.info(f"🔄 Posts actualizados: {metrics_updated}")

        return metrics_saved

    except Exception as e:
        logger.error(f"❌ Error recopilando métricas: {e}")
        session.rollback()
        return 0


def collect_follower_growth(api_client, session, days=7):
    """
    Recopila datos de crecimiento de seguidores.

    Args:
        api_client: Instancia de LinkedInClient
        session: Sesión de SQLAlchemy
        days: Número de días hacia atrás para analizar
    """
    logger.info(f"📈 Recopilando crecimiento de seguidores (últimos {days} días)...")

    try:
        df_growth = api_client.get_follower_growth(days=days)

        if df_growth is None or df_growth.empty:
            logger.warning("⚠️  No se pudieron obtener datos de crecimiento")
            return 0

        records_saved = 0

        for _, row in df_growth.iterrows():
            fecha = row['fecha']

            # Verificar si ya existe este día
            existing = session.query(LinkedInFollowerMetric).filter_by(
                date=fecha
            ).first()

            if existing:
                # Actualizar
                existing.ganancia_organica = int(row['ganancia_organica'])
                existing.ganancia_pagada = int(row['ganancia_pagada'])
                existing.ganancia_total = int(row['ganancia_total'])
                existing.collected_at = datetime.utcnow()
            else:
                # Crear nuevo
                new_record = LinkedInFollowerMetric(
                    date=fecha,
                    ganancia_organica=int(row['ganancia_organica']),
                    ganancia_pagada=int(row['ganancia_pagada']),
                    ganancia_total=int(row['ganancia_total'])
                )
                session.add(new_record)
                records_saved += 1

        session.commit()

        logger.info(f"✅ Datos de seguidores guardados: {records_saved} registros")

        return records_saved

    except Exception as e:
        logger.error(f"❌ Error recopilando datos de seguidores: {e}")
        session.rollback()
        return 0


def run_analytics_cycle():
    """Ejecuta un ciclo completo de recopilación de analytics."""
    try:
        # Inicializar cliente de LinkedIn
        api = LinkedInClient()

        # Obtener engine de base de datos
        engine = get_database_engine()

        # Crear tablas si no existen
        Base.metadata.create_all(engine)

        # Crear sesión
        Session = sessionmaker(bind=engine)
        session = Session()

        logger.info("\n" + "="*60)
        logger.info("🚀 INICIANDO RECOPILACIÓN DE MÉTRICAS")
        logger.info("="*60)

        # Recopilar métricas de posts
        posts_collected = collect_linkedin_metrics(api, session, num_posts=30)

        # Recopilar crecimiento de seguidores
        followers_collected = collect_follower_growth(api, session, days=7)

        session.close()

        logger.info("\n" + "="*60)
        logger.info("✅ CICLO DE RECOPILACIÓN COMPLETADO")
        logger.info(f"   - Posts analizados: {posts_collected}")
        logger.info(f"   - Días de seguidores: {followers_collected}")
        logger.info("="*60 + "\n")

        return True

    except Exception as e:
        logger.error(f"❌ Error en ciclo de analytics: {e}")
        return False


def main():
    """Función principal que corre en loop continuo."""

    # Obtener intervalo de actualización (en segundos)
    interval = int(os.getenv("AUTO_ANALYTICS_INTERVAL", "3600"))  # Default: 1 hora

    logger.info("="*60)
    logger.info("🤖 AUTO ANALYTICS - SERVICIO INICIADO")
    logger.info("="*60)
    logger.info(f"📊 Intervalo de actualización: {interval} segundos ({interval/60:.1f} minutos)")
    logger.info(f"⏰ Próxima ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    while True:
        try:
            # Ejecutar ciclo de recopilación
            run_analytics_cycle()

            # Esperar hasta la próxima ejecución
            next_run = datetime.now() + timedelta(seconds=interval)
            logger.info(f"⏳ Esperando hasta {next_run.strftime('%Y-%m-%d %H:%M:%S')}...")

            time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("\n⚠️  Servicio detenido por el usuario")
            break
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            logger.info("⏳ Esperando 5 minutos antes de reintentar...")
            time.sleep(300)  # Esperar 5 minutos antes de reintentar


if __name__ == "__main__":
    main()
