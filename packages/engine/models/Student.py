#!/usr/bin/env python3
from engine.models.University import University

class Student:

    def __init__(self, name: str, preferences: [str]):
        self.name = name
        self.preferences = preferences
        self.choice = None
        self.proposal_index = 0

    def engage(self, uni: University):
        accepted, evicted = uni.propose(self.name)
        if accepted:
            self.choice = uni.name
            return evicted
        self.proposal_index += 1

    def current_target(self):
        return self.preferences[self.proposal_index]

    def has_proposal_left(self) -> bool:
        return self.proposal_index < len(self.preferences)

    def is_engaged(self):
        return self.choice is not None

    def unengage(self):
        self.choice = None
        self.proposal_index += 1

    def reset(self):
        self.choice = None
        self.proposal_index = 0
