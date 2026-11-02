# Stratégie de tests du backend

Une commande lance tout : `pnpm test` (ou `uv run pytest`), 39 tests, ≈ 15 s, sans Docker ni base à installer.

Les tests suivent une pyramide : beaucoup de tests rapides et précis en bas, un seul scénario lent et large en haut.
Chaque niveau couvre ce que le niveau inférieur **ne peut pas voir**, sans répéter ce qu'il prouve déjà.

| Niveau | Fichier | Nombre | Durée | Ce qu'il prouve |
|---|---|---:|---:|---|
| Unitaire | `packages/engine/tests`, `packages/generator/tests` | 23 | < 1 s | Moteur de règles, Gale-Shapley et Boston, vérification de stabilité, reproductibilité du générateur, empreintes de référence |
| Fonctionnel | `apps/api/tests/functional` | 15 | ≈ 3 s | Chaque règle métier et de sécurité exposée par l'API |
| End-to-end | `apps/api/tests/e2e` | 1 scénario | ≈ 5 s (≈ 1 min en CI avec le build Docker) | La plateforme démarrée, pilotée en HTTP comme le feront le web et le mobile |
| Performance | `packages/engine/benchmark/run.py` | 68 vérifications | ≈ 6 s | Temps de calcul par algorithme, de 1 000 à 50 000 étudiants, et comparatif chiffré |
| Conventions | `.pre-commit-config.yaml` | – | – | Messages de commit, lint, format, absence de clé privée |

## Unitaire : le moteur, isolé

**Pourquoi ce niveau.** Le sujet impose au minimum des tests sur le moteur de règles, les algorithmes (dont la
vérification automatique de stabilité) et la reproductibilité du générateur. `packages/engine` est un module pur (aucune I/O),
donc testable sans base ni serveur, en millisecondes : une régression est localisée à la fonction près.

**Ce qui est couvert.** Validation des configurations (toutes les erreurs d'un coup, fautes de frappe refusées),
seuils éliminatoires, bonus, ajout d'un critère sans code, départage total, pondérations par université ;
Gale-Shapley stable sur les six scénarios, Boston instable et détecté comme tel, paires bloquantes sur une instance
construite à la main ; rejeu insensible à l'ordre des entrées ; équité de l'échelle d'anglais ; générateur
reproductible.

**Pourquoi des empreintes de référence.** `test_golden_hashes_pin_engine_behaviour` casse dès que le moteur change de
comportement, même subtilement. C'est voulu : on incrémente alors `ENGINE_VERSION`, sinon un rejeu ancien ne serait
plus explicable.

## Fonctionnel : l'API, une règle par test

**Pourquoi ce niveau.** Le moteur ne voit ni HTTP, ni sessions, ni permissions, ni base. Or l'essentiel des
exigences de sécurité du sujet (comptes distincts, permissions vérifiées côté serveur, OWASP) vit là.

**Comment.** `TestClient` de FastAPI (requêtes HTTP réelles, en processus) contre une base SQLite en mémoire **neuve
pour chaque test** : aucun test ne dépend d'un autre, l'ordre d'exécution est indifférent. Pas de mock : le moteur
est pur et la base est une vraie base SQL, on teste donc le vrai comportement.

**Ce qui est couvert.**
- Sécurité : routes fermées sans session ; rôles vérifiés côté serveur, un étudiant n'atteint pas `/admin` (OWASP A01) ;
  message d'échec identique que le compte existe ou non, puis blocage après 5 échecs (A07) ; cookie `HttpOnly`
  `SameSite=Lax` ; jeton révoqué à la déconnexion ; en-têtes de sécurité.
- Vœux : exactement 5, distincts, existants ; ordre conservé ; un étudiant ne touche que les siens ; fermés après
  publication.
- Règles : configuration invalide refusée avec toutes ses erreurs ; versions identifiées par leur contenu (renommer
  ne crée pas de version).
- Runs : résultat invisible avant publication ; Boston non publiable ; explication par vœu cohérente avec
  l'affectation ; rejeu identique même après modification de la base ; comparaison « et si ».
- Contrat base → moteur : ce que le moteur lit en base est, au bit près, ce que le générateur a produit. C'est le
  vrai contrat du rejeu (architecture §4).

## End-to-end : ce qui sera déployé

**Pourquoi ce niveau.** C'est le seul qui exerce ce que les niveaux inférieurs remplacent : l'image Docker de
production, PostgreSQL (et non SQLite), le chargement du jeu de démo complet au démarrage (1 000 étudiants,
100 universités), le serveur uvicorn, les deux transports de session (Bearer pour le mobile, cookie pour le web).
Il vérifie aussi le **test du nouvel arrivant** : si `docker compose up` ne donne pas une plateforme utilisable, la CI
échoue.

**Pourquoi un seul scénario.** Un test de bout en bout est lent et casse pour beaucoup de raisons. Il couvre donc le
seul parcours critique, une campagne d'affectation complète : un étudiant saisit ses vœux, le même compte les retrouve
depuis un autre client, l'admin lance les deux algorithmes et les compare, publie, l'étudiant lit son résultat
expliqué, ses vœux sont figés, le run se rejoue à l'identique, la déconnexion révoque le jeton. Le détail de chaque
règle reste au niveau fonctionnel.

**Mesure de performance de bout en bout.** Le sujet demande des performances mesurées ; le banc mesure le moteur seul.
Le test e2e chronomètre `POST /admin/runs` sur la cohorte complète (lecture de la base, moteur, écriture des 1 000
affectations expliquées) et affiche le résultat dans le journal CI. Mesuré en local : ≈ 190 ms sur PostgreSQL
(Docker), ≈ 315 ms sur SQLite. L'assertion est à 2 s (`BUDGET_MS`), quatre fois le budget de 500 ms de l'ADR-0004,
pour ne pas échouer au hasard sur un runner partagé : elle attrape une régression d'un ordre de grandeur, le chiffre
précis se lit dans le journal.

**Deux modes.** Sans variable, le test démarre lui-même uvicorn sur une base SQLite jetable : il tourne partout avec
`uv run pytest`. En CI, `E2E_BASE_URL` le dirige vers la plateforme lancée par `docker compose up --build`. Il exige une
instance **neuve** : le scénario publie des résultats, ce qui ferme les vœux.

## Performance : le banc

`packages/engine/benchmark/run.py` est une suite d'assertions (68 vérifications : invariants, stabilité, rejeu, détection de
l'instabilité de Boston, critère sans code) et un chronométrage par algorithme et par taille de cohorte. Il tourne en
CI sur chaque PR ; le rapport est publié en artefact du pipeline, pas commité : les temps varient d'une machine à
l'autre, seules les vérifications sont comparables. Protocole : [`benchmark-protocol.md`](benchmark-protocol.md).

## Conventions

Les hooks pre-commit (format, lint, clés privées, message de commit) tournent localement à chaque commit, et la CI les
rejoue sur tout le dépôt : un hook contourné localement (`--no-verify`) est rattrapé en PR. Détail dans
[`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Lancer une partie seulement

```bash
uv run pytest packages                                          # unitaires (moteur, générateur)
uv run pytest apps/api/tests/functional                         # fonctionnels
uv run pytest -k replay                                         # les tests dont le nom contient « replay »
uv run pytest packages/engine/tests/test_engine.py::test_config_id_tracks_content
uv run pytest apps/api/tests/e2e -s                             # affiche le temps mesuré du run
E2E_BASE_URL=http://localhost:8000 uv run pytest apps/api/tests/e2e  # contre une plateforme Docker neuve
pnpm bench                                                      # banc, réécrit docs/technical/benchmark-results.md
```

## Pas encore couvert, et quand l'ajouter

| Manque | Quand |
|---|---|
| Test de contrat OpenAPI (schéma figé, comparé en CI) | dès que le web et le mobile génèrent leur client depuis `/openapi.json` |
| Validation du fichier des 100 universités réelles par un schéma JSON | avec le fichier de données |
| Mesure de couverture (`pytest-cov`) | si l'équipe veut un seuil en CI |
| Charge concurrente (vœux saisis en masse à l'ouverture) | si la démo le demande |
| Tests de l'application mobile (logique et interface) | dans la partie mobile, exigés par le sujet |
