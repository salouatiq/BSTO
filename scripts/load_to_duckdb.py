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