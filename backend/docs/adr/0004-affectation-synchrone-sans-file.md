# ADR-0004 — Le run s'exécute dans la requête HTTP, sans file de tâches

Statut : accepté · Date : 2026-10-26

## Contexte
Le réflexe pour « lancer une simulation » est un worker (Celery, RQ) et une file (Redis), avec statut à interroger. Cela ajoute deux services au Docker Compose, un déploiement de plus, et des états intermédiaires à gérer dans les interfaces.

## Mesure
Banc d'essai (`docs/benchmark-results.md`) : préparation + affectation + vérification de stabilité pour 1 000 × 100 ≈ 16 ms ; 10 000 × 1 000 ≈ 0,2 s ; 50 000 × 1 000 ≈ 1,1 s. Budget fixé : 500 ms, qui doit aussi couvrir la base (lecture de la cohorte, écriture du snapshot et des 1 000 affectations : à mesurer dès que l'API existe, attendu 100 à 300 ms).

## Décision
`POST /admin/runs` calcule et persiste dans la requête, répond `201` avec le run complet. Persistance des 1 000 affectations en un seul `INSERT` multi-lignes dans la même transaction.

Exception : la **publication** notifie la cohorte. Mille jetons FCM appelés un par un dans la requête seraient inacceptables ; l'API abonne chaque appareil au sujet FCM `results` à l'enregistrement et envoie **un seul** message de sujet, en `BackgroundTask` FastAPI pour ne pas lier la réponse à la disponibilité de FCM.

## Conséquences
- `+` Un service, un déploiement, zéro état « en cours » ; le mode « et si » est instantané.
- `+` Erreur du moteur ⇒ transaction annulée, `status = failed`, message remonté à l'admin.
- `−` Plafond : au-delà de ≈ 10 000 étudiants × 1 000 universités (dix fois le besoin), le calcul seul approche le budget ; passer alors à un `BackgroundTask` puis à une file. Le service `runs.py` est le seul point à modifier.
