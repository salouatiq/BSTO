#!/usr/bin/env python3
"""
Script Gold : Lit les données depuis PostgreSQL (Silver),
sélectionne les KPIs de population, sauvegarde en Parquet dans MinIO (Gold),
et stocke dans DuckDB.
"""

import os
import logging
import pandas as pd
import duckdb
from minio import Minio
from sqlalchemy import create_engine
import pyarrow
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
MINIO_BUCKET_GOLD = "briancon-gold"

PG_USER = "admin"
PG_PASSWORD = "briancon2026"
PG_HOST = "localhost" if MINIO_ENDPOINT == "localhost:9000" else "postgres"
PG_PORT = "5432"
PG_DB = "briancon_db"

GOLD_DIR = "analytics/temp_export"
DUCKDB_DIR = "analytics/db"
DUCKDB_PATH = f"{DUCKDB_DIR}/briancon.duckdb"

def aggregate_population():
    logger.info("🥇 Lancement de l'export Gold pour la population...")
    
    # 1. Extraction depuis PostgreSQL (Silver)
    engine = create_engine(f'postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}')
    
    try:
        df = pd.read_sql_table('population_silver', engine)
    except Exception as e:
        logger.error(f"❌ Erreur de lecture de la table PostgreSQL : {e}")
        return

    # 2. Préparation des KPIs (Gold)
    # On sélectionne uniquement les colonnes essentielles pour notre Indice de Pression
    kpi_df = df[['code', 'nom', 'population', 'surface_km2', 'densite_km2', 'date_extraction']].copy()
    
    # 3. Sauvegarder en parquet local
    os.makedirs(GOLD_DIR, exist_ok=True)
    parquet_path = os.path.join(GOLD_DIR, "population_gold.parquet")
    kpi_df.to_parquet(parquet_path, index=False, engine='pyarrow')
    
    # 4. Uploader vers MinIO (Gold) dans son sous-dossier
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)
    if not client.bucket_exists(MINIO_BUCKET_GOLD):
        client.make_bucket(MINIO_BUCKET_GOLD)
        
    client.fput_object(MINIO_BUCKET_GOLD, "population/population_gold.parquet", parquet_path)
    logger.info("☁️ Fichier Parquet sécurisé dans MinIO Gold (dossier population/)")

    # 5. Sauvegarde dans DuckDB
    os.makedirs(DUCKDB_DIR, exist_ok=True)
    conn = duckdb.connect(DUCKDB_PATH)
    conn.execute(f"CREATE OR REPLACE TABLE population_kpi AS SELECT * FROM read_parquet('{parquet_path}')")
    conn.close()
    
    logger.info("✅ Succès ! Table 'population_kpi' créée dans DuckDB.")

if __name__ == "__main__":
    aggregate_population()


# La zone Gold pour la population est un peu particulière : comme nous n'avons récupéré les données que pour une seule ville (Briançon), nous n'avons pas besoin de faire des calculs d'agrégation complexes (comme des moyennes ou des sommes) comme nous l'avons fait pour la météo ou les parkings.
# L'objectif de ce script sera surtout de sélectionner les colonnes les plus pertinentes (nos KPIs), de les convertir au format Parquet pour des performances optimales, et de les ranger soigneusement dans MinIO et DuckDB.