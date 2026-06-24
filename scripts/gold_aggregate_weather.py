#!/usr/bin/env python3
"""
Script pour agréger les données de silver vers gold et DuckDB
"""

import os
import pandas as pd
from minio import Minio
import duckdb
import pyarrow  # Nécessaire pour la manipulation des fichiers Parquet
import logging
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
MINIO_BUCKET_SILVER = "briancon-silver"
MINIO_BUCKET_GOLD = "briancon-gold"
MINIO_SECURE = False

# Chemins locaux en dehors du territoire de MinIO, ajustés pour s'exécuter depuis la racine du projet
GOLD_DIR = "analytics/temp_export"
DUCKDB_DIR = "analytics/db"
DUCKDB_PATH = f"{DUCKDB_DIR}/briancon.duckdb"

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

def aggregate_weather_data(df):
    # Agrégation quotidienne : on passe de données horaires à des résumés journaliers
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    agg_df = df.groupby('date').agg({
        'temperature_2m': ['mean', 'max', 'min'],
        'precipitation': 'sum'
    }).round(2)
    
    # Aplatissement des noms de colonnes
    agg_df.columns = ['temp_mean', 'temp_max', 'temp_min', 'precip_sum']
    agg_df = agg_df.reset_index()
    return agg_df

def process_silver_to_gold(client):
    logger.info("🔄 Téléchargement des données Silver depuis MinIO...")
    # On cible uniquement le dossier météo de manière récursive (c'est suite à la céation des dossiers clean_weather/ dans Silver)
    objects = list(client.list_objects(MINIO_BUCKET_SILVER, prefix="clean_weather/", recursive=True))
    all_data = []
    
    for obj in objects:
        response = client.get_object(MINIO_BUCKET_SILVER, obj.object_name)
        df = pd.read_json(response)
        all_data.append(df)
        response.close()
        response.release_conn()

    if not all_data:
        logger.warning("⚠️ Aucune donnée silver trouvée")
        return

    # 1. Concaténer
    full_df = pd.concat(all_data, ignore_index=True)
    logger.info(f"📊 Données concaténées: {len(full_df)} lignes")

    # 2. Agréger
    agg_df = aggregate_weather_data(full_df)
    logger.info(f"📈 Données agrégées: {len(agg_df)} lignes (jours)")

    # 3. Sauvegarder en parquet local
    os.makedirs(GOLD_DIR, exist_ok=True)
    parquet_path = os.path.join(GOLD_DIR, "weather_gold.parquet")
    agg_df.to_parquet(parquet_path, index=False, engine='pyarrow')
    logger.info(f"💾 Fichier Parquet sauvegardé en local : {parquet_path}")

    # 4. Uploader vers gold
    client.fput_object(MINIO_BUCKET_GOLD, "weather_gold.parquet", parquet_path)
    logger.info("☁️ Fichier Parquet sécurisé dans MinIO Gold")

    # 5. Charger dans DuckDB
    logger.info("🦆 Chargement dans la base analytique DuckDB...")
    os.makedirs(DUCKDB_DIR, exist_ok=True)
    con = duckdb.connect(DUCKDB_PATH)
    
    # DuckDB lit directement le fichier Parquet pour créer sa table !
    con.execute("DROP TABLE IF EXISTS weather_daily")
    con.execute(f"CREATE TABLE weather_daily AS SELECT * FROM read_parquet('{parquet_path}')")
    con.close()

    logger.info("🏁 Agrégation Gold et chargement DuckDB terminés avec succès !")

# ==========================================
# EXÉCUTION
# ==========================================
if __name__ == "__main__":
    client = create_minio_client()
    ensure_bucket_exists(client, MINIO_BUCKET_GOLD)
    process_silver_to_gold(client)