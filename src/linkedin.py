import os
import requests
import json
from dotenv import load_dotenv
import logging
import pandas as pd
import urllib.parse

# Logger
logger = logging.getLogger(__name__)


class LinkedInClient:
    """
    Cliente para interactuar con la API de LinkedIn v2 para crear publicaciones.
    Maneja la publicación de texto, imágenes (única o carrusel) y vídeo.
    Soporta publicaciones en perfiles personales y páginas de empresa.
    """

    def __init__(self):
        load_dotenv()
        self.access_token = os.getenv("ACCESS_TOKEN_LINKEDIN")
        if not self.access_token:
            logger.critical("❌ ERROR CRÍTICO: No se pudo cargar ACCESS_TOKEN_LINKEDIN desde el archivo .env.")
            raise ValueError("El token de acceso de LinkedIn no está configurado.")

        self.api_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202601"
        }

        # Verificar si se debe publicar en una página de empresa u organización
        self.organization_id = os.getenv("LINKEDIN_ORGANIZATION_ID")
        self.base_url = "https://api.linkedin.com/rest"
        if self.organization_id:
            # Publicar en página de empresa
            self.author_urn = f"urn:li:organization:{self.organization_id}"
            self.is_organization = True
            logger.info(f"✅ Configurado para publicar en página de empresa: {self.author_urn}")
        else:
            # Publicar en perfil personal
            self.author_urn = self._get_user_urn()
            self.is_organization = False

        self.post_visibility = os.getenv("POST_VISIBILITY", "PUBLIC")

    def _get_user_urn(self):
        """Obtiene el URN del usuario autenticado (perfil personal)."""
        logger.info("Obteniendo URN de usuario de LinkedIn...")
        try:
            response = requests.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {self.access_token}"})
            response.raise_for_status()
            user_info = response.json()
            user_urn = f"urn:li:person:{user_info['sub']}"
            logger.info(f"✅ URN de usuario obtenido: {user_urn}")
            return user_urn
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ ERROR al obtener el URN de LinkedIn: {e.response.status_code} - {e.response.text}")
            raise

    def _register_asset(self, is_video=False):
        """Registra un asset (imagen/video) y obtiene la URL de subida."""
        logger.info(f"Registrando nuevo asset ({'VIDEO' if is_video else 'IMAGE'})...")
        asset_type = "VIDEO" if is_video else "IMAGE"
        payload = {
            "registerUploadRequest": {
                "recipes": [f"urn:li:digitalmediaRecipe:feedshare-{asset_type.lower()}"],
                "owner": self.author_urn,
                "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}]
            }
        }
        try:
            response = requests.post("https://api.linkedin.com/v2/assets?action=registerUpload", headers=self.api_headers, json=payload)
            response.raise_for_status()
            data = response.json()
            upload_url = data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset_urn = data['value']['asset']
            logger.info(f"✅ Asset registrado con éxito. URN: {asset_urn}")
            return asset_urn, upload_url
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ ERROR al registrar el asset en LinkedIn: {e.response.status_code} - {e.response.text}")
            raise

    def _upload_file(self, upload_url, file_path):
        """Sube el contenido binario del fichero a la URL de subida."""
        logger.info(f"Subiendo fichero: {file_path}...")
        try:
            with open(file_path, 'rb') as f:
                headers = {'Content-Type': 'application/octet-stream'}
                response = requests.put(upload_url, headers=headers, data=f)
                response.raise_for_status()
                logger.info(f"✅ Fichero subido correctamente (Status: {response.status_code}).")
        except FileNotFoundError:
            logger.error(f"❌ ERROR: Fichero no encontrado en {file_path}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ ERROR al subir el fichero a LinkedIn: {e.response.status_code} - {e.response.text}")
            raise

    def post(self, text: str, image_paths: list = None, video_path: str = None):
        """Crea una nueva publicación en LinkedIn.
        - Si no se proporcionan medios, publica solo texto.
        - Si se proporciona video_path, publica el vídeo (ignora image_paths).
        - Si se proporcionan image_paths, publica las imágenes.
        """
        logger.info("Iniciando proceso de publicación en LinkedIn...")

        # Publicación con vídeo
        if video_path:
            logger.info("Tipo de publicación: VÍDEO")
            asset_urn, upload_url = self._register_asset(is_video=True)
            self._upload_file(upload_url, video_path)
            media_category = "VIDEO"
            media_list = [{"status": "READY", "media": asset_urn}]

        # Publicación con imágenes
        elif image_paths:
            logger.info(f"Tipo de publicación: IMAGEN ({len(image_paths)} ficheros)")
            asset_urns = []
            for path in image_paths:
                asset_urn, upload_url = self._register_asset(is_video=False)
                self._upload_file(upload_url, path)
                asset_urns.append(asset_urn)
            media_category = "IMAGE"
            media_list = [{"status": "READY", "media": urn} for urn in asset_urns]

        # Solo texto
        else:
            logger.info("Tipo de publicación: TEXTO")
            media_category = "NONE"
            media_list = []

        # Payload de la publicación
        payload = {
            "author": self.author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": media_category
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": self.post_visibility}
        }

        # Para organizaciones, usar PUBLIC en lugar de MemberNetworkVisibility si es necesario
        if self.is_organization and self.post_visibility == "PUBLIC":
            payload["visibility"] = {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}

        # Añadir la clave "media" solo si hay medios
        if media_list:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_list

        logger.info("Enviando payload final a LinkedIn...")
        try:
            response = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=self.api_headers, data=json.dumps(payload))
            response.raise_for_status()
            logger.info("🎉 ¡Publicación en LinkedIn realizada con éxito!")
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ ERROR al crear la publicación final en LinkedIn: {e.response.status_code} - {e.response.text}")
            raise

    def get_page_metrics(self):
        logger.info("Obteniendo métricas de la página...")
        try:
            url = f"{self.base_url}/organizationalEntityShareStatistics"
            query_params = {
                "q": "organizationalEntity",
                "organizationalEntity": self.author_urn
            }

            response = requests.get(url, headers=self.api_headers, params=query_params)

            if response.status_code == 200:
                logger.info("✅ Petición exitosa a LinkedIn")
                elements = response.json().get('elements', [])
                data = []
                for item in elements:

                    stats = item.get('totalShareStatistics', {})
                    
                    data.append({
                        'fecha': pd.to_datetime(item['timeRange']['start'], unit='ms').date(),
                        'impresiones': stats.get('impressionCount', 0),
                        'clics': stats.get('clickCount', 0),
                        'likes': stats.get("likeCount", 0),
                        'comentarios': stats.get("commentCount", 0),
                        'compartidos': stats.get("shareCount", 0),
                        'engagement': stats.get("engagement", 0) 
                    })
                return pd.DataFrame(data)
            else:
                logger.error(f"❌ ERROR: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"🔥 Error inesperado: {e}")
            return None

    
    def get_recent_posts(self,count=10):
        logger.info("Obteniendo publicaciones recientes...")

        url=f"{self.base_url}/posts"
        params={
            "q":"author",
            "author":self.author_urn,
            "count":count
            }
        try:
            response = requests.get(url,headers=self.api_headers,params=params)
            if response.status_code==200:
                elements=response.json().get('elements',[])
                urns = [post['id'] for post in elements]
                logger.info(f"✅ Se han encontrado {len(urns)} posts recientes.")
                return urns
            else:
                logger.error(f"❌ Error al listar posts: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"🔥 Error en get_recent_posts: {e}")
            return []




    def get_post_metrics(self, post_ids):
        """
        Obtiene métricas de rendimiento para una lista de posts.
        Codifica correctamente los URNs dentro de List() para evitar el Error 400.
        IMPORTANTE: Solo funciona con urn:li:share:XXX, NO con urn:li:ugcPost:XXX
        """
        if not post_ids:
            return None

        if isinstance(post_ids, str):
            post_ids = [post_ids]

        # FILTRAR: Solo procesar posts de tipo 'share', excluir 'ugcPost'
        # El endpoint organizationalEntityShareStatistics NO acepta ugcPost
        valid_post_ids = [pid for pid in post_ids if 'urn:li:share:' in pid]
        ugc_posts = [pid for pid in post_ids if 'urn:li:ugcPost:' in pid]

        if ugc_posts:
            logger.warning(f"⚠️ Se encontraron {len(ugc_posts)} posts de tipo ugcPost que NO se pueden procesar con este endpoint")
            logger.warning(f"   Posts ugcPost excluidos: {len(ugc_posts)}")

        if not valid_post_ids:
            logger.error("❌ No hay posts de tipo 'share' para procesar. Todos son ugcPost.")
            return None

        valid_post_ids = valid_post_ids[:20]

        logger.info(f"📊 Consultando métricas para {len(valid_post_ids)} publicaciones (tipo 'share')...")

        try:
            encoded_ids = [urllib.parse.quote(pid) for pid in valid_post_ids]
            shares_param = f"List({','.join(encoded_ids)})"

            url = (
                f"{self.base_url}/organizationalEntityShareStatistics"
                f"?q=organizationalEntity"
                f"&organizationalEntity={urllib.parse.quote(self.author_urn)}"
                f"&shares={shares_param}"
            )

            response = requests.get(url, headers=self.api_headers)

            if response.status_code == 200:
                elements = response.json().get('elements', [])
                data = []
                for item in elements:
                    stats = item.get('totalShareStatistics', {})
                    
                    imp = stats.get('impressionCount', 0)
                    cli = stats.get('clickCount', 0)
                    lik = stats.get('likeCount', 0)
                    com = stats.get('commentCount', 0)
                    sha = stats.get('shareCount', 0)
                    
                    er = ((lik + com + sha + cli) / imp * 100) if imp > 0 else 0

                    data.append({
                        'post_id': item.get('share'),
                        'impresiones': imp,
                        'clics': cli,
                        'likes': lik,
                        'comentarios': com,
                        'compartidos': sha,
                        'ER%': round(er, 2)
                    })
                return pd.DataFrame(data)
            else:
                logger.error(f"❌ Error {response.status_code}: {response.text}")
                logger.error(f"URL de fallo: {url}")
                return None

        except Exception as e:
            logger.error(f"🔥 Error en get_post_metrics: {e}")
            return None

    def get_follower_segmentation(self, pivot_type="SENIORITY"):
        """
        Obtiene segmentación por: SENIORITY, INDUSTRY, FUNCTION, COMPANY_SIZE, GEOGRAPHIC_AREA
        """
        logger.info(f"📊 Obteniendo segmentación por {pivot_type}...")
        url = f"{self.base_url}/organizationalEntityFollowerStatistics"
        
        # Eliminado "pivot" en params para evitar el error 400
        params = {
            "q": "organizationalEntity",
            "organizationalEntity": self.author_urn
        }

        # Diccionario para traducir los URNs a nombres legibles
        labels_map = {
            "urn:li:seniority:1": "Sin experiencia", "urn:li:seniority:2": "En prácticas",
            "urn:li:seniority:3": "Junior", "urn:li:seniority:4": "Associate",
            "urn:li:seniority:5": "Senior", "urn:li:seniority:6": "Manager",
            "urn:li:seniority:7": "Director", "urn:li:seniority:8": "VP",
            "urn:li:seniority:9": "CXO", "urn:li:seniority:10": "Socio",
            "urn:li:companySize:B": "1 empleado", "urn:li:companySize:C": "2-10 emp",
            "urn:li:companySize:D": "11-50 emp", "urn:li:companySize:E": "51-200 emp",
            "urn:li:companySize:F": "201-500 emp", "urn:li:companySize:G": "501-1000 emp",
            "urn:li:companySize:H": "1001-5000 emp", "urn:li:companySize:I": "5001-10.000 emp",
            "urn:li:companySize:J": "10.001+ emp",
            "urn:li:geo:90009796": "Greater Orense Area",
            "urn:li:geo:90009818": "Greater Vigo Metropolitan Area",
            "urn:li:geo:90009790": "Greater Madrid Metropolitan Area",
            "urn:li:geo:90009773": "Greater Ferrol Metropolitan Area",
            "urn:li:geo:90009789": "Greater Lugo Metropolitan Area",
            "urn:li:geo:90009761": "Greater Barcelona Metropolitan Area",
            "urn:li:geo:90009795": "Greater Murcia Metropolitan Area",
            "urn:li:geo:90009809": "Greater Santiago de Compostela Metropolitan Area",
            "urn:li:geo:90009810": "Greater Sevilla Metropolitan Area",
            "urn:li:geo:90009816": "Greater Valencia Metropolitan Area",
            "urn:li:geo:90009776": "Greater Gijón Metropolitan Area",
            "urn:li:geo:90009805": "Greater Salamanca Metropolitan Area",
            "urn:li:geo:90009791": "Greater Málaga Metropolitan Area",
            "urn:li:geo:90009787": "Greater Lerida Area",
            "urn:li:geo:90009756": "Greater Alicante Area",
            "urn:li:geo:90009830": "Cracow Metropolitan Area",
            "urn:li:geo:90010133": "Bogotá D.C. Metropolitan Area",
            "urn:li:geo:90009763": "Greater Bilbao Metropolitan Area",
            "urn:li:geo:90009786": "Greater León, Spain Area",
            "urn:li:geo:90009757": "Greater Almería Metropolitan Area",
            "urn:li:geo:90009899": "Santiago Metropolitan Area",
            "urn:li:geo:90010274": "Belgrade Metropolitan Area",
            "urn:li:geo:90009770": "Greater Córdoba, Spain Area",
            "urn:li:geo:90010142": "Medellín Metropolitan Area",
            "urn:li:geo:90010352": "Lisbon Metropolitan Area",
            "urn:li:geo:104332104": "Qingdao, Shandong, China",
            "urn:li:geo:106486848": "Águilas, Región de Murcia, Spain",
            "urn:li:geo:90010045": "Mexico City Metropolitan Area",
            "urn:li:geo:90010354": "Porto Metropolitan Area",
            "urn:li:geo:90009784": "Greater Jerez de la Frontera Metropolitan Area",
            "urn:li:geo:90009792": "Greater Manresa Metropolitan Area",
            "urn:li:geo:90009812": "Greater Tarragona Area",
            "urn:li:geo:90009822": "Greater Zaragoza Metropolitan Area",
            "urn:li:geo:90009936": "Greater Milan Metropolitan Area",
            "urn:li:geo:90010414": "Grand Tunis Metropolitan Area",
            "urn:li:geo:90009765": "Greater Cáceres Metropolitan Area",
            "urn:li:geo:90009804": "Greater Sabadell Metropolitan Area",
            "urn:li:geo:90009870": "Greater Buenos Aires",
            "urn:li:geo:90009814": "Toledo, Spain Metropolitan Area",
            "urn:li:geo:90009946": "Greater Pescara Metropolitan Area",
            "urn:li:geo:90009797": "Greater Oviedo Metropolitan Area",
            "urn:li:geo:90009753": "Greater La Coruña Area",
            "urn:li:geo:90009778": "Greater Granada Metropolitan Area",
            "urn:li:geo:90010421": "Greater Ankara",
            "urn:li:geo:100238888": "Boiro, Galicia, Spain",
            "urn:li:geo:90010261": "Doha Metropolitan Area",
            "urn:li:geo:102007122": "Cairo, Egypt",
            "urn:li:geo:90009735": "Greater Munich Metropolitan Area",
            "urn:li:geo:104279445": "Miño, Galicia, Spain",
            "urn:li:geo:101623594": "Popayán, Cauca, Colombia",
            "urn:li:geo:90009949": "Greater Pordenone Metropolitan Area",
            "urn:li:geo:107845132": "Požarevac, Centralna Srbija, Serbia",
            "urn:li:geo:90010046": "Monterrey Metropolitan Area",
            "urn:li:geo:101614633": "Soria, Castilla and Leon, Spain",
            "urn:li:geo:101181680": "León, Castilla and Leon, Spain",
            "urn:li:geo:102304121": "Negreira, Galicia, Spain",
            "urn:li:geo:90009603": "Antwerp Metropolitan Area",
            "urn:li:geo:105303313": "Órdenes, Galicia, Spain",
            "urn:li:geo:103061829": "Santa Uxía, Galicia, Spain",
            "urn:li:geo:90009871": "Cordoba, Argentina Metropolitan Area",
            "urn:li:geo:90009794": "Greater Mataró Metropolitan Area",
            "urn:li:geo:102344967": "Fuzhou, Fujian, China",
            "urn:li:geo:90009894": "Greater Chillan Area",
            "urn:li:geo:90009874": "Greater Rosario",
            "urn:li:geo:101887839": "Geilenkirchen, North Rhine-Westphalia, Germany",
            "urn:li:geo:102763519": "Outes, Galicia, Spain",
            "urn:li:geo:104424298": "Athens, Georgia, United States",
            "urn:li:geo:106181918": "Montalbán de Córdoba, Andalusia, Spain",
            "urn:li:geo:106231118": "Coimbra, Coimbra, Portugal",
            "urn:li:geo:90009659": "Greater Paris Metropolitan Region",
            "urn:li:geo:101282030": "Alcobaça, Leiria, Portugal",
            "urn:li:geo:90009884": "Linz-Wels-Steyr Area",
            "urn:li:geo:90009813": "Greater Terrassa Area",
            "urn:li:geo:90009925": "Greater Foggia Metropolitan Area",
            "urn:li:geo:90009886": "Geneva Metropolitan Area",
            "urn:li:geo:90009563": "Hangzhou-Shaoxing Metropolitan Area",
            "urn:li:geo:90009817": "Greater Valladolid Metropolitan Area",
            "urn:li:geo:90009673": "Greater Grenoble Metropolitan Area",
            "urn:li:geo:101784658": "Rangpur, Rajshahi, Bangladesh",
            "urn:li:geo:113018621": "Bertamirans, Galicia, Spain",
            "urn:li:geo:106750182": "Shenzhen, Guangdong, China",
            "urn:li:geo:101321504": "Mar del Plata, Buenos Aires Province, Argentina",
            "urn:li:geo:90010275": "Novi Sad Metropolitan Area",
            "urn:li:geo:105224633": "Canet de Mar, Catalonia, Spain",
            "urn:li:geo:106635744": "Aguaí, São Paulo, Brazil",
            "urn:li:geo:90010347": "Greater Braga Area",
            "urn:li:geo:90009652": "Greater Allahabad Area",
            "urn:li:geo:105436342": "Los Llanos de Aridane, Canary Islands, Spain",
            "urn:li:geo:106702806": "Marau, Rio Grande do Sul, Brazil",
            "urn:li:geo:90009579": "Greater Curitiba",
            "urn:li:geo:102779754": "Jamshedpur, Jharkhand, India",
            "urn:li:geo:101942640": "Noia, Galicia, Spain",
            "urn:li:geo:90009768": "Greater Castellón de la Plana Area",
            "urn:li:geo:90009580": "Greater Campinas",
            "urn:li:geo:90009937": "Greater Modena Metropolitan Area",
            "urn:li:geo:90009766": "Greater Cádiz Metropolitan Area",
            "urn:li:geo:102628138": "Sabiote, Andalusia, Spain",
            "urn:li:geo:106683083": "Cardedeu, Catalonia, Spain",
            "urn:li:geo:90009801": "Greater Ponferrada Metropolitan Area",
            "urn:li:geo:90009834": "Wroclaw Metropolitan Area",
            # --- Sectores (Industries) ---
            "urn:li:industry:11": "Management Consulting",
            "urn:li:industry:135": "Mechanical Or Industrial Engineering",
            "urn:li:industry:64": "Ranching",
            "urn:li:industry:96": "Information Technology & Services",
            "urn:li:industry:4": "Computer Software",
            "urn:li:industry:63": "Farming",
            "urn:li:industry:48": "Construction",
            "urn:li:industry:133": "Wholesale",
            "urn:li:industry:99": "Design",
            "urn:li:industry:25": "Consumer Goods",
            "urn:li:industry:23": "Food Production",
            "urn:li:industry:6": "Internet",
            "urn:li:industry:55": "Machinery",
            "urn:li:industry:117": "Plastics",
            "urn:li:industry:68": "Higher Education",
            "urn:li:industry:53": "Automotive",
            "urn:li:industry:41": "Banking",
            "urn:li:industry:134": "Import & Export",
            "urn:li:industry:84": "Information Services",
            "urn:li:industry:108": "Translation & Localization",
            "urn:li:industry:19": "Apparel & Fashion",
            "urn:li:industry:116": "Logistics & Supply Chain",
            "urn:li:industry:75": "Government Administration",
            "urn:li:industry:70": "Research",
            "urn:li:industry:112": "Electrical & Electronic Manufacturing",
            "urn:li:industry:3241": "Sector 3241",
            "urn:li:industry:56": "Mining & Metals",
            "urn:li:industry:124": "Health, Wellness & Fitness",
            "urn:li:industry:51": "Civil Engineering",
            "urn:li:industry:141": "International Trade & Development",
            "urn:li:industry:383": "Sector 383",
            "urn:li:industry:1042": "Sector 1042",
            "urn:li:industry:42": "Insurance",
            "urn:li:industry:57": "Oil & Energy",
            "urn:li:industry:481": "Sector 481",
            "urn:li:industry:1862": "Sector 1862",
            "urn:li:industry:34": "Food & Beverages",
            "urn:li:industry:80": "Marketing & Advertising",
            "urn:li:industry:840": "Sector 840",
            "urn:li:industry:69": "Education Management",
            "urn:li:industry:59": "Utilities",
            "urn:li:industry:143": "Luxury Goods & Jewelry",
            "urn:li:industry:9": "Law Practice",
            "urn:li:industry:8": "Telecommunications",
            "urn:li:industry:100": "Non-profit Organization Management",
            "urn:li:industry:147": "Industrial Automation",
            "urn:li:industry:709": "Sector 709",
            "urn:li:industry:3242": "Sector 3242",
            "urn:li:industry:86": "Environmental Services",
            "urn:li:industry:15": "Pharmaceuticals",
            "urn:li:industry:30": "Leisure, Travel & Tourism",
            "urn:li:industry:67": "Primary/Secondary Education",
            "urn:li:industry:12": "Biotechnology",
            "urn:li:industry:3099": "Sector 3099",
            "urn:li:industry:27": "Retail",
            "urn:li:industry:150": "Horticulture",
            "urn:li:industry:24": "Consumer Electronics",
            "urn:li:industry:118": "Computer & Network Security",
            "urn:li:industry:52": "Aviation & Aerospace",
            "urn:li:industry:49": "Building Materials",
            "urn:li:industry:2458": "Sector 2458",
            "urn:li:industry:102": "Program Development",
            "urn:li:industry:7": "Semiconductors",
            "urn:li:industry:94": "Airlines/Aviation",
            "urn:li:industry:1999": "Sector 1999",
            "urn:li:industry:87": "Package/Freight Delivery",
            "urn:li:industry:3106": "Sector 3106",
            "urn:li:industry:82": "Publishing",
            "urn:li:industry:79": "Public Policy",
            "urn:li:industry:33": "Sports",
            "urn:li:industry:32": "Restaurants",
            "urn:li:industry:31": "Hospitality",
            "urn:li:industry:14": "Hospital & Health Care",
            "urn:li:industry:5": "Computer Networking",
            "urn:li:industry:66": "Fishery",
            "urn:li:industry:29": "Gambling & Casinos",
            "urn:li:industry:65": "Dairy",
            "urn:li:industry:1445": "Sector 1445",
            "urn:li:industry:928": "Sector 928",
            "urn:li:industry:408": "Sector 408",
            "urn:li:industry:148": "Government Relations",
            "urn:li:industry:3128": "Sector 3128",
            "urn:li:industry:2029": "Sector 2029",
            "urn:li:industry:2360": "Sector 2360",
            "urn:li:industry:126": "Media Production",
            "urn:li:industry:1916": "Sector 1916",
            "urn:li:industry:1905": "Sector 1905",
            "urn:li:industry:22": "Supermarkets",
            "urn:li:industry:111": "Arts & Crafts",
            "urn:li:industry:110": "Events Services",
            "urn:li:industry:20": "Sporting Goods",
            "urn:li:industry:256": "Sector 256",
            "urn:li:industry:105": "Professional Training & Coaching",
            "urn:li:industry:104": "Staffing & Recruiting",
            "urn:li:industry:47": "Accounting",
            "urn:li:industry:44": "Real Estate",
            "urn:li:industry:43": "Financial Services",
            "urn:li:industry:93": "Warehousing",
            "urn:li:industry:92": "Transportation/Trucking/Railroad",
            "urn:li:industry:90": "Civic & Social Organization",
        }

        # Mapeo del parámetro solicitado a la clave del JSON de respuesta y la clave interna del ítem
        field_mapping = {
            "SENIORITY": ("followerCountsBySeniority", "seniority"),
            "INDUSTRY": ("followerCountsByIndustry", "industry"),
            "FUNCTION": ("followerCountsByFunction", "function"),
            "COMPANY_SIZE": ("followerCountsByStaffCountRange", "staffCountRange"),
            "GEOGRAPHIC_AREA": ("followerCountsByGeo", "geo")
        }

        target_field, inner_key = field_mapping.get(pivot_type, (None, None))

        if not target_field:
            logger.error(f"❌ Tipo de segmentación no soportado: {pivot_type}")
            return None

        try:
            response = requests.get(url, headers=self.api_headers, params=params)
            if response.status_code == 200:
                elements = response.json().get('elements', [])
                data = []
                for el in elements:
                    # Obtenemos la lista específica para el pivot solicitado
                    counts_list = el.get(target_field, [])
                    
                    for item in counts_list:
                        # 1. Obtener la etiqueta (URN) usando la clave correcta
                        urn = item.get(inner_key)
                        
                        # 2. CORRECCIÓN CRÍTICA: Los seguidores están dentro de un objeto 'followerCounts'
                        # que separa 'organicFollowerCount' y 'paidFollowerCount'.
                        follower_counts = item.get('followerCounts', {})
                        organic = follower_counts.get('organicFollowerCount', 0)
                        paid = follower_counts.get('paidFollowerCount', 0)
                        total_count = organic + paid
                        
                        # Traducimos el URN si está en nuestro mapa
                        label = labels_map.get(urn, urn)
                        
                        data.append({
                            'segmento': label,
                            'seguidores': total_count
                        })
                
                if not data:
                    logger.warning(f"⚠️ No se encontraron datos para la segmentación {pivot_type}.")
                    return None

                return pd.DataFrame(data).sort_values(by='seguidores', ascending=False)
            else:
                logger.error(f"❌ Error en segmentación {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"🔥 Error inesperado: {e}")
            return None

    def get_recent_posts_details(self, count=10):
        """
        Nueva función que obtiene las publicaciones recientes con TODOS sus detalles
        (fecha, texto completo, tipo de contenido, enlace, etc.), sin afectar a la función original.
        """
        logger.info("Obteniendo publicaciones recientes con detalles completos...")

        url = f"{self.base_url}/posts"
        params = {
            "q": "author",
            "author": self.author_urn,
            "count": count,
            "sortBy": "CREATED"
        }
        
        try:
            response = requests.get(url, headers=self.api_headers, params=params)
            
            if response.status_code == 200:
                elements = response.json().get('elements', [])
                posts_data = []
                
                for post in elements:
                    # 1. ID y URN
                    urn = post.get('id')
                    
                    # 2. Fecha (timestamp en milisegundos -> fecha legible)
                    created_at = post.get('createdAt')
                    date_str = ""
                    if created_at:
                        date_obj = pd.to_datetime(created_at, unit='ms')
                        date_str = date_obj.strftime('%Y-%m-%d %H:%M')

                    # 3. Texto del Post
                    text = post.get('commentary', '')
                    
                    # 4. Tipo de Medio
                    media_type = "Texto"
                    content = post.get('content', {})
                    if content:
                        if 'media' in content:
                            media_type = "Imagen/Video"
                        elif 'multiImage' in content:
                            media_type = "Carrusel"
                        elif 'article' in content:
                            media_type = "Artículo"
                        elif 'poll' in content:
                            media_type = "Encuesta"

                    # 5. Enlace directo
                    permalink = f"https://www.linkedin.com/feed/update/{urn}"

                    posts_data.append({
                        'post_id': urn,
                        'fecha': date_str,
                        'texto_completo': text,
                        'texto_corto': text[:50] + "..." if len(text) > 50 else text,
                        'tipo': media_type,
                        'enlace': permalink
                    })
                
                logger.info(f"✅ Se han encontrado {len(posts_data)} posts con detalles.")
                return posts_data
            else:
                logger.error(f"❌ Error al listar posts detallados: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"🔥 Error en get_recent_posts_details: {e}")
            return []

    def get_post_metrics_advanced(self, post_ids, date_range=None, aggregation="TOTAL"):
        """
        Obtiene métricas avanzadas para posts con opciones de agregación temporal.

        Args:
            post_ids: Lista de URNs de posts
            date_range: Dict con {'start': {'year': 2024, 'month': 1, 'day': 1}, 'end': {...}}
            aggregation: "TOTAL" o "DAILY"

        Returns:
            DataFrame con métricas avanzadas incluyendo MEMBERS_REACHED, RESHARE, etc.
        """
        if not post_ids:
            return None

        if isinstance(post_ids, str):
            post_ids = [post_ids]

        post_ids = post_ids[:20]

        logger.info(f"📊 Consultando métricas avanzadas para {len(post_ids)} publicaciones...")

        try:
            all_metrics = []

            for post_id in post_ids:
                # Métricas estándar
                metrics_types = ["IMPRESSION", "REACTION", "COMMENT", "RESHARE", "CLICK_COUNT"]

                # Si date_range no es None, intentar agregar MEMBERS_REACHED (no soporta DAILY)
                if aggregation == "TOTAL":
                    metrics_types.append("MEMBERS_REACHED")

                post_metrics = {'post_id': post_id}

                for metric_type in metrics_types:
                    url = f"{self.base_url}/memberPostStatistics"
                    params = {
                        "q": "entity",
                        "entity": post_id,
                        "metricType": metric_type
                    }

                    # Añadir date_range si se proporciona
                    if date_range:
                        params["dateRange"] = f"({date_range})"

                    # Añadir aggregation
                    if aggregation and metric_type != "MEMBERS_REACHED":
                        params["aggregation"] = aggregation

                    response = requests.get(url, headers=self.api_headers, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        elements = data.get('elements', [])

                        if elements:
                            if aggregation == "DAILY" and metric_type != "MEMBERS_REACHED":
                                # Para agregación diaria, guardar todas las fechas
                                for elem in elements:
                                    count = elem.get('count', 0)
                                    date_range_elem = elem.get('dateRange', {})
                                    post_metrics[f"{metric_type.lower()}_data"] = {
                                        'count': count,
                                        'date_range': date_range_elem
                                    }
                            else:
                                # Para TOTAL, solo el count
                                post_metrics[metric_type.lower()] = elements[0].get('count', 0)
                    else:
                        logger.warning(f"⚠️ Error obteniendo {metric_type} para {post_id}: {response.status_code}")
                        post_metrics[metric_type.lower()] = 0

                # Calcular métricas derivadas
                impressions = post_metrics.get('impression', 0)
                members_reached = post_metrics.get('members_reached', impressions)
                reactions = post_metrics.get('reaction', 0)
                comments = post_metrics.get('comment', 0)
                reshares = post_metrics.get('reshare', 0)
                clicks = post_metrics.get('click_count', 0)

                # Engagement Rate
                total_engagement = reactions + comments + reshares + clicks
                er = (total_engagement / impressions * 100) if impressions > 0 else 0

                # Alcance Único (Reach Rate)
                reach_rate = (members_reached / impressions * 100) if impressions > 0 else 0

                # Viralidad (Reshare Rate)
                virality = (reshares / impressions * 100) if impressions > 0 else 0

                post_metrics.update({
                    'ER%': round(er, 2),
                    'reach_rate%': round(reach_rate, 2),
                    'virality%': round(virality, 2),
                    'total_engagement': total_engagement
                })

                all_metrics.append(post_metrics)

            return pd.DataFrame(all_metrics)

        except Exception as e:
            logger.error(f"🔥 Error en get_post_metrics_advanced: {e}")
            return None

    def get_video_analytics(self, video_post_id, time_range=None, aggregation="ALL"):
        """
        Obtiene analíticas específicas para posts de video.

        Args:
            video_post_id: URN del post de video
            time_range: Dict con {'start': timestamp_ms, 'end': timestamp_ms}
            aggregation: "DAY", "WEEK", o "ALL"

        Returns:
            Dict con métricas de video: views, viewers, watch_time, etc.
        """
        logger.info(f"📹 Obteniendo analíticas de video para {video_post_id}...")

        metrics = {
            'post_id': video_post_id,
            'video_views': 0,
            'unique_viewers': 0,
            'total_watch_time_ms': 0,
            'watch_time_for_views_ms': 0
        }

        metric_types = [
            "VIDEO_VIEW",
            "VIEWER",
            "TIME_WATCHED",
            "TIME_WATCHED_FOR_VIDEO_VIEWS"
        ]

        try:
            for metric_type in metric_types:
                url = f"{self.base_url}/videoAnalytics"
                params = {
                    "q": "entity",
                    "entity": video_post_id,
                    "type": metric_type,
                    "aggregation": aggregation
                }

                if time_range:
                    params["timeRange"] = f"(start:{time_range['start']},end:{time_range['end']})"

                response = requests.get(url, headers=self.api_headers, params=params)

                if response.status_code == 200:
                    data = response.json()
                    elements = data.get('elements', [])

                    if elements:
                        total_value = sum(elem.get('viewCount', elem.get('viewerCount', elem.get('watchTime', 0)))
                                        for elem in elements)

                        if metric_type == "VIDEO_VIEW":
                            metrics['video_views'] = total_value
                        elif metric_type == "VIEWER":
                            metrics['unique_viewers'] = total_value
                        elif metric_type == "TIME_WATCHED":
                            metrics['total_watch_time_ms'] = total_value
                        elif metric_type == "TIME_WATCHED_FOR_VIDEO_VIEWS":
                            metrics['watch_time_for_views_ms'] = total_value
                else:
                    logger.warning(f"⚠️ Error obteniendo {metric_type}: {response.status_code}")

            # Calcular métricas derivadas
            if metrics['video_views'] > 0:
                metrics['avg_watch_time_sec'] = round(
                    (metrics['watch_time_for_views_ms'] / metrics['video_views']) / 1000, 2
                )
                metrics['completion_rate%'] = round(
                    (metrics['unique_viewers'] / metrics['video_views'] * 100), 2
                )
            else:
                metrics['avg_watch_time_sec'] = 0
                metrics['completion_rate%'] = 0

            # Convertir tiempo total a formato legible
            total_hours = round(metrics['total_watch_time_ms'] / (1000 * 60 * 60), 2)
            metrics['total_watch_time_hours'] = total_hours

            logger.info(f"✅ Analíticas de video obtenidas: {metrics['video_views']} vistas, {total_hours}h reproducción")
            return metrics

        except Exception as e:
            logger.error(f"🔥 Error en get_video_analytics: {e}")
            return metrics

    def get_follower_growth(self, days=30):
        """
        Obtiene el crecimiento de seguidores en el tiempo.

        Args:
            days: Número de días hacia atrás para analizar

        Returns:
            DataFrame con crecimiento diario de seguidores
        """
        logger.info(f"📈 Obteniendo crecimiento de seguidores (últimos {days} días)...")

        try:
            url = f"{self.base_url}/organizationalEntityFollowerStatistics"
            params = {
                "q": "organizationalEntity",
                "organizationalEntity": self.author_urn,
                "timeIntervals.timeGranularityType": "DAY",
                "timeIntervals.timeRange.start": int((pd.Timestamp.now() - pd.Timedelta(days=days)).timestamp() * 1000)
            }

            response = requests.get(url, headers=self.api_headers, params=params)

            if response.status_code == 200:
                elements = response.json().get('elements', [])
                data = []

                for elem in elements:
                    time_range = elem.get('timeRange', {})
                    start_ms = time_range.get('start', 0)

                    if start_ms:
                        date = pd.to_datetime(start_ms, unit='ms').date()

                        # Seguidores orgánicos y pagos
                        organic = elem.get('followerGains', {}).get('organicFollowerGain', 0)
                        paid = elem.get('followerGains', {}).get('paidFollowerGain', 0)
                        total_gain = organic + paid

                        data.append({
                            'fecha': date,
                            'ganancia_organica': organic,
                            'ganancia_pagada': paid,
                            'ganancia_total': total_gain
                        })

                if data:
                    df = pd.DataFrame(data).sort_values('fecha')
                    # Calcular acumulado
                    df['seguidores_acumulados'] = df['ganancia_total'].cumsum()
                    logger.info(f"✅ Datos de crecimiento obtenidos: {len(df)} días")
                    return df
                else:
                    logger.warning("⚠️ No se encontraron datos de crecimiento")
                    return None
            else:
                logger.error(f"❌ Error {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logger.error(f"🔥 Error en get_follower_growth: {e}")
            return None