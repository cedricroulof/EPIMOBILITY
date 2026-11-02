# Résultats du banc d'essai du moteur d'affectation

## 1. Comparatif par scénario (1 000 étudiants × 100 universités, seed 42)

| Scénario | Algorithme | 1er vœu | Non affectés | Rang moyen | Paires bloquantes | Taux de remplissage | Préparation | Affectation | Détection paires bloquantes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| nominal | gale_shapley | 62.9 % | 17.8 % | 1.388 | 0 | 73.7 % | 15.3 ms | 0.5 ms | 0.3 ms |
| nominal | boston | 68.9 % | 18.5 % | 1.248 | 116 | 73.1 % | 15.3 ms | 0.5 ms | 0.3 ms |
| oversubscribed | gale_shapley | 49.0 % | 20.3 % | 1.733 | 0 | 71.5 % | 14.5 ms | 0.4 ms | 0.3 ms |
| oversubscribed | boston | 53.0 % | 22.1 % | 1.601 | 76 | 69.9 % | 14.5 ms | 0.6 ms | 0.3 ms |
| weak_english | gale_shapley | 43.1 % | 34.7 % | 1.496 | 0 | 58.6 % | 14.1 ms | 0.4 ms | 0.3 ms |
| weak_english | boston | 46.2 % | 35.4 % | 1.418 | 43 | 57.9 % | 14.1 ms | 0.6 ms | 0.3 ms |
| tight_capacity | gale_shapley | 55.5 % | 27.8 % | 1.402 | 0 | 80.5 % | 15.1 ms | 0.5 ms | 0.4 ms |
| tight_capacity | boston | 64.1 % | 28.3 % | 1.16 | 250 | 79.9 % | 15.1 ms | 0.6 ms | 0.3 ms |
| abundant | gale_shapley | 71.7 % | 13.7 % | 1.257 | 0 | 25.8 % | 15.2 ms | 0.4 ms | 0.2 ms |
| abundant | boston | 71.7 % | 13.7 % | 1.257 | 0 | 25.8 % | 15.2 ms | 0.5 ms | 0.2 ms |
| ties | gale_shapley | 71.0 % | 3.2 % | 1.51 | 0 | 86.8 % | 17.5 ms | 0.6 ms | 0.3 ms |
| ties | boston | 78.4 % | 5.8 % | 1.322 | 166 | 84.5 % | 17.5 ms | 0.6 ms | 0.3 ms |
| nominal + overrides | gale_shapley | 62.6 % | 17.6 % | 1.409 | 0 | 73.9 % | 17.4 ms | 0.5 ms | 0.3 ms |
| nominal + overrides | boston | 68.9 % | 18.5 % | 1.254 | 125 | 73.1 % | 17.4 ms | 0.5 ms | 0.3 ms |

Lecture : Boston maximise les premiers vœux mais crée des paires bloquantes (un étudiant et une université qui se préféreraient mutuellement à leur affectation). Gale-Shapley n'en crée jamais, au prix de quelques premiers vœux.

### Répartition des rangs obtenus (scénario nominal)

| Algorithme | Vœu 1 | Vœu 2 | Vœu 3 | Vœu 4 | Vœu 5 | Non affecté |
|---|---:|---:|---:|---:|---:|---:|
| gale_shapley | 629 | 113 | 45 | 24 | 11 | 178 |
| boston | 689 | 73 | 35 | 13 | 5 | 185 |

## 2. Montée en charge (marge au-delà du besoin : 1 000 × 100)

| Étudiants | Universités | Algorithme | Préparation | Affectation | Détection paires bloquantes | Total |
|---:|---:|---|---:|---:|---:|---:|
| 1 000 | 100 | gale_shapley | 15 ms | 0 ms | 0 ms | 16 ms |
| 1 000 | 100 | boston | 15 ms | 1 ms | 0 ms | 16 ms |
| 10 000 | 1 000 | gale_shapley | 175 ms | 6 ms | 3 ms | 184 ms |
| 10 000 | 1 000 | boston | 175 ms | 6 ms | 3 ms | 184 ms |
| 50 000 | 1 000 | gale_shapley | 974 ms | 62 ms | 40 ms | 1077 ms |
| 50 000 | 1 000 | boston | 974 ms | 49 ms | 40 ms | 1063 ms |

## 3. Vérifications de justesse : 68/68 réussies

- ✅ nominal/gale_shapley : invariants (vœux, éligibilité, capacités)
- ✅ nominal/gale_shapley : explications cohérentes avec les planchers
- ✅ nominal/gale_shapley : 0 paire bloquante (stabilité) — 0
- ✅ nominal/gale_shapley : budget 500 ms (préparation + affectation + vérification) — 16 ms
- ✅ nominal/boston : invariants (vœux, éligibilité, capacités)
- ✅ nominal/boston : explications cohérentes avec les planchers
- ✅ nominal : Boston sert au moins autant de 1ers vœux que Gale-Shapley (propriété théorique) — boston 68.9 vs GS 62.9
- ✅ oversubscribed/gale_shapley : invariants (vœux, éligibilité, capacités)
- ✅ oversubscribed/gale_shapley : explications cohérentes avec les planchers
- ✅ oversubscribed/gale_shapley : 0 paire bloquante (stabilité) — 0
- ✅ oversubscribed/gale_shapley : budget 500 ms (préparation + affectation + vérification) — 15 ms
- ✅ oversubscribed/boston : invariants (vœux, éligibilité, capacités)
- ✅ oversubscribed/boston : explications cohérentes avec les planchers
- ✅ oversubscribed : Boston sert au moins autant de 1ers vœux que Gale-Shapley (propriété théorique) — boston 53.0 vs GS 49.0
- ✅ weak_english/gale_shapley : invariants (vœux, éligibilité, capacités)
- ✅ weak_english/gale_shapley : explications cohérentes avec les planchers
- ✅ weak_english/gale_shapley : 0 paire bloquante (stabilité) — 0
- ✅ weak_english/gale_shapley : budget 500 ms (préparation + affectation + vérification) — 15 ms
- ✅ weak_english/boston : invariants (vœux, éligibilité, capacités)
- ✅ weak_english/boston : explications cohérentes avec les planchers
- ✅ weak_english : Boston sert au moins autant de 1ers vœux que Gale-Shapley (propriété théorique) — boston 46.2 vs GS 43.1
- ✅ tight_capacity/gale_shapley : invariants (vœux, éligibilité, capacités)
- ✅ tight_capacity/gale_shapley : explications cohérentes avec les planchers
- ✅ tight_capacity/gale_shapley : 0 paire bloquante (stabilité) — 0
- ✅ tight_capacity/gale_shapley : budget 500 ms (préparation + affectation + vérification) — 16 ms
- ✅ tight_capacity/boston : invariants (vœux, éligibilité, capacités)
- ✅ tight_capacity/boston : explications cohérentes avec les planchers
- ✅ tight_capacity : Boston sert au moins autant de 1ers vœux que Gale-Shapley (propriété théorique) — boston 64.1 vs GS 55.5
- ✅ abundant/gale_shapley : invariants (vœux, éligibilité, capacités)
- ✅ abundant/gale_shapley : explications cohérentes avec les planchers
- ✅ abundant/gale_shapley : 0 paire bloquante (stabilité) — 0
- ✅ abundant/gale_shapley : budget 500 ms (préparation + affectation + vérification) — 16 ms
- ✅ abundant/boston : invariants (vœux, éligibilité, capacités)
- ✅ abundant/boston : explications cohérentes avec les planchers
- ✅ abundant : Boston sert au moins autant de 1ers vœux que Gale-Shapley (propriété théorique) — boston 71.7 vs GS 71.7
- ✅ ties/gale_shapley : invariants (vœux, éligibilité, capacités)
- ✅ ties/gale_shapley : explications cohérentes avec les planchers
- ✅ ties/gale_shapley : 0 paire bloquante (stabilité) — 0
- ✅ ties/gale_shapley : budget 500 ms (préparation + affectation + vérification) — 18 ms
- ✅ ties/boston : invariants (vœux, éligibilité, capacités)
- ✅ ties/boston : explications cohérentes avec les planchers
- ✅ ties : Boston sert au moins autant de 1ers vœux que Gale-Shapley (propriété théorique) — boston 78.4 vs GS 71.0
- ✅ nominal + overrides/gale_shapley : invariants (vœux, éligibilité, capacités)
- ✅ nominal + overrides/gale_shapley : explications cohérentes avec les planchers
- ✅ nominal + overrides/gale_shapley : 0 paire bloquante (stabilité) — 0
- ✅ nominal + overrides/gale_shapley : budget 500 ms (préparation + affectation + vérification) — 18 ms
- ✅ nominal + overrides/boston : invariants (vœux, éligibilité, capacités)
- ✅ nominal + overrides/boston : explications cohérentes avec les planchers
- ✅ nominal + overrides : Boston sert au moins autant de 1ers vœux que Gale-Shapley (propriété théorique) — boston 68.9 vs GS 62.6
- ✅ Le vérificateur de stabilité détecte bien l'instabilité (Boston > 0 paires sur au moins un scénario)
- ✅ Pondérations par université (overrides) : Gale-Shapley reste stable et le classement diffère entre universités
- ✅ Générateur : même seed ⇒ jeu de données identique (hash) — 7503f5a3ac7b1319
- ✅ Générateur : seed différent ⇒ jeu de données différent — 7503f5a3ac7b1319 vs 26130efa74a8e063
- ✅ Générateur : les 6 continents habités sont couverts — ['Afrique', 'Amérique du Nord', 'Amérique du Sud', 'Asie', 'Europe', 'Océanie']
- ✅ Générateur : 5 vœux distincts et valides pour chaque étudiant
- ✅ Snapshot d'entrée d'un run (stocké en JSONB pour le rejeu) < 1 Mo — 182 Ko
- ✅ Rejeu/gale_shapley : même snapshot + même config ⇒ affectation identique — 8d3822f1957c1f63
- ✅ Déterminisme/gale_shapley : ordre des lignes en entrée mélangé ⇒ même affectation
- ✅ Rejeu/boston : même snapshot + même config ⇒ affectation identique — 78485432471f8670
- ✅ Déterminisme/boston : ordre des lignes en entrée mélangé ⇒ même affectation
- ✅ Versionnage : modifier un poids ⇒ nouvel identifiant de configuration — 0105de869c445535 → f6a8f6a6790fc2c7
- ✅ Mode « et si » : la nouvelle pondération change réellement des affectations — 101 étudiants déplacés
- ✅ Nouveau critère sans code : bonus « projet perso » + malus « absences » ajoutés par config seule, affectation modifiée, toujours stable — 84 étudiants déplacés
- ✅ Validation : une configuration invalide est rejetée avec toutes ses erreurs (types, opérateurs, clés inconnues, niveau CEFR) — 7 erreurs listées
- ✅ Seuil CEFR en constante (« C1 ») : accepté, appliqué, affectation stable
- ✅ Échelle 1000×100 : Gale-Shapley reste stable
- ✅ Échelle 10000×1000 : Gale-Shapley reste stable
- ✅ Échelle 50000×1000 : Gale-Shapley reste stable

## Environnement

- Python 3.14.5, arm64, Darwin 27.0.0
- Temps : médiane de 5 exécutions (1 seule exécution au-delà de 1 000 étudiants), `time.perf_counter` ; les temps varient d'une machine et d'une exécution à l'autre, seules les vérifications sont comparables entre deux rapports
- Généré par `python3 bench/run.py` le 2026-10-26 17:26
