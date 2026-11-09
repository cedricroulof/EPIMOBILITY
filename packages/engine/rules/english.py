"""Échelle d'anglais commune aux tests : chaque bande CEFR vaut la même position (0–100) quel que soit le test,
avec interpolation linéaire à l'intérieur de la bande. Un TOEIC 945 et un IELTS 7.0 (tous deux début de C1)
valent 80 points : équitable entre candidats, ce que ne donne pas une normalisation sur l'échelle brute.

Sources : ETS, « Mapping the TOEIC Listening and Reading Test Scores to the CEFR » ;
IELTS, « IELTS and the CEFR » (ielts.org).
Le TOEIC L&R n'atteste pas le C2 : son maximum vaut 100 points mais reste étiqueté C1.
"""

CEFR = ["A1", "A2", "B1", "B2", "C1", "C2"]
BANDS = {  # (seuil d'entrée, niveau)
    "TOEIC": [(10, "A1"), (225, "A2"), (550, "B1"), (785, "B2"), (945, "C1")],
    "IELTS": [(0.0, "A1"), (3.0, "A2"), (4.0, "B1"), (5.5, "B2"), (7.0, "C1"), (8.5, "C2")],
}
ANCHORS = {  # (score, points) : début de chaque bande, puis sommet de l'échelle
    "TOEIC": [(10, 0), (225, 20), (550, 40), (785, 60), (945, 80), (990, 100)],
    "IELTS": [(0.0, 0), (3.0, 20), (4.0, 40), (5.5, 60), (7.0, 80), (8.5, 100)],
}


def cefr(test: str, score: float) -> str:
    level = BANDS[test][0][1]
    for lo, lvl in BANDS[test]:
        if score >= lo:
            level = lvl
    return level


def pct(test: str, score: float) -> float:
    anchors = ANCHORS[test]
    if score <= anchors[0][0]:
        return 0.0
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:], strict=False):
        if score <= x1:
            return round(y0 + (y1 - y0) * (score - x0) / (x1 - x0), 2)
    return 100.0
