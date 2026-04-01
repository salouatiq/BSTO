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