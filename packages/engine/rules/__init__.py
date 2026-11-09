"""Rule engine: an interpreted JSON configuration, no hard-coded rule.

score(s, u)     = Σ weight_c × pct_c + Σ bonus,   pct_c = (value − min) / (max − min) × 100, clamped to [0, 100]
                  `overrides[u]` can replace `criteria` and/or `bonuses` for a given university
eligible(s, u)  ⇔ all eliminatory thresholds are met (threshold = constant `value` or university attribute `ref`)
preference of u = descending score, then `tie_break`, then student id ⇒ strict total order ⇒ deterministic result

Adding a criterion = one entry in `criteria` / `bonuses` / `eliminatory` / `tie_break` and the corresponding attribute
in `Student.attributes` (or `University.attributes` for a threshold). No code to change.
Reserved keys: built-in (`gpa`, `english_score`, `english_pct`, `english_cefr`, `associative`) and `lottery`
(seeded lottery, filled at snapshot time by `generator.draw_lottery`, final tie-break before the id).
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
    "name": "Default configuration",
    "criteria": [  # relative weights; here they sum to 1 ⇒ score out of 100
        {"key": "gpa", "weight": 0.5, "min": 0, "max": 4},
        {"key": "english_pct", "weight": 0.3, "min": 0, "max": 100},
        {"key": "associative", "weight": 0.2, "min": 0, "max": 100},
    ],
    "eliminatory": [  # `ref` = university attribute; `value` = constant (CEFR levels accepted in letters)
        {"key": "gpa", "op": ">=", "ref": "min_gpa"},
        {"key": "english_cefr", "op": ">=", "ref": "min_cefr"},
    ],
    "bonuses": [],  # e.g. {"key": "personal_project", "op": "==", "value": true, "points": 10}
    "overrides": {},  # e.g. {"U017": {"criteria": [...]}}: weights specific to one university
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
        return float(x)  # 1 and 1.0 are the same rule
    if isinstance(x, dict):
        return {k: _canon(v) for k, v in sorted(x.items())}
    return [_canon(v) for v in x]


def config_id(config) -> str:
    """Version = hash of the rules' CONTENT (`name` is not part of it): same rules ⇒ same id."""
    content = _canon({k: v for k, v in config.items() if k != "name"})
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def _const(key, v):
    """Rule constant: a CEFR level in letters becomes its ordinal."""
    return CEFR.index(v) if key in CEFR_KEYS and isinstance(v, str) and v in CEFR else v


def validate(config, student_keys=None, university_keys=None):
    """Raises ValueError listing ALL errors. With `student_keys` / `university_keys` (attributes actually present in
    the data), also checks that each key exists: a typo is rejected before the run."""
    errors = []
    known_s = STUDENT_KEYS | set(student_keys or ()) if student_keys is not None else None
    known_u = UNIVERSITY_KEYS | set(university_keys or ()) if university_keys is not None else None

    def key_ok(where, key):
        if key is None:
            errors.append(f"{where}: missing 'key'")
        elif known_s is not None and key not in known_s:
            errors.append(
                f"{where}: unknown key {key!r} (built-in: {sorted(STUDENT_KEYS)}, "
                f"attributes: {sorted(known_s - STUDENT_KEYS)})"
            )

    def check_criteria(where, items):
        for i, c in enumerate(items):
            key_ok(f"{where}[{i}]", c.get("key"))
            if not isinstance(c.get("weight"), NUM):
                errors.append(f"{where}[{i}]: numeric 'weight' required")
            if not (isinstance(c.get("min"), NUM) and isinstance(c.get("max"), NUM) and c["min"] < c["max"]):
                errors.append(f"{where}[{i}]: 'min' < 'max' required")

    def check_bonuses(where, items):
        for i, b in enumerate(items):
            key_ok(f"{where}[{i}]", b.get("key"))
            if "value" not in b:
                errors.append(f"{where}[{i}]: 'value' required")
            elif b.get("key") in CEFR_KEYS and isinstance(b["value"], str) and b["value"] not in CEFR:
                errors.append(f"{where}[{i}]: unknown CEFR level {b['value']!r}")
            if b.get("op") not in OPS:
                errors.append(f"{where}[{i}]: unknown op {b.get('op')!r}")
            if not isinstance(b.get("points"), NUM):
                errors.append(f"{where}[{i}]: numeric 'points' required")

    check_criteria("criteria", config.get("criteria", []))
    check_bonuses("bonuses", config.get("bonuses", []))
    for i, e in enumerate(config.get("eliminatory", [])):
        key_ok(f"eliminatory[{i}]", e.get("key"))
        if e.get("op") not in OPS:
            errors.append(f"eliminatory[{i}]: unknown op {e.get('op')!r}")
        if ("ref" in e) == ("value" in e):
            errors.append(f"eliminatory[{i}]: exactly one of 'ref' or 'value'")
        if "ref" in e and known_u is not None and e["ref"] not in known_u:
            errors.append(f"eliminatory[{i}]: unknown university attribute {e['ref']!r} (known: {sorted(known_u)})")
        if "value" in e and e.get("key") in CEFR_KEYS and isinstance(e["value"], str) and e["value"] not in CEFR:
            errors.append(f"eliminatory[{i}]: unknown CEFR level {e['value']!r}")
    for uid, o in config.get("overrides", {}).items():
        if not isinstance(o, dict) or not (set(o) <= {"criteria", "bonuses"}):
            errors.append(f"overrides[{uid}]: only 'criteria' and 'bonuses' can be overridden")
            continue
        check_criteria(f"overrides[{uid}].criteria", o.get("criteria", []))
        check_bonuses(f"overrides[{uid}].bonuses", o.get("bonuses", []))
    for i, t in enumerate(config.get("tie_break", [])):
        key_ok(f"tie_break[{i}]", t.get("key"))
        if t.get("order", "desc") not in ("asc", "desc"):
            errors.append(f"tie_break[{i}]: 'order' must be asc|desc")
    if errors:
        raise ValueError("invalid configuration: " + "; ".join(errors))
    return config


def student_value(student, key, default=None):
    """Resolves a criterion: derived attributes, built-in numeric fields, then `attributes` (added criteria)."""
    if key == "english_cefr":
        return CEFR.index(student.english_cefr)
    if key in STUDENT_KEYS and key != "lottery":
        return getattr(student, key)
    return student.attributes.get(key, default)


def university_value(uni, key):
    """Built-in or added attribute. Absent ⇒ None ⇒ the threshold does not apply to this university."""
    if key == "min_cefr":
        return CEFR.index(uni.min_cefr)
    return getattr(uni, key) if key in UNIVERSITY_KEYS else uni.attributes.get(key)


def _label(key, v):
    return CEFR[v] if key in CEFR_KEYS and isinstance(v, int) and 0 <= v < len(CEFR) else v


def failed_thresholds(student, uni, config):
    """Eliminatory thresholds not met (empty list = eligible). Structured: the UI writes the text."""
    failed = []
    for rule in config.get("eliminatory", []):
        v = student_value(student, rule["key"], rule.get("default"))
        ref = university_value(uni, rule["ref"]) if "ref" in rule else _const(rule["key"], rule["value"])
        if ref is None:
            continue  # the university does not have this threshold
        if v is None or not OPS[rule["op"]](
            v, ref
        ):  # attribute missing for the student ⇒ ineligible (cautious; set `default`)
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
            continue  # criterion missing for this student ⇒ 0 points (documented; otherwise set `default`)
        total += c["weight"] * min(100.0, max(0.0, 100.0 * (v - c["min"]) / (c["max"] - c["min"])))
    for b in bonuses:
        v = student_value(student, b["key"], b.get("default"))
        if v is not None and OPS[b["op"]](v, _const(b["key"], b["value"])):
            total += b["points"]
    return round(total, 4)  # fixed rounding: no floating-point noise in equalities ⇒ identical replay


def rank_key(student, config, uni=None, score_value=None):
    """Sort key = the university's preference order. Ends with the id ⇒ strict total order."""
    key = [-(score(student, config, uni) if score_value is None else score_value)]
    for t in config.get("tie_break", []):
        v = student_value(student, t["key"], t.get("default", 0))
        if v is None or isinstance(v, bool) or not isinstance(v, NUM) or math.isnan(v):
            raise ValueError(f"tie_break {t['key']!r}: non-numeric value {v!r} for {student.id}")
        key.append(-v if t.get("order", "desc") == "desc" else v)
    key.append(student.id)
    return tuple(key)
