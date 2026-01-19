import sys
import os
import logging

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from dotenv import load_dotenv

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_organizations():
    """Obtiene las organizaciones donde el usuario tiene permisos de administrador."""
    load_dotenv()
    access_token = os.getenv("ACCESS_TOKEN_LINKEDIN")

    if not access_token:
        logger.error("❌ No se encontró ACCESS_TOKEN_LINKEDIN en el archivo .env")
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        # Primero obtener el ID del usuario
        logger.info("🔍 Obteniendo información del usuario...")
        user_response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
        user_response.raise_for_status()
        user_info = user_response.json()
        user_id = user_info.get('sub')

        print("\n" + "="*70)
        print("👤 INFORMACIÓN DEL USUARIO")
        print("="*70)
        print(f"Nombre: {user_info.get('name', 'N/A')}")
        print(f"ID: {user_id}")
        print(f"URN: urn:li:person:{user_id}")

        # Intentar obtener organizaciones administradas
        logger.info("\n🏢 Buscando páginas de empresa administradas...")

        # Endpoint para obtener organizaciones (requiere permiso w_organization_social o r_organization_social)
        org_url = f"https://api.linkedin.com/v2/organizationAcls?q=roleAssignee&role=ADMINISTRATOR&projection=(elements*(organization~(localizedName,vanityName),organizationalTarget))"

        org_response = requests.get(org_url, headers=headers)

        if org_response.status_code == 403:
            print("\n" + "="*70)
            print("⚠️  PERMISOS INSUFICIENTES")
            print("="*70)
            print("El token actual no tiene permisos para listar organizaciones.")
            print("Esto es normal si tu token solo tiene permisos de perfil personal.")
            print("\n📋 OPCIONES PARA OBTENER EL ID DE LA ORGANIZACIÓN:")
            print("-"*70)
            print("\n1️⃣  Desde la URL de la página de LinkedIn:")
            print("   - Ve a la página de tu empresa en LinkedIn")
            print("   - La URL será algo como: linkedin.com/company/XXXXXXXX")
            print("   - El número XXXXXXXX es el ID de la organización")
            print("\n2️⃣  Desde el panel de administración:")
            print("   - Ve a la página como administrador")
            print("   - El ID aparece en la configuración de la página")
            print("\n3️⃣  Generar un nuevo token con permisos de organización:")
            print("   - En LinkedIn Developers, solicita el permiso 'w_organization_social'")
            print("   - Genera un nuevo token y ejecútame de nuevo")
            print("="*70 + "\n")
            return

        org_response.raise_for_status()
        org_data = org_response.json()

        organizations = org_data.get('elements', [])

        if not organizations:
            print("\n" + "="*70)
            print("📭 NO SE ENCONTRARON ORGANIZACIONES")
            print("="*70)
            print("No se encontraron páginas de empresa donde seas administrador.")
            print("\nVerifica que:")
            print("  1. Tu usuario es administrador de la página")
            print("  2. El token tiene los permisos correctos (w_organization_social)")
            print("="*70 + "\n")
            return

        print("\n" + "="*70)
        print("🏢 PÁGINAS DE EMPRESA ADMINISTRADAS")
        print("="*70)

        for i, org in enumerate(organizations, 1):
            org_info = org.get('organization~', {})
            org_urn = org.get('organization', '')
            org_id = org_urn.split(':')[-1] if org_urn else 'N/A'

            print(f"\n{i}. {org_info.get('localizedName', 'Sin nombre')}")
            print(f"   URL: linkedin.com/company/{org_info.get('vanityName', org_id)}")
            print(f"   ID de Organización: {org_id}")
            print(f"   URN: {org_urn}")

        print("\n" + "="*70)
        print("📝 INSTRUCCIONES:")
        print("="*70)
        print("Para publicar en una página de empresa, agrega esta línea al .env:")
        print(f"\nLINKEDIN_ORGANIZATION_ID=ID_DE_TU_ORGANIZACION")
        print("\nReemplaza ID_DE_TU_ORGANIZACION con el ID numérico de tu página")
        print("="*70 + "\n")

    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ ERROR: {e.response.status_code}")
        logger.error(f"Detalles: {e.response.text}")
    except Exception as e:
        logger.error(f"❌ ERROR inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    get_organizations()
