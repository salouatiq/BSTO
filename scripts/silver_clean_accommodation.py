#!/usr/bin/env python3
"""
Script Silver : Lit les hébergements bruts (JSON) depuis MinIO (Bronze),
les nettoie, gère les capacités manquantes, et les stocke dans MinIO + PostgreSQL (Silver).
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
PG_HOST = "postgres"  
PG_PORT = "5432"
PG_DB = "briancon_db"

def clean_and_load_accommodation():
    logger.info("🥈 Lancement de la transformation Silver pour les hébergements...")
    
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
    objects = list(client.list_objects(MINIO_BUCKET_BRONZE, prefix="accommodation/", recursive=True))
    
    if not objects:
        logger.error("❌ Aucun fichier trouvé dans Bronze.")
        return
        
    latest_file = sorted(objects, key=lambda x: x.last_modified, reverse=True)[0]
    response = client.get_object(MINIO_BUCKET_BRONZE, latest_file.object_name)
    data = json.loads(response.read().decode('utf-8'))
    response.close()
    response.release_conn()

    # Nettoyage et aplatissement
    acc_list = []
    for element in data.get('elements', []):
        if 'tags' in element:
            tags = element['tags']
            acc_list.append({
                'osm_id': element.get('id'),
                'type': tags.get('tourism', 'inconnu'),
                'name': tags.get('name', 'Hébergement sans nom'),
                'beds': pd.to_numeric(tags.get('beds') or tags.get('rooms'), errors='coerce')
            })

    df = pd.DataFrame(acc_list)
    
    # Imputation basique : si le nombre de lits est inconnu, on met 4 par défaut (moyenne basse)
    df['beds'] = df['beds'].fillna(4).round()
    
    logger.info(f"🧹 {len(df)} hébergements nettoyés.")

    # Sauvegarde MinIO (Silver)
    raw_filename = os.path.basename(latest_file.object_name)
    silver_object_name = f"clean_accommodation/clean_{raw_filename}"
    
    json_bytes = df.to_json(orient='records', date_format='iso', indent=4).encode('utf-8')
    if not client.bucket_exists(MINIO_BUCKET_SILVER):
        client.make_bucket(MINIO_BUCKET_SILVER)
        
    client.put_object(MINIO_BUCKET_SILVER, silver_object_name, data=io.BytesIO(json_bytes), length=len(json_bytes), content_type='application/json')
    logger.info(f"☁️ Fichier sauvegardé dans MinIO Silver : {silver_object_name}")

    # Sauvegarde PostgreSQL
    db_host = "localhost" if MINIO_ENDPOINT == "localhost:9000" else PG_HOST
    engine = create_engine(f'postgresql://{PG_USER}:{PG_PASSWORD}@{db_host}:{PG_PORT}/{PG_DB}')
    df.to_sql('accommodation_silver', engine, if_exists='replace', index=False)
    logger.info("✅ Table 'accommodation_silver' mise à jour dans PostgreSQL.")

if __name__ == "__main__":
    clean_and_load_accommodation()