import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

@custom
def execute_custom_script(*args, **kwargs):
    print("📊 Ordre reçu : Création des KPIs d'hébergement vers Gold...")
    
    result = subprocess.run(["python", "scripts/gold_aggregate_accommodation.py"], capture_output=True, text=True)
    print(result.stdout)
    
    if result.returncode != 0:
        raise Exception(f"❌ Erreur lors de l'exécution : {result.stderr}")
        
    return {}