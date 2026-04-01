# Script : load_to_duckdb.py
# Ce script lit les données de stationnement du jour (niveau BRONZE), calcule le taux d'occupation, et les charge dans une table GOLD dans DuckDB.
# C'est ici que la magie de la transformation opère, et où nous pouvons faire du SQL pour enrichir nos données.
# Note 1: 
# ------
    # Assurez-vous que les données de stationnement du jour sont bien présentes dans le dossier "data/parking_status/year=2026/month=04/day=01/" avant d'exécuter ce script.     
    # Pour exécuter ce script, utilisez la commande : python scripts/load_to_duckdb.py
    # DuckDB est un moteur de base de données en mémoire qui supporte SQL et peut lire directement des fichiers JSON, CSV, Parquet, etc. C'est parfait pour notre cas d'usage local.
    # Ce script est un exemple de transformation simple. En production, vous pourriez vouloir ajouter des étapes de nettoyage, de validation, ou d'enrichissement plus complexes.
# Assurez-vous d'avoir installé DuckDB dans votre environnement Python : pip install duckdb
# Le résultat final sera une table "daily_occupancy" dans DuckDB avec le taux d'occupation calculé pour chaque parking, que vous pourrez ensuite interroger ou visualiser avec des outils comme Metabase.

# Note 2: 
# ------
# Ce script suppose que les données de stationnement sont au format JSON et suivent la structure définie dans le script d'extraction (extract_api.py). Si la structure change, vous devrez adapter la requête SQL en conséquence.
    # Ce script est conçu pour être exécuté quotidiennement, idéalement après l'extraction des données de stationnement. Vous pouvez automatiser son exécution avec un cron job ou un scheduler comme Airflow pour garantir que votre table GOLD est toujours à jour avec les dernières données.
    # N'oubliez pas de vérifier les permissions d'accès au dossier "data/gold/" pour que DuckDB puisse créer et écrire dans le fichier de base de données.
    # Ce script est un point de départ pour votre pipeline de données. Vous pouvez l'enrichir avec des fonctionnalités supplémentaires comme la gestion des erreurs, les notifications en cas d'échec, ou l'intégration avec d'autres sources de données pour un enrichissement plus complet.
    # N'hésitez pas à consulter la documentation de DuckDB pour découvrir toutes les fonctionnalités SQL avancées que vous pouvez utiliser pour transformer et analyser vos données de stationnement de manière encore plus puissante !
# Documentation : https://duckdb.org/docs/sql/overview

import duckdb
import os

# Connexion à la base de données locale (un simple fichier .db)
db_path = "data/gold/briancon_observatory.duckdb"
con = duckdb.connect(db_path)

def transform_and_load():
    print("--- 🔄 Transformation vers le niveau GOLD ---")
    
    # On utilise DuckDB pour lire tous les JSON du jour et calculer le taux d'occupation
    # C'est ici que la puissance de SQL intervient
    query = """
    CREATE OR REPLACE TABLE daily_occupancy AS
    SELECT 
        id_parking,
        nom,
        places_libres,
        capacite_totale,
        -- Calcul du taux d'occupation
        ROUND(((capacite_totale - places_libres) / CAST(capacite_totale AS DOUBLE)) * 100, 2) as taux_occupation_pct,
        date_obs
    FROM read_json_auto('data/parking_status/year=2026/month=04/day=01/*.json');
    """
    
    con.execute(query)
    
    # Vérification
    result = con.execute("SELECT nom, taux_occupation_pct FROM daily_occupancy").fetchall()
    for row in result:
        print(f"📊 Parking : {row[0]} | Occupation : {row[1]}%")

if __name__ == "__main__":
    transform_and_load()