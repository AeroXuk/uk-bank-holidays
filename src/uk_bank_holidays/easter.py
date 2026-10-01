"""Date of Easter Sunday (Gregorian calendar).

A port of the T-SQL ``CalculateEasterDay`` function from the original blog post, itself based on
the Anonymous Gregorian algorithm (Meeus/Jones/Butcher). Valid for years 1583 onwards.
"""

from datetime import date


def easter_sunday(year: int) -> date:
    metonic = year % 19
    century = year // 100
    year_in_century = year % 100
    a = (19 * metonic + century - century // 4 - (century - (century + 8) // 25 + 1) // 3 + 15) % 30
    b = (32 + 2 * (century % 4) + 2 * (year_in_century // 4) - a - year_in_century % 4) % 7
    d = a + b - 7 * ((metonic + 11 * a + 22 * b) // 451) + 114
    return date(year, d // 31, d % 31 + 1)
