# Protocole de benchmark du moteur d'affectation

Objectif : prouver, de façon reproductible, que le moteur est **juste** (invariants, stabilité, explications cohérentes, rejeu) et **robuste** (scénarios de tension, montée en charge), et mesurer le temps de calcul exigé par le sujet.

## Exécution

```
pnpm bench                        # ≈ 10 s, écrit docs/technical/benchmark-results.md, code de sortie 1 si une vérification échoue
uv run pytest packages            # tests unitaires du moteur et du générateur, < 1 s
```

Le moteur n'a aucune dépendance. Le banc tourne en CI sur chaque PR, rapport en artefact (sans commit du rapport : les temps varient d'une machine à l'autre, seules les vérifications et les métriques d'affectation sont comparables).

## Jeu de données

`packages/generator`, seed 42, 1 000 étudiants × 100 universités. Universités synthétiques mais cohérentes : une sélectivité tirée dans Beta(2, 3) pilote à la fois les places (3 à 17), le GPA minimum (2,0 à 3,5), le niveau d'anglais minimum (B1 / B2 / C1) et la popularité. Étudiants : GPA ~ N(2,9 ; 0,5) borné [1 ; 4], TOEIC ~ N(720 ; 150) (60 %) ou IELTS ~ N(6,3 ; 1,0) (40 %), vie associative ~ N(50 ; 20), 5 vœux distincts tirés selon la popularité avec auto-sélection (un vœu inéligible n'est gardé qu'à 15 %, « vœu de rêve »). Un numéro de tirage au sort `lottery` est tiré avec la graine 42, comme le fera l'API au snapshot.

| Scénario | Ce qu'il met à l'épreuve |
|---|---|
| `nominal` | distributions réalistes, capacité totale ≈ 1,1 × effectif |
| `oversubscribed` | 60 % des étudiants concentrent leurs vœux sur les 10 universités les plus prisées |
| `weak_english` | cohorte faible en anglais : beaucoup d'inéligibles, forte part de non-affectés |
| `tight_capacity` | capacités réduites à 80 % : moins de places que d'étudiants |
| `abundant` | capacités triplées : les deux algorithmes doivent converger |
| `ties` | profils tous identiques : seul le tirage au sort seedé décide ; le résultat doit rester stable et déterministe |
| `nominal + overrides` | données nominales, mais les 15 universités les plus disputées pondèrent l'anglais à 60 % : les classements diffèrent d'une université à l'autre |

## Métriques (par scénario et par algorithme)

- **1er vœu** : % d'étudiants affectés à leur vœu 1 · **Non affectés** : % sans place · **Rang moyen** : parmi les affectés · **Répartition des rangs**.
- **Paires bloquantes** : nombre de (étudiant, université) tels que l'étudiant préfère l'université à son affectation et que l'université a une place libre ou le préfère à son pire admis. 0 ⇔ stable. Calcul indépendant des algorithmes (`metrics.blocking_pairs`).
- **Taux de remplissage** : affectés / places.
- **Temps** : préparation (scores, éligibilité, tri des candidats), affectation, détection des paires bloquantes seule ; médiane de 5 exécutions (une seule au-delà de 1 000 étudiants), `time.perf_counter`.

## Vérifications de justesse (le banc échoue si l'une casse)

| Famille | Vérification |
|---|---|
| Invariants | affecté uniquement à l'un de ses vœux ; jamais là où il est inéligible ; jamais de sur-capacité (chaque scénario, chaque algorithme) |
| Overrides | avec pondérations par université, Gale-Shapley reste stable et le résultat diffère du cas sans override |
| Stabilité | Gale-Shapley : 0 paire bloquante sur chaque scénario et aux échelles 10 000 × 1 000 et 50 000 × 1 000 ; le détecteur trouve des paires sur Boston (test du test) |
| Propriété théorique | Boston sert au moins autant de 1ers vœux que Gale-Shapley sur chaque scénario |
| Explications | tout « refusé » a un score ≤ plancher annoncé ; tout « admis » a un score ≥ plancher ; en Gale-Shapley, un refus sans plancher n'existe que pour une capacité nulle |
| Générateur | même seed ⇒ même empreinte ; seed différent ⇒ empreinte différente ; 6 continents ; 5 vœux distincts valides |
| Rejeu | même snapshot + même configuration ⇒ même empreinte d'affectation (deux algorithmes) |
| Déterminisme | lignes d'entrée mélangées ⇒ même empreinte (deux algorithmes) |
| Versionnage | modifier un poids ⇒ nouvel identifiant de configuration et des affectations différentes |
| Règles sans code | ajout d'un bonus et d'un malus par configuration seule ⇒ affectation modifiée, toujours stable |
| Validation | une configuration invalide est rejetée avec toutes ses erreurs (types, opérateurs, clés inconnues, niveau CEFR) ; un seuil CEFR en constante (« C1 ») est accepté et appliqué |
| Budget | préparation + affectation + vérification < 500 ms pour 1 000 × 100 |
| Stockage | snapshot d'entrée < 1 Mo |

## Ajouter un scénario

Une entrée dans `generator.SCENARIOS` et, si besoin, une branche dans `generator.generate`. Le banc et les tests l'exécutent automatiquement.

## Limites connues

- Universités synthétiques : les 100 réelles remplaceront `make_universities` par un chargement de `data/universities.json` ; le reste du protocole est inchangé.
- Temps mesurés hors base de données : la mesure de bout en bout (`POST /admin/runs`) s'ajoutera aux tests d'API.
- Machine de référence : Apple M3 ; les temps CI seront 2 à 4 fois plus lents, le budget de 500 ms garde une marge de 10 × sur le calcul seul.
- Universités synthétiques : les plus sélectives reçoivent peu de candidats éligibles (auto-sélection), la tension se joue sur les universités intermédiaires ; c'est pour cela que la variante `overrides` cible les universités les plus disputées et non les plus sélectives.
