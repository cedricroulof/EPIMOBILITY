#!/usr/bin/env python3

class University:

    def __init__(self, name: str, preferences: [str]):
        self.name = name
        self.preferences = preferences
        self.choice = None

    def get_uni_choice_index_preferences(self) -> int:
        if self.choice is not None:
            for i in range(len(self.preferences)):
                if self.preferences[i] == self.choice:
                    return i
        return 999

    def get_uni_index_preferences(self, uni: str) -> int:
        for i in range(len(self.preferences)):
            if self.preferences[i] == uni:
                return i
        return -1

    def prefers(self, s: str) -> bool:
        choice = self.get_uni_choice_index_preferences()
        pretendant = self.get_uni_index_preferences(s)
        return pretendant < choice
