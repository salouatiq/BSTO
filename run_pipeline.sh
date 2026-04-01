#!/bin/bash
# Script pour exécuter le pipeline BSTO complet
# Architecture Medallion : Bronze → Silver → Gold

echo "🚀 Démarrage du pipeline BSTO..."

# Activer l'environnement virtuel
source .venv/Scripts/activate

# Étape 1 : Extraction API → MinIO Bronze
echo "📥 Étape 1 : Extraction des données brutes vers Bronze"
python scripts/extract_weather.py

# Étape 2 : Nettoyage Bronze → Silver
echo "🧹 Étape 2 : Nettoyage des données vers Silver"
python scripts/silver_clean.py

# Étape 3 : Agrégation Silver → Gold + DuckDB
echo "📊 Étape 3 : Agrégation des données vers Gold"
python scripts/gold_aggregate.py

echo "✅ Pipeline terminé avec succès !"
echo "📈 Vérifiez vos données dans DuckDB :"
echo "python -c \"import duckdb; con = duckdb.connect('data/duckdb/briancon.duckdb'); print(con.execute('SELECT * FROM weather_daily LIMIT 5').fetchall())\""