# Architecture backend — Plateforme de mobilité internationale

> Périmètre : tout ce qui est derrière l'API. Le site web et l'application mobile sont deux clients de cette API.
> Le moteur d'affectation est **implémenté, testé et mesuré** (`packages/engine`, `packages/generator`, `benchmark-results.md`) ;
> l'API existe en preuve de concept (`apps/api`, voir `testing.md`) ; la base et le déploiement sont spécifiés pour être construits tels quels.
> Ce document a été relu par un développeur extérieur ; ses remarques sont intégrées, et les questions qui restent
> ouvertes sont listées en §14. Stack retenue : Python, FastAPI, PostgreSQL (ADR-0001, accepté).

## 1. Ce que le sujet impose au backend, et la réponse retenue

| Exigence du sujet | Réponse | Section |
|---|---|---|
| Règles modifiables par l'administration sans développeur ; nouveau critère sans toucher au code | Configuration JSON interprétée (poids, seuils éliminatoires, bonus/malus, départage, pondérations par université) ; attributs libres sur l'étudiant et sur l'université | §5, ADR-0002 |
| Configurations versionnées, rejeu d'une affectation à l'identique | Configurations immuables identifiées par l'empreinte de leur contenu ; chaque run conserve le snapshot exact de ses entrées, sa graine et la version du moteur | §6, ADR-0003 |
| ≥ 2 algorithmes dont Gale-Shapley ; comparatif chiffré ; stabilité vérifiée | Gale-Shapley (acceptation différée) + Boston (acceptation immédiate) ; métriques et détecteur de paires bloquantes indépendants des algorithmes | §5.3, ADR-0006 |
| Résultat expliqué : « pourquoi ce vœu-là et pas le précédent » | Explication structurée par vœu, calculée pendant le run, vérifiée, stockée avec l'affectation | §5.4 |
| Mode « et si » : deux configurations côte à côte | Deux runs, comparés côté serveur (métriques + étudiants déplacés) | §7 |
| Même backend pour le web et le mobile ; vœux synchronisés | Une seule API REST JSON ; les vœux n'existent que côté serveur | §7, §8 |
| Catalogue consultable hors connexion ; notification à la publication | `ETag` sur le catalogue ; push FCM par sujet (un seul appel) | §8 |
| Comptes étudiant/admin distincts, permissions côté serveur, OWASP Top 10 | Sessions opaques, contrôle de rôle par dépendance, routes étudiant sans identifiant, SPA servie par l'API | §9, ADR-0005 |
| Temps de calcul mesuré pour 1 000 étudiants, par algorithme | Banc d'essai reproductible ; budget 500 ms par run, mesuré ≈ 16 ms hors base | §10, ADR-0004 |
| Tests moteur / algorithmes / générateur en une commande ; CI/CD ; installation en une commande | `pytest` ; GitHub Actions ; Docker Compose avec jeu de démo chargé au démarrage | §11 |
| Données réelles sourcées, photos créditées | Schéma JSON de `data/universities.json` vérifié par un test | §11 |

## 2. Vue d'ensemble

```
        Navigateur (SPA servie par l'API)        Mobile (natif)
                    │        HTTPS / JSON              │
                    └───────────────┬──────────────────┘
                                    ▼
      ┌──────────────────────────────────────────┐        ┌───────────────┐
      │ API — FastAPI (un seul déployable)       │  SQL   │ PostgreSQL 16 │
      │  routers  → validation, auth, rôles      │◀──────▶│               │
      │  services → snapshot, run, publication   │        └───────────────┘
      │  engine   → module pur, sans I/O         │──1 appel──▶ FCM (sujet « results »)
      └──────────────────────────────────────────┘
```

Trois couches, une dépendance dans un seul sens : `routers → services → engine`.

- **engine** (`packages/engine`) ne connaît ni HTTP ni base : il prend (universités, étudiants, configuration) et rend (affectation, planchers, métriques, explications). Il est testable et benchable sans rien démarrer : c'est ce qui a été mesuré.
- **services/** orchestre : charger la configuration, figer le snapshot (dont le tirage au sort), appeler le moteur, persister, publier, notifier.
- **routers/** expose l'API : schémas Pydantic (validation aux frontières), authentification, autorisation par rôle.

Pas de file de tâches, pas de cache externe, pas de second service : un run 1 000 × 100 prend ≈ 16 ms hors base (§10) et s'exécute dans la requête HTTP. La notification de publication part en tâche de fond FastAPI (un appel FCM).

## 3. Stack retenue

| Besoin | Choix | Pourquoi (détail en ADR-0001) |
|---|---|---|
| Langage / framework | Python 3.12 (CI et production ; le moteur tourne de 3.10 à 3.14), FastAPI, Pydantic v2 | OpenAPI généré automatiquement, validation déclarative, peu de code |
| Base | PostgreSQL 16, SQLAlchemy 2, Alembic | JSONB pour configurations, snapshots, attributs libres ; contraintes d'intégrité en base ; migrations versionnées |
| Mots de passe / sessions | argon2-cffi, sessions opaques en base | ADR-0005 |
| Tests / qualité | pytest, ruff (lint + format), pre-commit | Une commande pour tout |
| Conteneurs / CI / CD | Docker Compose, GitHub Actions, Fly.io (API, machine qui ne s'endort pas) + Neon (Postgres), offres gratuites | Déploiement à chaque merge sur `main` ; Render gratuit écarté : mise en veille ≈ 50 s, fatale en démo |
| Push mobile | FCM HTTP v1, envoi par sujet | Un appel pour toute la cohorte, iOS et Android |

Le moteur n'utilise que la bibliothèque standard : il se teste et se mesure sans base ni serveur.

## 4. Modèle de données

```
users          id uuid PK · email unique · password_hash · role ∈ {student, admin} · created_at
sessions       token_hash text PK · user_id→users · created_at · expires_at · user_agent        ← ADR-0005
students       user_id PK→users · gpa numeric(3,2) · english_test ∈ {TOEIC, IELTS} · english_score numeric
               · associative int · attributes jsonb '{}'            ← critères ajoutés sans code (projet perso, absences, lottery…)
universities   id text PK (slug) · name · city · country · continent · lat · lng
               · description · fields text[] · teaching_language · local_life
               · cost_of_living jsonb {housing, food, transport, monthly_total, source}
               · photos jsonb [{url, author, license, alt}]           ← crédits obligatoires (règle d'or du sujet)
               · capacity int · min_gpa numeric · min_cefr text       ← conditions d'accès (fictif cohérent)
               · attributes jsonb '{}'                                ← seuils ajoutés sans code (ex. min_associative)
               · stay jsonb {duration_months, period, fees} · sources jsonb [{label, url}] · updated_at
wishes         student_id→students · rank smallint 1..5 · university_id→universities · updated_at
               PK(student_id, rank) · UNIQUE(student_id, university_id)    ← 5 vœux ordonnés, distincts, garantis par la base
rule_configs   id text PK = empreinte du contenu (hors `name`) · name · config jsonb · parent_id→rule_configs
               · created_by→users · created_at                            ← IMMUABLE : modifier = créer une nouvelle ligne
runs           id uuid PK · config_id→rule_configs · algorithm · seed int · engine_version text · status ∈ {done, failed} · error text
               · input_snapshot jsonb · input_hash · output_hash · metrics jsonb · duration_ms
               · created_by · created_at · published_at nullable · replay_of→runs nullable
assignments    run_id→runs · student_id→students · university_id→universities nullable · rank smallint nullable
               · score numeric · explanation jsonb · PK(run_id, student_id)
devices        id · user_id→users · platform ∈ {ios, android} · token text unique · created_at
settings       key text PK · value jsonb                                   ← wishes_open (seule clé pour l'instant)
```

Dictionnaire des champs : généré depuis les modèles SQLAlchemy vers `docs/data-model.md` ; les noms ci-dessus sont ceux du moteur (`packages/generator`), pour éviter toute traduction entre couches. **Le mapping base → moteur (`services/runs.py : snapshot()`) est le vrai contrat du rejeu : il est couvert par un test qui charge le jeu de démo, construit le snapshot, et vérifie l'empreinte attendue.**

Règles d'intégrité portées par la base plutôt que par le code : 5 vœux au plus et distincts (clé primaire + contrainte unique), configurations immuables (aucun `UPDATE`/`DELETE` accordé au rôle applicatif sur `rule_configs`), une affectation par étudiant et par run (clé primaire composite), suppression d'étudiants impossible tant qu'un run les référence (`ON DELETE RESTRICT`).

## 5. Moteur de règles et d'affectation (`packages/engine`)

### 5.1 Format de configuration (exemple commenté, valide)

```jsonc
{
  "name": "Rentrée 2027 — pondération standard",      // hors empreinte : renommer ne crée pas de version
  "criteria": [                                        // score = Σ weight × pct, pct = (valeur − min) / (max − min) × 100 borné [0, 100]
    { "key": "gpa",         "weight": 0.5,  "min": 0, "max": 4 },
    { "key": "english_pct", "weight": 0.3,  "min": 0, "max": 100 },  // échelle commune TOEIC/IELTS par bandes CEFR (ADR-0007)
    { "key": "associative", "weight": 0.2,  "min": 0, "max": 100 },
    { "key": "absences",    "weight": -0.1, "min": 0, "max": 20, "default": 0 }  // poids négatif = malus ; default : attribut absent = 0
  ],
  "eliminatory": [                                     // tous vrais, sinon inéligible à cette université
    { "key": "gpa",          "op": ">=", "ref": "min_gpa" },          // ref = attribut de l'université (natif ou `attributes`)
    { "key": "english_cefr", "op": ">=", "ref": "min_cefr" },         // niveaux comparés par ordinal A1 < … < C2
    { "key": "english_cefr", "op": ">=", "value": "B1" },             // constante : un niveau en toutes lettres est accepté
    { "key": "absences",     "op": "<",  "value": 15, "default": 0 }  // SANS default, un étudiant sans l'attribut serait inéligible partout
  ],
  "bonuses": [                                         // points ajoutés si la condition est vraie (négatifs = malus)
    { "key": "personal_project", "op": "==", "value": true, "points": 10 }
  ],
  "overrides": {                                       // pondération propre à une université (criteria et/ou bonuses)
    "U017": { "criteria": [ { "key": "english_pct", "weight": 0.7, "min": 0, "max": 100 },
                            { "key": "gpa",         "weight": 0.3, "min": 0, "max": 4 } ] }
  },
  "tie_break": [                                       // départage à score égal ; l'id étudiant est toujours ajouté en dernier
    { "key": "gpa", "order": "desc" },
    { "key": "english_pct", "order": "desc" },
    { "key": "lottery", "order": "asc" }               // numéro de tirage au sort seedé, tiré au snapshot, montré dans l'explication
  ]
}
```

Opérateurs : `>= <= > < == != in`. Aucune expression libre, aucun `eval`. `rules.validate(config, student_keys, university_keys)` renvoie **toutes** les erreurs d'un coup : types, opérateurs, niveaux CEFR inconnus, et **clés qui n'existent dans aucune donnée** (une faute de frappe comme `gpaa` est refusée). L'API appelle `validate` avec les clés réellement présentes en base ; `GET /admin/configs/keys` expose cette liste pour que le formulaire admin propose les bonnes clés.

Résolution d'une clé étudiant : dérivées (`english_cefr`, `english_pct`), natives (`gpa`, `english_score`, `associative`), puis `attributes`. Côté université : `capacity`, `min_gpa`, `min_cefr`, puis `attributes`. Attribut étudiant absent : `default` s'il existe, sinon 0 point (critère) ou inéligible (seuil, choix prudent). Attribut université absent dans un `ref` : le seuil ne s'applique pas à cette université.

### 5.2 Ajouter un critère sans modifier le code

1. Renseigner l'attribut : `PUT /admin/students/attributes` (CSV `student_id,key,value` ou JSON) en une requête pour toute la cohorte, ou `PATCH /admin/students/{id}` à l'unité ; idem `PUT /admin/universities/{id}` pour un seuil côté université.
2. Dans l'espace admin, ajouter l'entrée dans `criteria`, `bonuses`, `eliminatory` ou `tie_break` ; valider ; enregistrer → nouvelle version.
3. Lancer un run avec cette version.

Preuves : `test_new_criterion_without_code_changes_outcome`, `test_university_attribute_threshold_without_code`, et la vérification « Nouveau critère sans code » du banc.

### 5.3 Algorithmes

Prétraitement commun (`algorithms.Problem`) : validation de la configuration contre les données et des entrées (vœux distincts, universités connues, capacités ≥ 0), score de chaque (étudiant, vœu), éligibilité, et pour chaque université l'ordre de préférence de ses candidats éligibles : score décroissant, puis `tie_break`, puis id. Ordre **total et strict** : condition de l'unicité du résultat et du rejeu.

| | Gale-Shapley (étudiants proposants, capacités) | Boston (acceptation immédiate) |
|---|---|---|
| Principe | Chaque étudiant propose à son meilleur vœu restant ; l'université garde provisoirement ses meilleurs candidats dans la limite des places et évince le pire, qui repropose | Tour 1 : tout le monde postule à son 1er vœu, admissions définitives ; tour 2 : les refusés postulent à leur 2e vœu sur les places restantes ; etc. |
| Complexité | O(Σ vœux × log capacité), 5 000 propositions au plus | O(Σ vœux × log) |
| Propriétés | Stable (0 paire bloquante, garanti), optimal pour les étudiants parmi les affectations stables, non manipulable par eux | Maximise le nombre de 1ers vœux servis, mais instable et manipulable (intérêt à « mentir » sur son 1er vœu) |
| Rôle | Algorithme de publication | Point de comparaison dans le mode « et si » ; sa publication est refusée (`409`) |

Sans `overrides`, toutes les universités classent les candidats dans le même ordre (seule l'éligibilité diffère) et Gale-Shapley coïncide avec un service par score décroissant. Avec `overrides`, les classements diffèrent d'une université à l'autre et la stabilité devient une vraie propriété : le banc le montre (« nominal + overrides »).

**Vérification automatique de stabilité** (`algorithms/stability.py`, `blocking_pairs`) : indépendante des algorithmes, elle ne lit que l'affectation finale. Une paire (étudiant, université) est bloquante si l'étudiant préfère cette université à son affectation et que l'université a une place libre ou le préfère à son pire admis. ≈ 0,3 ms pour 1 000 × 100 ; résultat stocké dans `runs.metrics`. Le banc exige aussi qu'elle *détecte* l'instabilité (Boston : 116 paires sur le scénario nominal).

### 5.4 Explication par étudiant

Pour chaque vœu, un statut et de quoi le justifier, stockés dans `assignments.explanation` :

```json
[
  {"rank": 1, "university": "U017", "status": "ineligible", "score": 71.2, "failed": [{"key": "english_cefr", "value": "B2", "op": ">=", "threshold": "C1", "ref": "min_cefr"}]},
  {"rank": 2, "university": "U042", "status": "rejected",   "score": 71.2, "cutoff": 74.9},
  {"rank": 3, "university": "U008", "status": "assigned",   "score": 70.4, "cutoff": 66.0},
  {"rank": 4, "university": "U051", "status": "not_considered", "score": 71.2},
  {"rank": 5, "university": "U090", "status": "not_considered", "score": 71.2}
]
```

- `score` est le score de l'étudiant **pour cette université** (il varie si elle a un `override`).
- `cutoff` : score du dernier admis à cette université (Gale-Shapley : plancher final ; Boston : plancher du tour où l'étudiant a postulé). `cutoff: null` sur un `rejected` signifie « aucune place n'était ouverte » (capacité 0, ou déjà complète avant ce tour en Boston) : le client affiche ce libellé.
- Cohérence vérifiée sur les 1 000 étudiants par `algorithms/metrics.py`, `explanation_violations` : un refusé n'excède jamais le plancher annoncé, un admis l'atteint toujours, et en Gale-Shapley un refus sans plancher n'existe que pour une capacité nulle.

Le texte (« Refusé : le dernier admis avait 74,9, votre score est 71,2 ») est rédigé par le client à partir de cette structure : traduction et rendu accessible restent de son ressort.

### 5.5 Déterminisme et rejeu

- Score arrondi à 4 décimales ; ordre de préférence total (id en dernier) ; aucun recours à l'ordre des lignes (vérifié : entrées mélangées ⇒ même `output_hash`).
- Départage à égalité parfaite : numéro de **tirage au sort** `lottery` tiré par `generator.draw_lottery(students, run.seed)` au snapshot, dans l'ordre des ids, stocké dans `attributes` (donc dans le snapshot), configurable dans `tie_break`, visible dans l'explication. Sans lui, l'id départagerait : légal mais arbitraire et invisible.
- `runs.engine_version` = `engine.ENGINE_VERSION`. Un rejeu qui renvoie `identical: false` avec une version différente est expliqué comme tel. Les empreintes de référence (`test_golden_hashes_pin_engine_behaviour`) cassent dès que le moteur change de comportement : c'est voulu, on incrémente alors la version.

## 6. Cycle de vie d'un run

```
Admin ─POST /admin/runs {config_id, algorithm, seed?}─▶ API
  1. charger rule_configs[config_id]  (immuable)
  2. snapshot : étudiants (champs, attributs, vœux) + universités (capacité, seuils, attributs) ; tirage `lottery` avec seed
     → runs.input_snapshot, input_hash, seed, engine_version
  3. engine : Problem (valide config ⊗ données) → algorithme → métriques + paires bloquantes + explications   ≈ 16 ms
  4. persister run + 1 000 assignments (un INSERT multi-lignes), une transaction
  5. 201 {run}  ← comparatif immédiat
Admin ─POST /admin/runs/{id}/publish─▶ published_at = now · wishes_open = false · tâche de fond : 1 appel FCM sur le sujet « results »
Étudiant ─GET /me/result─▶ affectation + explication du dernier run publié (published_at max)
```

- **Rejeu** : `POST /admin/runs/{id}/replay` relit `input_snapshot`, `config_id`, `seed`, relance le moteur, crée un run `replay_of = id`, répond `{"identical": bool, "engine_version": {"original", "current"}}`. Indépendant de l'état courant de la base.
- **Et si** : `GET /admin/runs/{a}/compare/{b}` : deux blocs de métriques + étudiants dont l'affectation diffère. Le banc montre qu'un changement de pondération déplace ≈ 100 étudiants sur 1 000.
- **Échec** : exception du moteur ⇒ transaction annulée, `status = failed`, `error` = message de `validate` ou d'entrées invalides, rien n'est publié.
- **Plusieurs publications** : la plus récente fait foi et remplace la précédente ; l'historique reste consultable côté admin.

Taille d'un snapshot 1 000 × 100 : ≈ 180 Ko de JSON (mesuré). Cent runs ≈ 18 Mo.

## 7. API REST

Conventions : JSON, `snake_case`, erreurs `application/problem+json` (RFC 9457) avec `errors[]` liés aux champs, dates ISO 8601 UTC, OpenAPI sur `/docs` et `/openapi.json`. Pagination `?limit=&offset=` sur les listes admin uniquement.

| Méthode et chemin | Rôle | Comportement |
|---|---|---|
| `POST /auth/login` · `POST /auth/logout` · `GET /me` | tous | session cookie (web) ou jeton Bearer (mobile), même mécanisme |
| `GET /universities` (filtres `continent, country, language, max_cefr, max_cost, q`) · `GET /universities/{id}` | étudiant, admin | `ETag` + `Cache-Control: max-age=300` ; `304` si inchangé |
| `GET /me/wishes` · `PUT /me/wishes` `[id×5]` | étudiant | exactement 5 ids distincts et existants sinon `400` ; remplacement atomique ; `409` si `wishes_open = false` ; renvoie `updated_at` |
| `GET /me/result` | étudiant | dernier run publié ; `404` tant que rien n'est publié |
| `POST /me/devices {platform, token}` · `DELETE /me/devices/{token}` | étudiant | enregistrement + abonnement au sujet FCM `results` |
| `GET /admin/configs` · `GET /admin/configs/{id}` · `GET /admin/configs/keys` · `POST /admin/configs/validate` · `POST /admin/configs` | admin | `POST` idempotent : même contenu ⇒ `200` avec la version existante, sinon `201` (`parent_id` = version de départ) ; `keys` = clés utilisables |
| `POST /admin/runs` · `GET /admin/runs` · `GET /admin/runs/{id}` · `GET /admin/runs/{id}/assignments?format=json\|csv` | admin | run synchrone, `201` ; `seed` optionnel (défaut : aléatoire, stocké) |
| `GET /admin/runs/{a}/compare/{b}` · `POST /admin/runs/{id}/replay` · `POST /admin/runs/{id}/publish` | admin | §6 ; `publish` refuse un run Boston ou `failed` (`409`) |
| `GET /admin/stats` | admin | `{demand: [{university_id, wishes_by_rank: [n1..n5], capacity}], gpa_hist, english_hist, associative_hist, wishes_by_continent, published_run_metrics}` |
| `GET /admin/students` · `PATCH /admin/students/{id}` · `PUT /admin/students/attributes` | admin | attributs libres ; import en masse CSV/JSON |
| `POST /admin/students/generate {seed, scenario, n}` | admin | régénère la cohorte fictive ; `409` dès qu'un run existe (les runs référencent les étudiants) |
| `GET /admin/universities` · `PUT /admin/universities/{id}` | admin | places, seuils, attributs, infos pratiques |
| `GET /admin/settings` · `PUT /admin/settings` | admin | `wishes_open` |
| `GET /health` | public | base joignable, version de l'API et du moteur |

Règle de conception : **aucune route étudiant ne prend d'identifiant d'étudiant**. Tout passe par `/me`, résolu depuis la session. L'accès aux données d'un autre étudiant n'a pas de chemin.

## 8. Contrat avec l'application mobile

- **Hors connexion** : chargement de `GET /universities` au premier lancement, stockage local (JSON + images par URL) ; à chaque ouverture, requête conditionnelle `If-None-Match`, `304` = rien à télécharger. Fiches, carte et filtres fonctionnent sur ce cache.
- **Synchronisation des vœux** : vœux côté serveur uniquement ; `PUT /me/wishes` remplace la liste et renvoie `updated_at`. Dernier écrit gagne (un étudiant, deux appareils : conflit improbable) ; `If-Match` à ajouter si des conflits apparaissent.
- **Notification** : à l'enregistrement d'un appareil, l'API l'abonne au sujet FCM `results` ; à la publication, un seul message de données `{"type": "results_published", "run_id": …}` sur le sujet. L'app affiche la notification et rafraîchit `GET /me/result`. Repli : interrogation de `GET /me/result` à l'ouverture. **Sur simulateur iOS, aucun push réel n'arrive** : si la cible est iOS, la démo passe par un vrai appareil ou par le repli (question ouverte §14).
- **Authentification** : `POST /auth/login` renvoie aussi le jeton dans le corps ; l'app le stocke dans le trousseau et l'envoie en `Authorization: Bearer`.

## 9. Sécurité (OWASP Top 10 2021)

| Risque | Mesure |
|---|---|
| A01 Contrôle d'accès | `require_role("admin")` sur tout `/admin/*` ; routes étudiant en `/me` uniquement ; tests d'API qui tentent l'accès croisé |
| A02 Cryptographie | argon2id ; TLS terminé par l'hébergeur ; jetons de session 32 octets aléatoires, stockés hachés (`sessions.token_hash`) |
| A03 Injection | ORM à paramètres liés ; Pydantic sur toutes les entrées ; règles = données validées, opérateurs en liste blanche, clés vérifiées contre les données, pas d'évaluation d'expression |
| A04 Conception | Configurations immuables, snapshots, vœux verrouillés à la publication, régénération interdite après un run |
| A05 Configuration | En-têtes (`HSTS`, `X-Content-Type-Options`, `Content-Security-Policy`), SPA servie par l'API donc **pas de CORS en production** (ADR-0005), debug désactivé hors développement, `.env.example` |
| A06 Composants | `uv.lock` ; Dependabot ; `pip-audit` en CI |
| A07 Authentification | Limitation de débit sur `/auth/login` (5 essais / minute / IP et compte) ; expiration 7 jours glissants ; rotation à la connexion ; message identique que l'email existe ou non |
| A08 Intégrité | Vérifications CI obligatoires ; dépendances verrouillées ; image construite en CI |
| A09 Journalisation | Logs structurés JSON ; actions admin (config créée, run, publication, import) journalisées avec l'auteur |
| A10 SSRF | Aucun appel sortant construit depuis une entrée utilisateur (FCM seul, URL fixe) |

Données fictives traitées comme réelles : pas d'export sans rôle admin, emails de démo en `@exemple.test`.

## 10. Performance

Budget : préparation + affectation + vérification de stabilité en moins de 500 ms pour 1 000 × 100, afin de tenir dans la requête HTTP (ADR-0004). Mesuré hors base, Apple M3, Python 3.14, médiane de 5 exécutions (une seule au-delà de 1 000 étudiants), `docs/benchmark-results.md` :

| Instance | Gale-Shapley | Boston | dont détection des paires bloquantes |
|---|---:|---:|---:|
| 1 000 × 100 (le besoin) | ≈ 16 ms | ≈ 16 ms | 0,3 ms |
| 10 000 × 1 000 | ≈ 0,2 s | ≈ 0,2 s | 3 ms |
| 50 000 × 1 000 | ≈ 1,1 s | ≈ 1,1 s | 40 ms |

Le temps est dominé par la préparation (scores, éligibilité, tri des candidats), linéaire en Σ vœux. Dix fois le besoin tient dans le budget ; cinquante fois le dépasse : c'est le seuil où une file de tâches se justifierait.

**Ce qui n'est pas encore mesuré** : le run de bout en bout (`POST /admin/runs`) avec lecture des 1 000 étudiants, écriture du snapshot (≈ 180 Ko) et des 1 000 affectations avec explications (≈ 0,5 à 1 Mo) sur une base distante. Attendu : 100 à 300 ms depuis Fly.io vers Neon dans la même région. Ce chiffre entre dans les tests d'API dès que l'API existe, et le budget de 500 ms couvre les deux parties.

Comparatif sur le besoin (nominal) : Gale-Shapley 62,9 % de 1ers vœux, 17,8 % de non-affectés, rang moyen 1,39, 0 paire bloquante ; Boston 68,9 %, 18,5 %, 1,25, **116 paires bloquantes**. Les cinq autres scénarios, la variante avec pondérations par université et les 68 vérifications sont dans le rapport.

## 11. Tests, CI/CD, exploitation

**Tests** (`pytest`, une commande) :
- moteur et générateur : `packages/*/tests`, 23 tests, < 3 s : règles (validation, seuils, bonus, critère sans code, départage, overrides), deux algorithmes avec vérification automatique de stabilité, générateur (reproductibilité, bornes, continents), échelle d'anglais, empreintes de référence ;
- API (`TestClient`, Postgres éphémère) : droits et accès croisé, cycle run → publier → résultat, rejeu identique, mapping base → moteur, mesure de bout en bout ;
- données : `data/universities.json` validé par un schéma JSON (100 entrées, 6 continents, GPS, chaque photo avec `author`/`license`/`alt`, `cost_of_living.source`, `sources[]` non vide) ;
- le banc (`pnpm bench`) est une suite d'assertions et tourne en CI sur chaque PR, rapport en artefact (sans commit du rapport : les temps varient, seules les vérifications sont comparables).

**CI** (GitHub Actions, chaque PR) : Conventional Commits, `ruff check` + `ruff format --check`, licences des dépendances (`pip-licenses`), secrets sur tout l'historique (`gitleaks`), `pytest`, banc, `docker build`. Vérifications obligatoires sur `main`.

**CD** : merge sur `main` → déploiement Fly.io ; `alembic upgrade head` au démarrage ; seed du jeu de démo si la base est vide. La SPA est construite dans l'image et servie par l'API sous `/` (l'API sous `/api`). Mobile : build APK / simulateur publié en artefact par le pipeline du dépôt mobile (ou du même dépôt, question ouverte §14).

**Démarrage local** : `docker compose up` lance Postgres + API, applique les migrations, charge 100 universités et 1 000 étudiants (`generate(seed=42)`), crée un compte admin et trois comptes étudiants de démo (mots de passe dans `.env.example`). Swagger sur `http://localhost:8000/docs`.

**Logs** : lisibles en développement (requêtes SQL affichées), JSON en production.

## 12. Place du backend dans le mono-dépôt

```
apps/api/
├── app/
│   ├── main.py            FastAPI : routes sous /api, en-têtes de sécurité, démarrage (tables + jeu de démo)
│   ├── db.py              connexion SQLAlchemy et tables du §4
│   ├── auth.py            argon2id, sessions opaques, require_role, limitation des échecs de connexion
│   └── services.py        mapping base → moteur, snapshot (dont lottery) → engine → persistance
├── tests/                 functional/ (API en processus), e2e/ (plateforme démarrée) : voir testing.md
└── Dockerfile             image de production, construite depuis la racine du dépôt
packages/engine/
├── rules/                 format de configuration, critères, seuils, bonus, départage ; english.py (échelle CEFR)
├── algorithms/            problem.py (prétraitement commun), gale_shapley.py, boston.py, stability.py, metrics.py
├── benchmark/run.py       banc d'essai : temps pour 1 000 étudiants et plus, par algorithme
└── tests/
packages/generator/        étudiants et universités fictifs, seed, scénarios de tension ; tests/
docs/technical/            ce document, benchmark-protocol.md, benchmark-results.md, testing.md
docs/adr/                  décisions
pyproject.toml · uv.lock   environnement Python unique du dépôt (uv), importé comme app, engine, generator
```

À venir dans `apps/api` quand le besoin apparaît : Alembic (migrations), `notify.py` (adaptateur FCM), découpage de
`main.py` en routers par espace. `data/destinations/` remplacera les universités générées.

## 13. Volontairement reporté

| Non fait | Pourquoi | Quand l'ajouter |
|---|---|---|
| File de tâches (Celery, Redis) | run ≈ 16 ms ; publication en tâche de fond FastAPI (un appel FCM) | si un run dépasse 5 s (≥ 100 000 étudiants) |
| JWT / OAuth | sessions opaques révocables, plus simples | jamais pour ce projet |
| Cache Redis du catalogue | 100 lignes, `ETag` suffit | jamais pour ce projet |
| Verrou optimiste sur les vœux | un étudiant, conflit improbable | `If-Match` si conflits observés |
| Historique des modifications d'étudiants | le snapshot de run suffit au rejeu | si l'audit individuel est demandé |
| Second tour pour les non-affectés (≈ 18 % en nominal) | politique à décider (§14) | dès la réponse : nouveau run sur places restantes avec vœux complémentaires, même moteur |
| Grille CEFR modifiable par l'admin | constante sourcée (ADR-0007) | si une autre certification (Cambridge, TOEFL) entre au catalogue |

## 14. Décisions prises par l'auteur, et questions qui restent au propriétaire

**Tranchées ici (à contester si besoin)** : stack Python/FastAPI/PostgreSQL (ADR-0001, confirmée le 2026-11-02) ; échelle d'anglais commune par bandes CEFR (ADR-0007) ; tirage au sort seedé comme dernier départage ; `name` hors empreinte de version ; `POST /admin/configs` idempotent ; exactement 5 vœux ; dernier run publié fait foi ; publication d'un run Boston refusée ; régénération de cohorte interdite après un run ; SPA servie par l'API ; Fly.io plutôt que Render.

**À trancher par l'équipe, car la réponse change ce qui est construit** :
1. Un dépôt unique (web + backend + mobile, ce que le PDF suggère) ou trois : change CI, Compose, README, GitHub Projects.
2. Plateforme mobile : iOS ou Android. iOS ⇒ pas de push sur simulateur, démo de la notification sur appareil réel ou via le repli.
3. Sort des non-affectés : statut final, second tour sur places restantes, ou affectation forcée ?
4. Départage : le tirage au sort seedé convient-il à l'école fictive, ou préfère-t-elle un critère déterministe affiché (ancienneté, etc.) ?
