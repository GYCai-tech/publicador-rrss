import os
import logging
from src.db_config import get_all_media_assets, delete_media_asset

# Configuración de logging para este script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MediaCleanup')


def find_and_delete_orphan_assets():
    """
    Busca en la base de datos activos de medios cuyos ficheros ya no existen
    en el disco y los elimina de la base de datos.
    """
    logger.info("Iniciando escaneo de la biblioteca de medios en busca de huérfanos...")

    # Obtener todos los activos de la base de datos
    all_assets = get_all_media_assets()

    if not all_assets:
        logger.info("La biblioteca de medios está vacía. No hay nada que limpiar.")
        return

    orphan_count = 0
    total_assets = len(all_assets)

    logger.info(f"Verificando {total_assets} activos de medios...")

    # Iterar sobre cada uno y comprobar si el fichero existe
    for asset in all_assets:
        file_path = asset.get('file_path')
        asset_id = asset.get('id')

        if not file_path or not asset_id:
            continue

        if not os.path.exists(file_path):
            logger.warning(f"FICHERO NO ENCONTRADO: {file_path}. Eliminando registro ID: {asset_id} de la base de datos.")

            # Si no existe, eliminar el registro de la BD
            success = delete_media_asset(asset_id)
            if success:
                logger.info(f"Registro ID {asset_id} eliminado con éxito.")
                orphan_count += 1
            else:
                logger.error(f"Fallo al intentar eliminar el registro ID {asset_id}.")

    if orphan_count > 0:
        logger.info(f"Limpieza completada. Se han eliminado {orphan_count} registros huérfanos.")
    else:
        logger.info("Análisis completado. No se encontraron registros huérfanos. ¡La base de datos está limpia!")


if __name__ == "__main__":
    find_and_delete_orphan_assets()
