"""Preprocessing shared by the algorithms (`Problem`) and shape of their result (`Result`): like-for-like comparison."""

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field

from .. import rules


class Problem:
    """Shared precomputation: score of each (student, wish), eligibility, and rank of each applicant at each university.
    Validates the configuration AGAINST the data (keys actually present) and the inputs (distinct wishes, known
    universities)."""

    def __init__(self, universities, students, config):
        s_keys = {k for s in students for k in s.attributes}
        u_keys = {k for u in universities for k in u.attributes}
        rules.validate(config, student_keys=s_keys, university_keys=u_keys)
        self.students = students
        self.unis = {u.id: u for u in universities}
        self.cap = {u.id: u.capacity for u in universities}
        errors = [f"{u.id}: negative capacity" for u in universities if u.capacity < 0]
        errors += [f"{s.id}: duplicate wishes" for s in students if len(set(s.wishes)) != len(s.wishes)]
        errors += [f"{s.id}: unknown university {w!r}" for s in students for w in s.wishes if w not in self.unis]
        if errors:
            raise ValueError("invalid inputs: " + "; ".join(errors[:10]))
        self.score = {}  # (s, u) -> score of s for u (may depend on u via `overrides`)
        self.reasons = {}  # (s, u) -> failed thresholds (empty = eligible)
        self.rank = {u: {} for u in self.unis}  # u -> {s: position in u's preference order} (eligible students only)
        self.eligible = {}  # s -> their eligible wishes, in their own order
        applicants = defaultdict(list)
        overrides = config.get("overrides", {})
        for s in students:
            self.eligible[s.id] = []
            base = rules.score(s, config)  # once per student; recomputed only for universities with an override
            for u in s.wishes:
                uni = self.unis[u]
                self.score[(s.id, u)] = rules.score(s, config, uni) if u in overrides else base
                failed = rules.failed_thresholds(s, uni, config)
                self.reasons[(s.id, u)] = failed
                if not failed:
                    applicants[u].append(s)
                    self.eligible[s.id].append(u)
        for u, apps in applicants.items():
            uni = self.unis[u]
            apps.sort(key=lambda s: rules.rank_key(s, config, uni, self.score[(s.id, u)]))
            self.rank[u] = {s.id: i for i, s in enumerate(apps)}


@dataclass
class Result:
    algorithm: str
    assignment: dict  # student -> university | None
    cutoff: dict = field(default_factory=dict)  # u -> final cutoff: lowest admitted score
    round_cutoff: dict = field(
        default_factory=dict
    )  # boston: (u, round) -> last admitted in that round (None = already full)

    def output_hash(self) -> str:
        return hashlib.sha256(json.dumps(sorted(self.assignment.items())).encode()).hexdigest()[:16]
