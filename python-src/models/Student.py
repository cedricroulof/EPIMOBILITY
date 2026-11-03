#!/usr/bin/env python3

class Student:

    def __init__(self, name: str, preferences: [str]):
        self.name = name
        self.preferences = preferences
        self.choice = None
        self.proposal_index = 0

    def engage(self, uni: University):
        if uni.prefers(self.name):
            self.choice = uni.name
            student_rejected = uni.choice
            uni.choice = self.name
            return student_rejected
        self.proposal_index += 1
        return

    def is_engaged(self):
        return self.choice is not None

    def unengage(self):
        self.choice = None
