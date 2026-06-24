#!/usr/bin/env python3
"""
Script pour nettoyer les données de bronze vers silver ET charger dans PostgreSQL
"""

import os
import json
import pandas as pd
from minio import Minio
from minio.error import S3Error
from sqlalchemy import create_engine
import logging
from dotenv import load_dotenv
import io

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
MINIO_SECURE = False

# Configuration PostgreSQL (ajoutée)
PG_USER = "admin"
PG_PASSWORD = "briancon2026"
PG_HOST = "postgres"  # <--- Remplacer localhost par postgres
PG_PORT = "5432"
PG_DB = "briancon_db"
DATABASE_URI = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"

# ==========================================
# FONCTIONS
# ==========================================
def create_minio_client():
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)
    return client

def ensure_bucket_exists(client, bucket):
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info(f"🪣 Bucket {bucket} créé")

def clean_weather_data(df):
    # Nettoyage : supprimer nulls, convertir timestamps
    df = df.dropna()
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def process_file(client, engine, object_name):
    try:
        # 1. Télécharger depuis bronze
        response = client.get_object(MINIO_BUCKET_BRONZE, object_name)
        data = json.load(response)
        response.close()
        response.release_conn()

        # 2. Extraire hourly data
        if 'hourly' in data:
            df = pd.DataFrame(data['hourly'])
            df.rename(columns={'time': 'timestamp'}, inplace=True)
        else:
            logger.warning(f"⚠️ Pas de données hourly dans {object_name}")
            return

        # 3. Nettoyer
        df_clean = clean_weather_data(df)

        # 4. UPLOADER VERS MINIO (SILVER)
        json_data = df_clean.to_json(orient='records', date_format='iso')
        json_bytes = json_data.encode('utf-8')

        client.put_object(
            MINIO_BUCKET_SILVER,
            f"clean_{object_name}",
            data=io.BytesIO(json_bytes),
            length=len(json_bytes),
            content_type='application/json'
        )
        logger.info(f"✅ Fichier uploadé dans Silver : clean_{object_name}")

        # 5. CHARGER DANS POSTGRESQL (STAGING)
        table_name = 'weather_silver'
        df_clean.to_sql(table_name, con=engine, if_exists='append', index=False)
        logger.info(f"🐘 Données insérées dans la table PostgreSQL : {table_name}")

    except Exception as e:
        logger.error(f"❌ Erreur traitement {object_name}: {e}")

# ==========================================
# EXÉCUTION
# ==========================================
if __name__ == "__main__":
    logger.info("🚀 Lancement du traitement Bronze -> Silver & PostgreSQL")
    
    # Initialisation des connexions
    client = create_minio_client()
    engine = create_engine(DATABASE_URI)
    
    ensure_bucket_exists(client, MINIO_BUCKET_SILVER)

    # Lister les objets de bronze et les traiter
    objects = client.list_objects(MINIO_BUCKET_BRONZE)
    for obj in objects:
        process_file(client, engine, obj.object_name)

    logger.info("🏁 Nettoyage Silver et chargement PostgreSQL terminés")