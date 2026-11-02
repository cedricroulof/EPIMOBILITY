# ADR-0007 — Échelle d'anglais commune par bandes CEFR ; tirage au sort seedé comme dernier départage

Statut : accepté (choix de l'auteur, contestable) · Date : 2026-10-26

## Contexte
Les étudiants présentent un TOEIC (10–990) ou un IELTS (0–9). La première version normalisait chaque test sur son échelle brute : un TOEIC 945 valait 95 points, un IELTS 7.0 en valait 78, alors que les deux attestent le début du niveau C1. Inéquitable, et difficile à défendre devant un jury. Par ailleurs, à score et départages égaux, le moteur tranchait par l'identifiant : déterministe mais arbitraire et invisible.

## Décision
- `english_pct` = position sur une échelle commune où chaque bande CEFR vaut la même plage (A1 = 0, A2 = 20, B1 = 40, B2 = 60, C1 = 80, sommet = 100), interpolée linéairement dans la bande, à partir des grilles officielles (ETS « Mapping the TOEIC tests on the CEFR » ; « IELTS and the CEFR »). Le TOEIC L&R n'atteste pas le C2 : son maximum vaut 100 points mais reste étiqueté C1. Code : `engine/english.py` ; test : `test_english_scale_is_equitable_between_tests`.
- Départage : un numéro `lottery` par étudiant, tiré au snapshot avec `run.seed` dans l'ordre des ids (`generator.draw_lottery`), stocké dans `attributes` donc dans le snapshot, référencé par `tie_break` et montré dans l'explication. L'id reste l'ultime fallback théorique.

## Conséquences
- `+` Équité entre tests ; grille sourcée et documentée ; une autre certification s'ajoute par une ligne dans `english.py`.
- `+` Égalités parfaites tranchées de façon défendable, reproductible (seed stocké) et transparente (visible par l'étudiant).
- `−` Changer la grille change les scores et donc les affectations : incrémenter `ENGINE_VERSION`, mettre à jour les empreintes de référence.
- Le propriétaire peut préférer un critère déterministe affiché au tirage au sort : c'est une entrée `tie_break` de plus, rien d'autre ne bouge.
