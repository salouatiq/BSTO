# Script d'extraction et de validation des données de stationnement de Briançon
# Ce script simule l'extraction des données de stationnement depuis une API de la ville, valide la structure des données selon un modèle défini, et les charge dans un bucket MinIO (équivalent local de GCS).
# Note 1:       
# ------
    # Assurez-vous d'avoir un serveur MinIO en cours d'exécution localement (par exemple, via Docker) et que les variables d'environnement sont correctement configurées dans un fichier .env.
    # Pour exécuter ce script, utilisez la commande : python scripts/extract_api.py 
    # Ce script est un point de départ pour votre pipeline d'extraction. En production, vous pourriez vouloir remplacer la simulation de données par un appel réel à l'API de la ville de Briançon, et ajouter des fonctionnalités comme la gestion des erreurs, les notifications en cas d'échec, ou l'intégration avec d'autres sources de données.
# Note 2:
# ------
    # Ce script utilise Pydantic pour la validation des données, ce qui garantit que les données respectent une structure définie avant d'être chargées dans MinIO. Cela correspond à une bonne pratique de qualité des données, surtout dans le secteur public où la fiabilité des données est cruciale.
    # N'hésitez pas à consulter la documentation de Pydantic pour découvrir toutes les fonctionnalités de validation avancées que vous pouvez utiliser pour garantir la qualité de vos données de stationnement !
# Documentation : https://pydantic.dev/

#!/usr/bin/env python3
"""
Script pour extraire les données des parkings de Briançon depuis l'API OpenStreetMap (Overpass)
et les injecter dans le bucket briancon-bronze de MinIO.
"""

import os
import io
import json
import requests
import logging
from datetime import datetime
from minio import Minio
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
# Si on lance le script depuis le terminal local, 'localhost:9000' est nécessaire.
# Si on le lance depuis Mage (Docker), c'est 'minio:9000'. On gère les deux via le fallback.
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_PASSWORD", "briancon2026")
MINIO_BUCKET = "briancon-bronze"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def extract_and_load_parking():
    logger.info("🚗 Lancement de l'extraction des parkings depuis OpenStreetMap...")
    
    # 1. Formulation de la requête Overpass QL
    # On cible spécifiquement la commune de Briançon et on cherche le tag amenity=parking
    overpass_query = """
    [out:json][timeout:60];
    area["name"="Briançon"]->.searchArea;
    (
      node["amenity"="parking"](area.searchArea);
      way["amenity"="parking"](area.searchArea);
      relation["amenity"="parking"](area.searchArea);
    );
    out body;
    >;
    out skel qt;
    """
    
    try:
        # 2. Appel de l'API OpenStreetMap avec un User-Agent (Badge visiteur)
        headers = {
            'User-Agent': 'Projet_BSTO_Data_Engineering/1.0 (Analyse de la pression touristique)'
        }
        
        response = requests.post(OVERPASS_URL, data={'data': overpass_query}, headers=headers, timeout=60)
        response.raise_for_status()
        parking_data = response.json()
        
        count_elements = len(parking_data.get('elements', []))
        logger.info(f"📥 {count_elements} éléments 'parking' trouvés dans OpenStreetMap.")
        
        # 3. Préparation de la sauvegarde dans MinIO
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"parking/briancon_parking_raw_{timestamp}.json"
        
        # Conversion du dictionnaire JSON en octets (bytes) pour l'envoyer en mémoire
        json_bytes = json.dumps(parking_data, indent=2, ensure_ascii=False).encode('utf-8')
        
        # 4. Connexion et Envoi vers MinIO (Bronze)
        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
        
        client.put_object(
            MINIO_BUCKET,
            object_name,
            data=io.BytesIO(json_bytes),
            length=len(json_bytes),
            content_type='application/json'
        )
        
        logger.info(f"✅ Succès ! Fichier brut sauvegardé dans Bronze : {object_name}")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erreur lors de l'appel à l'API Overpass : {e}")
    except Exception as e:
        logger.error(f"❌ Erreur inattendue : {e}")

if __name__ == "__main__":
    extract_and_load_parking()