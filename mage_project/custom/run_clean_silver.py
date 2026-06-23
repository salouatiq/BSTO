import subprocess

if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

@custom
def execute_custom_script(*args, **kwargs):
    print("🌍 Ordre reçu : Lancement de l'extraction vers Bronze...")
    
    # On lance ton script Python exactement comme tu le ferais dans le terminal
    result = subprocess.run(["python", "scripts/silver_clean.py"], capture_output=True, text=True)
    
    # On affiche ce que le script a fait
    print(result.stdout)
    
    # S'il y a eu un problème rouge, on fait échouer le bloc Mage
    if result.returncode != 0:
        raise Exception(f"❌ Erreur lors de l'exécution : {result.stderr}")
        
    return {}