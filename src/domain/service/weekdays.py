from datetime import date, timedelta

from dateutil import easter
import holidays

feriados = [(1, 1), (21, 4), (1, 5), (7, 9), (12, 10), (2, 11), (15, 11), (25, 12)]


def findpascoa(ano: int):
    pascoa = easter.easter(ano)

    return (pascoa.day - 2, pascoa.month)


def gethollidays(ano: int):

    pascoa = easter.easter(ano)

    sextafeirasanta = (pascoa.day - 2, pascoa.month)
    carnaval_datetime = pascoa - timedelta(days=47)
    carnaval_terca = (carnaval_datetime.day, carnaval_datetime.month)
    carnaval_segunda = (carnaval_terca[0] - 1, carnaval_terca[1])

    ext_feriado = [x[:] for x in feriados]
    ext_feriado.append(sextafeirasanta)
    ext_feriado.append(carnaval_terca)
    ext_feriado.append(carnaval_segunda)

    return ext_feriado


def get_weekdays(month: int, year: int):
    weekdays: list[date] = []

    start_date = date(year, month, 1)

    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    current_date = start_date

    this_year_feriados = gethollidays(year)

    while current_date <= end_date:
        dia = (current_date.day, current_date.month)
        if (current_date.weekday() < 5) and (dia not in this_year_feriados):
            weekdays.append(current_date)
        current_date += timedelta(days=1)

    return weekdays


def get_weekdays_from_range(start: date, end: date):
    weekdays: list[date] = []

    if start > end:
        start, end = end, start

    current_date = start
    
    # Cache holidays by year to avoid redundant calculations
    holidays_by_year = {}

    while current_date <= end:
        # Get holidays for the current year if not cached
        if current_date.year not in holidays_by_year:
            holidays_by_year[current_date.year] = gethollidays(current_date.year)
        
        dia = (current_date.day, current_date.month)
        current_year_holidays = holidays_by_year[current_date.year]
        
        # Check if it's a weekday (Monday=0 to Friday=4) and not a holiday
        if (current_date.weekday() < 5) and (dia not in current_year_holidays):
            weekdays.append(current_date)
        
        current_date += timedelta(days=1)

    return weekdays

def get_weekdays_lib(start: date, end: date):
    holidays = set(holidays.Brazil(years=range(start.year, end.year+1)))
    
    weekdays = get_weekdays_from_range(start, end)
    
    return [day for day in weekdays if day not in holidays]

def is_weekday(d: date):
    weekdays = get_weekdays_from_range(d, d)
    return d in weekdays

def is_holliday_bridge(d: date):
    #checar se é ponte
    ...

if __name__ == "__main__":

    dias = [x.strftime("%d-%m-%Y") for x in get_weekdays(9, 2022)]
    print(dias)

    dias = [x.strftime("%d-%m-%Y") for x in get_weekdays(10, 2022)]
    print(dias)

    dias = [x.strftime("%d-%m-%Y") for x in get_weekdays(11, 2022)]
    print(dias)

    vinte = gethollidays(2021)
    print(vinte)
