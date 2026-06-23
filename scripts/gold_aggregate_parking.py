#!/usr/bin/env python3
"""
Script Gold : Lit les données nettoyées depuis PostgreSQL (Silver),
calcule les indicateurs clés (KPIs) des parkings,
et les stocke dans DuckDB (Gold) pour l'analyse.
"""

import os
import logging
import pandas as pd
import duckdb
from sqlalchemy import create_engine
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
PG_USER = "admin"
PG_PASSWORD = "briancon2026"
PG_HOST = "localhost" if MINIO_ENDPOINT == "localhost:9000" else "postgres"
PG_PORT = "5432"
PG_DB = "briancon_db"

DUCKDB_PATH = "analytics/db/briancon.duckdb"

def aggregate_parking():
    logger.info("🥇 Lancement de l'agrégation Gold pour les parkings...")
    
    # 1. Extraction depuis PostgreSQL (Silver)
    engine = create_engine(f'postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}')
    
    try:
        df = pd.read_sql_table('parking_silver', engine)
        logger.info(f"📥 {len(df)} lignes lues depuis la zone Silver.")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la lecture dans PostgreSQL : {e}")
        return

    # 2. Transformation / Agrégation (Gold)
    # Grouper par type de tarification (fee)
    kpi_df = df.groupby('fee').agg(
        nombre_parkings=('osm_id', 'count'),
        capacite_totale=('capacity', 'sum')
    ).reset_index()
    
    # Remplacer les valeurs inconnues par un label propre
    kpi_df['fee'] = kpi_df['fee'].replace({'unknown': 'Non renseigné', 'yes': 'Payant', 'no': 'Gratuit'})
    
    # Ajouter une colonne pour marquer la date de calcul
    kpi_df['date_calcul'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    
    logger.info(f"📊 KPIs calculés :\n{kpi_df}")

    # 3. Sauvegarde dans DuckDB (Gold)
    os.makedirs(os.path.dirname(DUCKDB_PATH), exist_ok=True)
    conn = duckdb.connect(DUCKDB_PATH)
    
    # Enregistrement du DataFrame dans DuckDB
    conn.execute("CREATE OR REPLACE TABLE parking_kpi AS SELECT * FROM kpi_df")
    conn.close()
    
    logger.info("✅ Succès ! Table 'parking_kpi' créée dans DuckDB (Zone Gold).")

if __name__ == "__main__":
    aggregate_parking()