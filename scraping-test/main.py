#!/usr/bin/env python3

import math
import time
import pandas as pd
import requests

# URL de base identifiée dans votre cURL
url = "https://www.topuniversities.com/rankings/endpoint"

# Headers extraits de votre commande cURL
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.topuniversities.com/asia-university-rankings?tab=indicators&sort_by=rank&order_by=asc",
    "sec-ch-ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
}

# Paramètres de base
items_per_page = 100  # On augmente à 100 par page pour faire moins de requêtes
all_universities = []
page = 0
total_items = None

print("Début du scraping...")

while True:
    params = {
        "nid": "4085811",
        "page": page,
        "items_per_page": items_per_page,
        "tab": "indicators",
        "region": "",
        "countries": "",
        "cities": "",
        "search": "",
        "star": "",
        "sort_by": "rank",
        "order_by": "asc",
        "program_type": "",
        "scholarship": "",
        "fee": "",
        "english_score": "",
        "academic_score": "",
        "mix_student": "",
        "loggedincache": "",
        "study_level": "",
        "subjects": "",
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Erreur HTTP {response.status_code} à la page {page}")
        break

    data = response.json()

    # Récupération de la liste des universités dans le JSON
    # (selon la structure habituelle du JSON de TopUniversities)
    nodes = data.get("score_nodes", [])

    if not nodes:
        print("Plus aucune donnée retournée.")
        break

    # Si c'est le premier passage, on calcule le nombre total de pages
    if total_items is None and "total_scores_records" in data:
        total_items = int(data["total_scores_records"])
        total_pages = math.ceil(total_items / items_per_page)
        print(
            f"Total d'universités à récupérer : {total_items} ({total_pages} pages)"
        )

    # Extraction des données utiles
    for node in nodes:
        all_universities.append(
            {
                "Rank": node.get("rank_display"),
                "Title": node.get("title"),
                "Country": node.get("country"),
                "City": node.get("city"),
                "Overall Score": node.get("overall_score"),
                "NID": node.get("nid"),
                # Remarque : si d'autres indicateurs vous intéressent (ex: ratio étudiants/profs),
                # vous pourrez lire les clés directement dans l'objet node.
            }
        )

    print(
        f"Page {page + 1} récupérée ({len(nodes)} universités ajoutées)..."
    )

    page += 1

    # Pause de courtoisie pour éviter le blocage IP
    time.sleep(0.5)

# Convertir en Dataframe Pandas et exporter en CSV
df = pd.DataFrame(all_universities)
df.to_csv("asia_university_rankings.csv", index=False, encoding="utf-8")

print(
    f"\nScraping terminé avec succès ! {len(df)} universités enregistrées dans 'asia_university_rankings.csv'."
)
