# Script d'extraction et de validation des données de stationnement de Briançon
# Ce script simule l'extraction des données de stationnement depuis une API de la ville, valide la structure des données selon un modèle défini, et les charge dans un bucket MinIO (équivalent local de GCS).
# Note 1:       
# ------
    # Assurez-vous d'avoir un serveur MinIO en cours d'exécution localement (par exemple, via Docker) et que les variables d'environnement sont correctement configurées dans un fichier .env.
    # Pour exécuter ce script, utilisez la commande : python scripts/extract_api.py 
    # Ce script est un point de départ pour votre pipeline d'extraction. En production, vous pourriez vouloir remplacer la simulation de données par un appel réel à l'API de la ville de Briançon, et ajouter des fonctionnalités comme la gestion des erreurs, les notifications en cas d'échec, ou l'intégration avec d'autres sources de données.
# Note 2:
# ------
    # Ce script utilise Pydantic pour la validation des données, ce qui garantit que les données respectent une structure définie avant d'être chargées dans MinIO. Cela correspond à une bonne pratique de qualité des données, surtout dans le secteur public où la fiabilité des données est cruciale.
    # N'hésitez pas à consulter la documentation de Pydantic pour découvrir toutes les fonctionnalités de validation avancées que vous pouvez utiliser pour garantir la qualité de vos données de stationnement !
# Documentation : https://pydantic.dev/

import os
import json
import boto3
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

# --- CONFIGURATION ---
BUCKET_NAME = os.getenv("BUCKET_NAME", "briancon-raw")
ENDPOINT = f"http://{os.getenv('MINIO_ENDPOINT', 'localhost:9000')}"

# Modèle de données pour la validation (Qualité Secteur Public)
class ParkingStatus(BaseModel):
    id_parking: str
    nom: str
    commune: str
    places_libres: int
    capacite_totale: int
    date_obs: datetime
    licence: str = "Etalab-2.0"

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=ENDPOINT,
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY")
    )

def upload_to_minio(data):
    s3 = get_s3_client()
    
    # Création du chemin partitionné (Clé de l'objet)
    # Exemple: parking/year=2026/month=04/day=01/extract_1430.json
    now = datetime.now()
    partition_path = now.strftime("year=%Y/month=%m/day=%d")
    file_name = now.strftime("extract_%Y%m%d_%H%M%S.json")
    full_path = f"parking_status/{partition_path}/{file_name}"
    
    # Upload
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=full_path,
        Body=json.dumps(data, default=str),
        ContentType='application/json'
    )
    print(f"✅ Données de Briançon sauvegardées sous : {full_path}")

if __name__ == "__main__":
    # Simulation d'une donnée reçue de l'API de la ville
    sample_data = {
        "id_parking": "P1_VAUBAN",
        "nom": "Parking Cité Vauban",
        "commune": "Briançon",
        "places_libres": 45,
        "capacite_totale": 150,
        "date_obs": datetime.now().isoformat()
    }
    
    try:
        validated = ParkingStatus(**sample_data)
        upload_to_minio(validated.model_dump())
    except ValidationError as e:
        print(f"❌ Erreur Qualité Donnée : {e}")