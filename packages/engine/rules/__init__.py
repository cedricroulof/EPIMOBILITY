"""Moteur de règles : une configuration JSON interprétée, aucune règle codée en dur.

score(s, u)     = Σ poids_c × pct_c + Σ bonus,   pct_c = (valeur − min) / (max − min) × 100, borné à [0, 100]
                  `overrides[u]` peut remplacer `criteria` et/ou `bonuses` pour une université donnée
éligible(s, u)  ⇔ tous les seuils éliminatoires sont satisfaits (seuil = constante `value` ou attribut `ref` de l'université)
préférence de u = score décroissant, puis `tie_break`, puis id étudiant ⇒ ordre total strict ⇒ résultat déterministe

Ajouter un critère = une entrée dans `criteria` / `bonuses` / `eliminatory` / `tie_break` et l'attribut correspondant
dans `Student.attributes` (ou `University.attributes` pour un seuil). Aucun code à modifier.
Clés réservées : natives (`gpa`, `english_score`, `english_pct`, `english_cefr`, `associative`) et `lottery`
(tirage au sort seedé, rempli au snapshot par `generator.draw_lottery`, départage ultime avant l'id).
"""

import hashlib
import json
import math
import operator

from .english import CEFR

OPS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "==": operator.eq,
    "!=": operator.ne,
    "in": lambda a, b: a in b,
}
STUDENT_KEYS = {"gpa", "english_score", "english_pct", "english_cefr", "associative", "lottery"}
UNIVERSITY_KEYS = {"capacity", "min_gpa", "min_cefr"}
CEFR_KEYS = {"english_cefr", "min_cefr"}
NUM = (int, float)

DEFAULT_CONFIG = {
    "name": "Configuration par défaut",
    "criteria": [  # poids relatifs ; ici ils somment à 1 ⇒ score sur 100
        {"key": "gpa", "weight": 0.5, "min": 0, "max": 4},
        {"key": "english_pct", "weight": 0.3, "min": 0, "max": 100},
        {"key": "associative", "weight": 0.2, "min": 0, "max": 100},
    ],
    "eliminatory": [  # `ref` = attribut de l'université ; `value` = constante (niveaux CEFR acceptés en toutes lettres)
        {"key": "gpa", "op": ">=", "ref": "min_gpa"},
        {"key": "english_cefr", "op": ">=", "ref": "min_cefr"},
    ],
    "bonuses": [],  # ex. {"key": "personal_project", "op": "==", "value": true, "points": 10}
    "overrides": {},  # ex. {"U017": {"criteria": [...]}} : pondération propre à une université
    "tie_break": [
        {"key": "gpa", "order": "desc"},
        {"key": "english_pct", "order": "desc"},
        {"key": "lottery", "order": "asc"},
    ],
}


def _canon(x):
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    if isinstance(x, NUM):
        return float(x)  # 1 et 1.0 sont la même règle
    if isinstance(x, dict):
        return {k: _canon(v) for k, v in sorted(x.items())}
    return [_canon(v) for v in x]


def config_id(config) -> str:
    """Version = empreinte du CONTENU des règles (le `name` n'en fait pas partie) : même règles ⇒ même id."""
    content = _canon({k: v for k, v in config.items() if k != "name"})
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def _const(key, v):
    """Constante de règle : un niveau CEFR en toutes lettres devient son ordinal."""
    return CEFR.index(v) if key in CEFR_KEYS and isinstance(v, str) and v in CEFR else v


def validate(config, student_keys=None, university_keys=None):
    """Lève ValueError listant TOUTES les erreurs. Avec `student_keys` / `university_keys` (attributs réellement présents
    dans les données), vérifie aussi que chaque clé existe : une faute de frappe est refusée avant le run."""
    errors = []
    known_s = STUDENT_KEYS | set(student_keys or ()) if student_keys is not None else None
    known_u = UNIVERSITY_KEYS | set(university_keys or ()) if university_keys is not None else None

    def key_ok(where, key):
        if key is None:
            errors.append(f"{where} : 'key' manquant")
        elif known_s is not None and key not in known_s:
            errors.append(
                f"{where} : clé {key!r} inconnue (natives : {sorted(STUDENT_KEYS)}, attributs : {sorted(known_s - STUDENT_KEYS)})"
            )

    def check_criteria(where, items):
        for i, c in enumerate(items):
            key_ok(f"{where}[{i}]", c.get("key"))
            if not isinstance(c.get("weight"), NUM):
                errors.append(f"{where}[{i}] : 'weight' numérique requis")
            if not (isinstance(c.get("min"), NUM) and isinstance(c.get("max"), NUM) and c["min"] < c["max"]):
                errors.append(f"{where}[{i}] : 'min' < 'max' requis")

    def check_bonuses(where, items):
        for i, b in enumerate(items):
            key_ok(f"{where}[{i}]", b.get("key"))
            if "value" not in b:
                errors.append(f"{where}[{i}] : 'value' requis")
            elif b.get("key") in CEFR_KEYS and isinstance(b["value"], str) and b["value"] not in CEFR:
                errors.append(f"{where}[{i}] : niveau CEFR inconnu {b['value']!r}")
            if b.get("op") not in OPS:
                errors.append(f"{where}[{i}] : op inconnu {b.get('op')!r}")
            if not isinstance(b.get("points"), NUM):
                errors.append(f"{where}[{i}] : 'points' numérique requis")

    check_criteria("criteria", config.get("criteria", []))
    check_bonuses("bonuses", config.get("bonuses", []))
    for i, e in enumerate(config.get("eliminatory", [])):
        key_ok(f"eliminatory[{i}]", e.get("key"))
        if e.get("op") not in OPS:
            errors.append(f"eliminatory[{i}] : op inconnu {e.get('op')!r}")
        if ("ref" in e) == ("value" in e):
            errors.append(f"eliminatory[{i}] : exactement un de 'ref' ou 'value'")
        if "ref" in e and known_u is not None and e["ref"] not in known_u:
            errors.append(f"eliminatory[{i}] : attribut d'université {e['ref']!r} inconnu (connus : {sorted(known_u)})")
        if "value" in e and e.get("key") in CEFR_KEYS and isinstance(e["value"], str) and e["value"] not in CEFR:
            errors.append(f"eliminatory[{i}] : niveau CEFR inconnu {e['value']!r}")
    for uid, o in config.get("overrides", {}).items():
        if not isinstance(o, dict) or not (set(o) <= {"criteria", "bonuses"}):
            errors.append(f"overrides[{uid}] : seuls 'criteria' et 'bonuses' peuvent être remplacés")
            continue
        check_criteria(f"overrides[{uid}].criteria", o.get("criteria", []))
        check_bonuses(f"overrides[{uid}].bonuses", o.get("bonuses", []))
    for i, t in enumerate(config.get("tie_break", [])):
        key_ok(f"tie_break[{i}]", t.get("key"))
        if t.get("order", "desc") not in ("asc", "desc"):
            errors.append(f"tie_break[{i}] : 'order' doit être asc|desc")
    if errors:
        raise ValueError("configuration invalide : " + " ; ".join(errors))
    return config


def student_value(student, key, default=None):
    """Résout un critère : attributs dérivés, champs natifs numériques, puis `attributes` (critères ajoutés)."""
    if key == "english_cefr":
        return CEFR.index(student.english_cefr)
    if key in STUDENT_KEYS and key != "lottery":
        return getattr(student, key)
    return student.attributes.get(key, default)


def university_value(uni, key):
    """Attribut natif ou ajouté. Absent ⇒ None ⇒ le seuil ne s'applique pas à cette université."""
    if key == "min_cefr":
        return CEFR.index(uni.min_cefr)
    return getattr(uni, key) if key in UNIVERSITY_KEYS else uni.attributes.get(key)


def _label(key, v):
    return CEFR[v] if key in CEFR_KEYS and isinstance(v, int) and 0 <= v < len(CEFR) else v


def failed_thresholds(student, uni, config):
    """Seuils éliminatoires non satisfaits (liste vide = éligible). Structuré : l'UI rédige le texte."""
    failed = []
    for rule in config.get("eliminatory", []):
        v = student_value(student, rule["key"], rule.get("default"))
        ref = university_value(uni, rule["ref"]) if "ref" in rule else _const(rule["key"], rule["value"])
        if ref is None:
            continue  # l'université n'a pas ce seuil
        if v is None or not OPS[rule["op"]](
            v, ref
        ):  # attribut absent chez l'étudiant ⇒ inéligible (prudent ; mettre `default`)
            failed.append(
                {
                    "key": rule["key"],
                    "value": _label(rule["key"], v),
                    "op": rule["op"],
                    "threshold": _label(rule.get("ref") or rule["key"], ref),
                    "ref": rule.get("ref"),
                }
            )
    return failed


def _rules_for(config, uni):
    o = config.get("overrides", {}).get(uni.id) if uni is not None else None
    if not o:
        return config["criteria"], config.get("bonuses", [])
    return o.get("criteria", config["criteria"]), o.get("bonuses", config.get("bonuses", []))


def score(student, config, uni=None) -> float:
    criteria, bonuses = _rules_for(config, uni)
    total = 0.0
    for c in criteria:
        v = student_value(student, c["key"], c.get("default"))
        if v is None:
            continue  # critère absent chez cet étudiant ⇒ 0 point (documenté ; mettre `default` sinon)
        total += c["weight"] * min(100.0, max(0.0, 100.0 * (v - c["min"]) / (c["max"] - c["min"])))
    for b in bonuses:
        v = student_value(student, b["key"], b.get("default"))
        if v is not None and OPS[b["op"]](v, _const(b["key"], b["value"])):
            total += b["points"]
    return round(total, 4)  # arrondi fixe : pas de bruit flottant dans les égalités ⇒ rejeu identique


def rank_key(student, config, uni=None, score_value=None):
    """Clé de tri = ordre de préférence de l'université. Se termine par l'id ⇒ ordre total strict."""
    key = [-(score(student, config, uni) if score_value is None else score_value)]
    for t in config.get("tie_break", []):
        v = student_value(student, t["key"], t.get("default", 0))
        if v is None or isinstance(v, bool) or not isinstance(v, NUM) or math.isnan(v):
            raise ValueError(f"tie_break {t['key']!r} : valeur non numérique {v!r} pour {student.id}")
        key.append(-v if t.get("order", "desc") == "desc" else v)
    key.append(student.id)
    return tuple(key)
