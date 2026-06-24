import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

@custom
def execute_custom_script(*args, **kwargs):
    print("🧹 Ordre reçu : Nettoyage et enrichissement de la population vers Silver...")
    
    result = subprocess.run(["python", "scripts/silver_clean_population.py"], capture_output=True, text=True)
    print(result.stdout)
    
    if result.returncode != 0:
        raise Exception(f"❌ Erreur lors de l'exécution : {result.stderr}")
        
    return {}