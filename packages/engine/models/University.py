#!/usr/bin/env python3
import math
class University:

    def __init__(self, name: str, preferences: [str]):
        self.name = name
        self.preferences = preferences
        self.choice = None
        self.rank = { s:i for i,s in enumerate(preferences) }

    def reset(self):
        self.choice = None

    def get_uni_choice_index_preferences(self) -> float:
        if self.choice is None:
            return math.inf
        return self.rank[self.choice]

    def get_uni_index_preferences(self, s: str) -> int:
        return self.rank.get(s, math.inf)

    def prefers(self, s: str) -> bool:
        choice = self.get_uni_choice_index_preferences()
        pretendant = self.get_uni_index_preferences(s)
        return pretendant < choice

    def propose(self, student: str) -> tuple[bool, str | None]:
        if not self.prefers(student):
            return False, None
        evicted = self.choice
        self.choice = student
        return True, evicted
