#!/usr/bin/env python3
#
# Source code from
# Video example : https://youtu.be/0m_YW1zVs-Q?si=r3_IDyVNzvjlh9z0

from models.Student import Student
from models.University import University
from engine.GaleShapleyEngine import StudentPool

if __name__ == "__main__":

    # Student init
    pool = []
    s1 = Student("toto", ['u1', 'u2', 'u3'])
    s2 = Student("tata", ['u3', 'u1', 'u2'])
    s3 = Student("titi", ['u3', 'u2', 'u1'])
    pool.append(s1)
    pool.append(s2)
    pool.append(s3)

    spool = StudentPool(pool)
    print(spool)

    # University init
    u1 = University("u1", ["toto", "titi", "tata"])
    u2 = University("u2", ["toto", "tata", "titi"])
    u3 = University("u3", ["tata", "toto", "titi"])
    upool = [u1, u2, u3]

    spool.stable_marriage(upool, True)

    for s in spool.pool:
        print(f"{s.name} -> {s.choice}")
    print("=============================")
    for u in upool:
        print(f"{u.name} -> {u.choice}")

    # Video example
    A = Student("A", ["O", "M", "N", "L", "P"])
    B = Student("B", ["P", "N", "M", "L", "O"])
    C = Student("C", ["M", "P", "L", "O", "N"])
    D = Student("D", ["P", "M", "O", "N", "L"])
    E = Student("E", ["O", "L", "M", "N", "P"])
    sp = StudentPool([A, B, C, D, E])

    L = University("L", ["D", "B", "E", "C", "A"])
    M = University("M", ["B", "A", "D", "C", "E"])
    N = University("N", ["A", "C", "E", "D", "B"])
    O = University("O", ["D", "A", "C", "B", "E"])
    P = University("P", ["B", "E", "A", "C", "D"])
    up = [L, M, N, O, P]
    # print(sp)
    # sp.stable_marriage(up, True)
    # for s in sp.pool:
    #     print(f"{s.name} -> {s.choice}")
    # print("=============================")
    # for u in up:
    #     print(f"{u.name} -> {u.choice}")

    # Fictional test from Gemini
    S1 = Student("S1", ["U1", "U2", "U3", "U4", "U5"])
    S2 = Student("S2", ["U2", "U1", "U4", "U3", "U5"])
    S3 = Student("S3", ["U1", "U3", "U2", "U5", "U4"])
    S4 = Student("S4", ["U3", "U4", "U1", "U2", "U5"])
    S5 = Student("S5", ["U1", "U2", "U5", "U3", "U4"])
    ssp = StudentPool([S1, S2, S3, S4, S5])

    U1 = University("U1", ["S2", "S1", "S3", "S5", "S4"])
    U2 = University("U2", ["S1", "S2", "S3", "S4", "S5"])
    U3 = University("U3", ["S4", "S3", "S1", "S5", "S2"])
    U4 = University("U4", ["S3", "S2", "S5", "S4", "S1"])
    U5 = University("U5", ["S5", "S4", "S1", "S2", "S3"])
    uup = [U1, U2, U3, U4, U5]

    # Expected final output: each SX -> UX where X = [1 ... 5]
    ssp.stable_marriage(uup, True)
    for s in ssp.pool:
        print(f"{s.name} -> {s.choice}")
    print("=============================")
    for u in uup:
        print(f"{u.name} -> {u.choice}")
