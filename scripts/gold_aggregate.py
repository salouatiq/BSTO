#!/usr/bin/env python3
"""
Script pour agréger les données de silver vers gold et DuckDB
"""

import os
import pandas as pd
from minio import Minio
import duckdb
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_USER", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_PASSWORD", "briancon2026")
MINIO_BUCKET_SILVER = "briancon-silver"
MINIO_BUCKET_GOLD = "briancon-gold"
MINIO_SECURE = False

GOLD_DIR = "../data/gold"
DUCKDB_PATH = "../data/duckdb/briancon.duckdb"

def create_minio_client():
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)
    return client

def ensure_bucket_exists(client, bucket):
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info(f"Bucket {bucket} créé")

def aggregate_weather_data(df):
    # Agrégation quotidienne
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    agg_df = df.groupby('date').agg({
        'temperature_2m': ['mean', 'max', 'min'],
        'precipitation': 'sum'
    }).round(2)
    agg_df.columns = ['temp_mean', 'temp_max', 'temp_min', 'precip_sum']
    agg_df = agg_df.reset_index()
    return agg_df

def process_silver_to_gold(client):
    # Télécharger tous les fichiers silver
    objects = list(client.list_objects(MINIO_BUCKET_SILVER))
    all_data = []
    for obj in objects:
        response = client.get_object(MINIO_BUCKET_SILVER, obj.object_name)
        df = pd.read_json(response)
        all_data.append(df)
        response.close()
        response.release_conn()

    if not all_data:
        logger.warning("Aucune donnée silver trouvée")
        return

    # Concaténer
    full_df = pd.concat(all_data, ignore_index=True)
    logger.info(f"Données concaténées: {len(full_df)} lignes")

    # Agréger
    agg_df = aggregate_weather_data(full_df)
    logger.info(f"Données agrégées: {len(agg_df)} lignes")

    # Sauvegarder en parquet local (optionnel pour archivage)
    os.makedirs(GOLD_DIR, exist_ok=True)
    parquet_path = os.path.join(GOLD_DIR, "weather_gold.parquet")
    agg_df.to_parquet(parquet_path, index=False, engine='pyarrow')
    logger.info(f"Parquet sauvegardé: {parquet_path}")

    # Uploader vers gold
    client.fput_object(MINIO_BUCKET_GOLD, "weather_gold.parquet", parquet_path)

    # Charger dans DuckDB
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("DROP TABLE IF EXISTS weather_daily")
    con.execute(f"CREATE TABLE weather_daily AS SELECT * FROM read_parquet('{parquet_path}')")
    con.close()

    logger.info("Agrégation gold et chargement DuckDB terminé")

if __name__ == "__main__":
    client = create_minio_client()
    ensure_bucket_exists(client, MINIO_BUCKET_GOLD)
    process_silver_to_gold(client)