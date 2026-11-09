"""English scale common to the tests: each CEFR band is worth the same position (0–100) whatever the test,
with linear interpolation inside the band. A TOEIC 945 and an IELTS 7.0 (both at the start of C1)
are worth 80 points: fair between applicants, which a normalization on the raw scale does not provide.

Sources: ETS, "Mapping the TOEIC Listening and Reading Test Scores to the CEFR";
IELTS, "IELTS and the CEFR" (ielts.org). The TOEIC L&R does not certify C2: its maximum is worth 100 points but stays
labeled C1.
"""

CEFR = ["A1", "A2", "B1", "B2", "C1", "C2"]
BANDS = {  # (entry threshold, level)
    "TOEIC": [(10, "A1"), (225, "A2"), (550, "B1"), (785, "B2"), (945, "C1")],
    "IELTS": [(0.0, "A1"), (3.0, "A2"), (4.0, "B1"), (5.5, "B2"), (7.0, "C1"), (8.5, "C2")],
}
ANCHORS = {  # (score, points): start of each band, then the top of the scale
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
