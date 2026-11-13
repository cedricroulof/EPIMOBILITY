#!/usr/bin/env python3
from collections import deque
from engine.models.Student import Student
from engine.models.University import University

class StudentPool:

    def __init__(self, pool: [Student]):
        self.pool = pool
        self.student_reject_propposal = None

    def add(self, student: Student):
        self.pool.append(student)

    def all_student_engaged(self):
        for s in self.pool:
            if s.choice is None:
                return False
        return True

    def unengage_the_student(self, r: str):
       for s in self.pool:
           if r == s.name:
               s.unengage()

    def get_target_uni(self, s: Student, uni_pool: [University]):
        uni_name = s.preferences[s.proposal_index]
        for u in uni_pool:
            if uni_name == u.name:
                return u

    def stable_marriage(self, uni_pool: [University], visual=False):
        cycle = 1
        unis = {u.name:u for u in uni_pool}
        students = {s.name:s for s in self.pool}

        for s in self.pool:
            s.reset()
        for u in uni_pool:
            u.reset()

        free = deque(self.pool)
        while free:
            s = free.popleft()
            if not s.has_proposal_left():
                cycle += 1
                continue
            target_name = s.current_target()
            uni = unis.get(target_name)

            if uni is None:
                s.proposal_index += 1
                free.append(s)
                cycle += 1
                continue
            evicted = s.engage(uni)

            if s.is_engaged():
                if evicted is not None:
                    other = students[evicted]
                    other.unengage()
                    free.append(other)
            else:
                free.append(s)
            cycle += 1


    def __str__(self):
        string = ""
        for s in self.pool:
            string += f"{s.name} -> ["
            for p in s.preferences:
                string += f" {p} "
            string += "]\n"
        return string
