import holidays
from datetime import date

from src.domain.service.weekdays import gethollidays

def library_holidays(y: int):
    return [(day.day, day.month) for day in holidays.Brazil(years=y)]

for y in range(2020, 2025):
    print(y)
    print("\t",set(set(library_holidays(y)) - set(gethollidays(y))))
    print("\t",set(set(gethollidays(y)) - set(library_holidays(y))))
    
print(holidays.Brazil(years=2024).items())