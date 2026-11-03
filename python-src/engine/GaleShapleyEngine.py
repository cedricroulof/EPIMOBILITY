#!/usr/bin/env python3

class StudentPool:

    def __init__(self, pool: [Student]):
        self.pool = pool
        self.engaged_pool = []
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
        while not self.all_student_engaged():
            if visual:
                print(f" ================= cycle {cycle} ================= ")
            for s in self.pool:
                if visual:
                    print(f"+++ student {s.name} +++")
                if s.is_engaged():
                    continue
                target_uni = self.get_target_uni(s, uni_pool)
                s_rejected = s.engage(target_uni)
                if visual:
                    print(f"{s.name} student choice: {s.choice}")
                if s_rejected is not None:
                    self.unengage_the_student(s_rejected)
            cycle += 1

    def __str__(self):
        string = ""
        for s in self.pool:
            string += f"{s.name} -> ["
            for p in s.preferences:
                string += f" {p} "
            string += "]\n"
        return string
