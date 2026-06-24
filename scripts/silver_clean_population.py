#!/usr/bin/env python3
"""
Script Silver : Lit les données de population brutes (JSON) depuis MinIO (Bronze),
calcule la densité, sauvegarde dans MinIO (Silver) ET stocke dans PostgreSQL (Silver).
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

def clean_and_load_population():
    logger.info("🥈 Lancement de la transformation Silver pour la population...")
    
    # 1. Connexion à MinIO et récupération du dernier fichier
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
    
    objects = list(client.list_objects(MINIO_BUCKET_BRONZE, prefix="population/", recursive=True))
    if not objects:
        logger.error("❌ Aucun fichier de population trouvé dans Bronze.")
        return
        
    latest_file = sorted(objects, key=lambda x: x.last_modified, reverse=True)[0]
    logger.info(f"📥 Lecture du fichier brut : {latest_file.object_name}")
    
    response = client.get_object(MINIO_BUCKET_BRONZE, latest_file.object_name)
    data = json.loads(response.read().decode('utf-8'))
    response.close()
    response.release_conn()

    # 2. Nettoyage et Enrichissement
    # L'API renvoie un simple dictionnaire, on le met dans une liste pour faire un DataFrame
    df = pd.DataFrame([data])
    
    # L'API Geo donne la surface en hectares. 1 km² = 100 hectares.
    # On calcule la densité : Population / (Surface / 100)
    if 'population' in df.columns and 'surface' in df.columns:
        df['surface_km2'] = df['surface'] / 100
        df['densite_km2'] = (df['population'] / df['surface_km2']).round(2)
    
    # Ajout d'une date de mise à jour
    df['date_extraction'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    
    logger.info(f"🧹 Données enrichies : Densité calculée à {df['densite_km2'].iloc[0]} hab/km².")

    # 3. SAUVEGARDE DANS MINIO (SILVER)
    raw_filename = os.path.basename(latest_file.object_name)
    silver_object_name = f"clean_population/clean_{raw_filename}"
    
    json_data = df.to_json(orient='records', date_format='iso', indent=4)
    json_bytes = json_data.encode('utf-8')
    
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

    # 4. SAUVEGARDE DANS POSTGRESQL (SILVER)
    db_host = "localhost" if MINIO_ENDPOINT == "localhost:9000" else PG_HOST
    engine = create_engine(f'postgresql://{PG_USER}:{PG_PASSWORD}@{db_host}:{PG_PORT}/{PG_DB}')
    
    df.to_sql('population_silver', engine, if_exists='replace', index=False)
    logger.info("✅ Succès ! Table 'population_silver' mise à jour dans PostgreSQL.")

if __name__ == "__main__":
    clean_and_load_population()