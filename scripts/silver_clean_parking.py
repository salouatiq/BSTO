#!/usr/bin/env python3
"""
Script Silver : Lit les données parkings brutes (JSON) depuis MinIO (Bronze),
les nettoie, les aplatit, les sauvegarde dans MinIO (Silver) ET les stocke dans PostgreSQL (Silver).
"""

import os
import json
import io
import logging
import pandas as pd
from minio import Minio
from sqlalchemy import create_engine
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_PASSWORD", "briancon2026")
MINIO_BUCKET_BRONZE = "briancon-bronze"
MINIO_BUCKET_SILVER = "briancon-silver"

PG_USER = "admin"
PG_PASSWORD = "briancon2026"
PG_HOST = "postgres"            # Adresse Docker (sera "localhost" si exécuté en dehors de Docker sans redirection)
PG_PORT = "5432"
PG_DB = "briancon_db"

def clean_and_load_parking():
    logger.info("🥈 Lancement de la transformation Silver pour les parkings...")
    
    # 1. Connexion à MinIO et récupération du dernier fichier Parking
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
    
    objects = list(client.list_objects(MINIO_BUCKET_BRONZE, prefix="parking/", recursive=True))
    if not objects:
        logger.error("❌ Aucun fichier de parking trouvé dans Bronze.")
        return
        
    latest_file = sorted(objects, key=lambda x: x.last_modified, reverse=True)[0]
    logger.info(f"📥 Lecture du fichier brut : {latest_file.object_name}")
    
    response = client.get_object(MINIO_BUCKET_BRONZE, latest_file.object_name)
    data = json.loads(response.read().decode('utf-8'))
    response.close()
    response.release_conn()

    # 2. Nettoyage et extraction des données (Aplatissement du JSON)
    parking_list = []
    for element in data.get('elements', []):
        if 'tags' in element and element['tags'].get('amenity') == 'parking':
            tags = element['tags']
            parking_list.append({
                'osm_id': element.get('id'),
                'osm_type': element.get('type'),
                'name': tags.get('name', 'Parking sans nom'),
                'capacity': pd.to_numeric(tags.get('capacity'), errors='coerce'), 
                'fee': tags.get('fee', 'unknown'), 
                'parking_type': tags.get('parking', 'surface') 
            })

    df = pd.DataFrame(parking_list)
    median_capacity = df['capacity'].median()
    df['capacity'] = df['capacity'].fillna(median_capacity).round()
    
    logger.info(f"🧹 {len(df)} parkings nettoyés et préparés.")

    # 3. SAUVEGARDE DANS MINIO (SILVER) - Nouvelle étape harmonisée !
    # On extrait juste le nom du fichier (sans le préfixe parking/)
    raw_filename = os.path.basename(latest_file.object_name)
    silver_object_name = f"clean_parking/clean_{raw_filename}"
    
    json_data = df.to_json(orient='records', date_format='iso', indent=4)
    json_bytes = json_data.encode('utf-8')
    
    # On s'assure que le bucket silver existe
    if not client.bucket_exists(MINIO_BUCKET_SILVER):
        client.make_bucket(MINIO_BUCKET_SILVER)
        
    client.put_object(
        MINIO_BUCKET_SILVER,
        silver_object_name,
        data=io.BytesIO(json_bytes),
        length=len(json_bytes),
        content_type='application/json'
    )
    logger.info(f"☁️ Fichier sauvegardé dans MinIO Silver : {silver_object_name}")

    # 4. Sauvegarde dans PostgreSQL (Silver)
    db_host = "localhost" if MINIO_ENDPOINT == "localhost:9000" else PG_HOST
    engine = create_engine(f'postgresql://{PG_USER}:{PG_PASSWORD}@{db_host}:{PG_PORT}/{PG_DB}')
    
    df.to_sql('parking_silver', engine, if_exists='replace', index=False)
    logger.info("✅ Succès ! Table 'parking_silver' mise à jour dans PostgreSQL.")

if __name__ == "__main__":
    clean_and_load_parking()