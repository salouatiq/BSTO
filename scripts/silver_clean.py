#!/usr/bin/env python3
"""
Script pour nettoyer les données de bronze vers silver
"""

import os
import json
import pandas as pd
from minio import Minio
from minio.error import S3Error
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_PASSWORD", "briancon2026")
MINIO_BUCKET_BRONZE = "briancon-bronze"
MINIO_BUCKET_SILVER = "briancon-silver"
MINIO_SECURE = False

def create_minio_client():
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)
    return client

def ensure_bucket_exists(client, bucket):
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info(f"Bucket {bucket} créé")

def clean_weather_data(df):
    # Nettoyage : supprimer nulls, convertir timestamps
    df = df.dropna()
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def process_file(client, object_name):
    try:
        # Télécharger depuis bronze
        response = client.get_object(MINIO_BUCKET_BRONZE, object_name)
        data = json.load(response)
        response.close()
        response.release_conn()

        # Extraire hourly data
        if 'hourly' in data:
            df = pd.DataFrame(data['hourly'])
            df.rename(columns={'time': 'timestamp'}, inplace=True)
        else:
            logger.warning(f"Pas de données hourly dans {object_name}")
            return

        # Nettoyer
        df_clean = clean_weather_data(df)

        # Convertir en JSON string pour upload (pas de sauvegarde locale)
        json_data = df_clean.to_json(orient='records', date_format='iso')

        # Uploader vers silver
        client.put_object(
            MINIO_BUCKET_SILVER,
            f"clean_{object_name}",
            data=json_data,
            length=len(json_data),
            content_type='application/json'
        )

        logger.info(f"Nettoyé et uploadé : {object_name}")
    except Exception as e:
        logger.error(f"Erreur traitement {object_name}: {e}")

if __name__ == "__main__":
    client = create_minio_client()
    ensure_bucket_exists(client, MINIO_BUCKET_SILVER)

    # Lister les objets de bronze
    objects = client.list_objects(MINIO_BUCKET_BRONZE)
    for obj in objects:
        process_file(client, obj.object_name)

    logger.info("Nettoyage silver terminé")