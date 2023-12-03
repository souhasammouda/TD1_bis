import uvicorn
import sqlite3
import logging
import re
from fastapi import FastAPI, HTTPException
from fastapi import Depends
from pydantic import BaseModel


file_path = 'D:\SOA\client.txt'
with open(file_path, 'r') as file:
    client_info_text = file.read()

# Extraction des informations pertinentes à l'aide d'expressions régulières
nom = re.search(r"Nom du Client: (.+)", client_info_text).group(1)
adresse = re.search(r"Adresse: (.+)", client_info_text).group(1)
email = re.search(r"Email: (.+)", client_info_text).group(1)
telephone = re.search(r"Numero de Telephone: (.+)", client_info_text).group(1)
montant_pret = int(re.search(r"Montant du Pret Demande: (\d+)", client_info_text).group(1))
duree_pret = int(re.search(r"Duree du Pret: (\d+)", client_info_text).group(1))
revenu_mensuel = int(re.search(r"Revenu Mensuel: (\d+)", client_info_text).group(1))
depenses_mensuelles = int(re.search(r"Depenses Mensuelles: (\d+)", client_info_text).group(1))
description_propriete = re.search(r"Description de la Propriete: (.+)", client_info_text).group(1)

# Changement du format de code pour l'insertion dans la base de données
file_content = f"'{nom}','{nom}','{adresse}','{email}','{telephone}',{montant_pret},{duree_pret},{revenu_mensuel},{depenses_mensuelles},'{description_propriete}'"

app = FastAPI()
logger = logging.getLogger(__name__)

def sqlite_to_dict(database_path, table_name):
    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()
    
    # Insertion des valeurs du nouveau client dans la base de données
    cursor.execute(f'INSERT INTO {table_name} VALUES({file_content})')
    connection.commit() 
    cursor.execute(f'SELECT * FROM {table_name}')
    
    column_names = [description[0] for description in cursor.description]
    
    rows = cursor.fetchall()

    connection.close()
    
    # changement des données de la base vers un format dict
    result_dict = {}
    for row in rows:
        row_dict = dict(zip(column_names, row))
        unique_key = row_dict["nom"]  
        result_dict[unique_key] = row_dict
    
    return result_dict

# Connexion à la base de données SQLite, insertion des données du client et récupération de toutes les données sous forme de dictionnaire
database_path = r"D:\SOA\clients.db"
table_name = "clients"
clients_data = sqlite_to_dict(database_path, table_name)

# Debug valeurs du dictionnaire 
# for key, value in clients_data.items():
#     print(f'"{key}": {value},')


class ClientData(BaseModel):
    nom: str
    adresse: str
    email: str
    telephone: str

class FinancialData(BaseModel):
    montant_pret: int
    duree_pret: int
    revenu_mensuel: int
    depenses_mensuelles: int

class PropertyData(BaseModel):
    description_propriete: str
    montant_pret: int

@app.get("/get_personal_data/{client_id}", response_model=ClientData)
async def get_personal_data(client_id: str):
    client = clients_data.get(client_id, {})
    return client

@app.get("/get_financial_data/{client_id}", response_model=FinancialData)
async def get_financial_data(client_id: str):
    client = clients_data.get(client_id, {})
    financial_data = {
        "montant_pret": client.get("montant_pret", 0),
        "duree_pret": client.get("duree_pret", 0),
        "revenu_mensuel": client.get("revenu_mensuel", 0),
        "depenses_mensuelles": client.get("depenses_mensuelles", 0)
    }
    return financial_data

@app.get("/get_property_data/{client_id}", response_model=PropertyData)
async def get_property_data(client_id: str):
    client = clients_data.get(client_id, {})
    property_data = {
        "description_propriete": client.get("description_propriete", ""),
        "montant_pret": client.get("montant_pret", 0)
    }
    return property_data

@app.post("/check_solvency", response_model=str)
async def check_solvency(financial_data: FinancialData):
    try:
        x = (financial_data['revenu_mensuel'] - financial_data['depenses_mensuelles']) * 12
        y = financial_data['montant_pret'] / financial_data['duree_pret']

        if x >= y:
            return "Le client est solvable."
        else:
            return "Le client n'est pas solvable."
    except Exception as e:
        print(f"An exception occurred in check_solvency: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


@app.post("/evaluate_property", response_model=str)
async def evaluate_property(property_data: PropertyData):
    try:
        description_propriete = property_data['description_propriete']
        montant_pret = property_data['montant_pret']

        valeur_estimee = 100000
        if "jardin" in description_propriete:
            valeur_estimee += 10000
        if "piscine" in description_propriete:
            valeur_estimee += 50000
        if "centre-ville" in description_propriete:
            valeur_estimee += 5000

        is_property_worth_loan = valeur_estimee >= montant_pret

        if is_property_worth_loan:
            return "La propriété vaut le montant du prêt."
        else:
            return "La propriété ne vaut pas le montant du prêt."
    except Exception as e:
        print(f"An exception occurred in evaluate_property: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


@app.post("/make_decision", response_model=str)
async def make_decision(client_id: str, property_data: PropertyData = Depends(get_property_data)):
    try:
        solvability_result = await check_solvency(await get_financial_data(client_id))
        evaluation_result = await evaluate_property(property_data)

        if solvability_result == "Le client est solvable." and evaluation_result == "La propriété vaut le montant du prêt.":
            return "L'acceptation de l'attribution du prêt."
        else:
            decision = "Refus de l'attribution du prêt."
            if solvability_result != "Le client est solvable.":
                decision += " Le client n'est pas solvable."
            if evaluation_result != "La propriété vaut le montant du prêt.":
                decision += " La propriété ne vaut pas le montant du prêt."
            return decision
    except Exception as e:
        print(f"An exception occurred: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

if __name__ == "_main_":
    uvicorn.run("_main_:app", host="127.0.0.1", port=8080, reload=True, workers=2)