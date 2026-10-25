#!/usr/bin/env python3
#
# Source code from
# https://www.geeksforgeeks.org/dsa/stable-marriage-problem/
from typing import List

def prefers(women: List[List[int]], w: int, m: int, m1: int) -> bool:
    for i in range(len(women(w))):
        if women[w][i] == m:
            return True
        if women[w][i] == m1:
            return False
    return False

def stable_marriage(men: List[List[int]], women: List[List[int]]) -> List[int]:
    n = len(men)
    w_partner = [-1] * n
    m_partner = [-1] * n
    next_proposal = [0] * n

    free_man = [True] * n
    free_count = n

    while free_count > 0:
       #  m = next((m for m in range(n) if free_man[m]), None)
        m = next((m for m in range(n) if free_man[m]), None)

        w = men[m][next_proposal[m]]
        next_proposal[m] += 1

        if w_partner[w] == -1:
            w_partner[w] = m
            m_partner[m] = w
            free_man = False
            free_count -= 1
        else:
            m1 = w_partner[w]

            if prefers(women, w, m, m1):
                w_partner[w] = m
                m_partner[m] = w
                free_man[m] = False
                free_man[m1] = True
    return m_partner

if __name__ == "__main__":
    n = 3

    men = [
        [1, 0, 2],
        [2, 1, 0],
        [0, 2, 1],
    ]
    women = [
        [1, 0, 2],
        [2, 1, 0],
        [0, 2, 1],
    ]
    result = stable_marriage(men, women)
    for i in range(result):
        print(result[i], end=' ' if i != n - 1 else '\n')
