from datetime import date, datetime, timedelta

import pytest
from src.domain.service.weekdays import (
    findpascoa,
    get_weekdays,
    get_weekdays_from_range,
    gethollidays,
)


class TestFindPascoa:
    """Test the findpascoa function that calculates Easter Friday."""

    def test_findpascoa_2023(self):
        # Easter 2023 was on April 9, so Good Friday was April 7
        result = findpascoa(2023)
        assert result == (7, 4)  # (day, month)

    def test_findpascoa_2024(self):
        # Easter 2024 was on March 31, so Good Friday was March 29
        result = findpascoa(2024)
        assert result == (29, 3)

    def test_findpascoa_2025(self):
        # Easter 2025 will be on April 20, so Good Friday will be April 18
        result = findpascoa(2025)
        assert result == (18, 4)

    def test_findpascoa_returns_tuple(self):
        result = findpascoa(2023)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], int)  # day
        assert isinstance(result[1], int)  # month


class TestGetHollidays:
    """Test the gethollidays function that returns all holidays for a year."""

    def test_gethollidays_contains_fixed_holidays(self):
        holidays = gethollidays(2023)

        # Check that all fixed holidays are included
        fixed_holidays = [
            (1, 1),
            (21, 4),
            (1, 5),
            (7, 9),
            (12, 10),
            (2, 11),
            (15, 11),
            (25, 12),
        ]
        for holiday in fixed_holidays:
            assert holiday in holidays

    def test_gethollidays_contains_easter_holidays(self):
        holidays = gethollidays(2023)

        # Should contain Good Friday (April 7, 2023)
        assert (7, 4) in holidays

        # Should contain Carnival Monday and Tuesday
        # Carnival 2023 was February 20-21
        assert (20, 2) in holidays  # Monday
        assert (21, 2) in holidays  # Tuesday

    def test_gethollidays_different_years(self):
        holidays_2023 = gethollidays(2023)
        holidays_2024 = gethollidays(2024)

        # Should have different Easter-related dates
        assert holidays_2023 != holidays_2024

        # But should have the same fixed holidays
        fixed_holidays = [
            (1, 1),
            (21, 4),
            (1, 5),
            (7, 9),
            (12, 10),
            (2, 11),
            (15, 11),
            (25, 12),
        ]
        for holiday in fixed_holidays:
            assert holiday in holidays_2023
            assert holiday in holidays_2024

    def test_gethollidays_returns_list(self):
        holidays = gethollidays(2023)
        assert isinstance(holidays, list)
        assert len(holidays) > 8  # At least the fixed holidays plus Easter-related ones


class TestGetWeekdays:
    """Test the get_weekdays function that returns weekdays for a specific month."""

    def test_get_weekdays_january_2023(self):
        # January 2023: 1st was Sunday, so weekdays start from Monday 2nd
        # New Year's Day (1/1) is a holiday, so it shouldn't be included anyway
        weekdays = get_weekdays(1, 2023)

        # Check that it returns date objects
        assert all(isinstance(day, date) for day in weekdays)

        # Check that all returned days are weekdays (Monday=0 to Friday=4)
        assert all(day.weekday() < 5 for day in weekdays)

        # Check that January 1 (New Year) is not included
        assert not any(day.day == 1 and day.month == 1 for day in weekdays)

    def test_get_weekdays_excludes_weekends(self):
        weekdays = get_weekdays(3, 2023)  # March 2023

        # Should not contain any Saturdays (weekday=5) or Sundays (weekday=6)
        weekend_days = [day for day in weekdays if day.weekday() >= 5]
        assert len(weekend_days) == 0

    def test_get_weekdays_excludes_holidays(self):
        weekdays = get_weekdays(4, 2023)  # April 2023

        # Should not contain Good Friday (April 7, 2023) or Tiradentes (April 21)
        assert not any(
            day.day == 7 and day.month == 4 for day in weekdays
        )  # Good Friday
        assert not any(
            day.day == 21 and day.month == 4 for day in weekdays
        )  # Tiradentes

    def test_get_weekdays_december_handles_year_boundary(self):
        weekdays = get_weekdays(12, 2023)

        # Should only contain December 2023 days
        assert all(day.year == 2023 and day.month == 12 for day in weekdays)

        # Should not contain Christmas (December 25)
        assert not any(day.day == 25 for day in weekdays)

    def test_get_weekdays_february_leap_year(self):
        # Test leap year handling
        weekdays_2024 = get_weekdays(2, 2024)  # 2024 is a leap year
        weekdays_2023 = get_weekdays(2, 2023)  # 2023 is not a leap year

        # 2024 should have more days in February
        feb_days_2024 = max(day.day for day in weekdays_2024)
        feb_days_2023 = max(day.day for day in weekdays_2023)

        assert feb_days_2024 >= feb_days_2023


class TestGetWeekdaysFromRange:
    """Test the get_weekdays_from_range function that returns weekdays for a date range."""

    def test_get_weekdays_from_range_single_month(self):
        start = date(2023, 3, 1)
        end = date(2023, 3, 31)

        weekdays = get_weekdays_from_range(start, end)

        # Check that it returns date objects
        assert all(isinstance(day, date) for day in weekdays)

        # Check that all dates are within the range
        assert all(start <= day <= end for day in weekdays)

        # Check that all returned days are weekdays
        assert all(day.weekday() < 5 for day in weekdays)

    def test_get_weekdays_from_range_multi_year(self):
        start = date(2023, 12, 15)
        end = date(2024, 1, 15)

        weekdays = get_weekdays_from_range(start, end)

        # Should contain days from both years
        years = {day.year for day in weekdays}
        assert 2023 in years
        assert 2024 in years

        # Should not contain New Year's Day 2024
        assert date(2024, 1, 1) not in weekdays

        # Should not contain Christmas 2023
        assert date(2023, 12, 25) not in weekdays

    def test_get_weekdays_from_range_reversed_dates(self):
        start = date(2023, 3, 15)
        end = date(2023, 3, 1)  # End before start

        weekdays = get_weekdays_from_range(start, end)

        # Should handle reversed dates correctly
        assert all(date(2023, 3, 1) <= day <= date(2023, 3, 15) for day in weekdays)

    def test_get_weekdays_from_range_excludes_holidays(self):
        # Range that includes Easter 2023
        start = date(2023, 4, 1)
        end = date(2023, 4, 30)

        weekdays = get_weekdays_from_range(start, end)

        # Should not contain Good Friday (April 7) or Tiradentes (April 21)
        assert date(2023, 4, 7) not in weekdays  # Good Friday
        assert date(2023, 4, 21) not in weekdays  # Tiradentes

    def test_get_weekdays_from_range_excludes_weekends(self):
        start = date(2023, 3, 1)  # Wednesday
        end = date(2023, 3, 7)  # Tuesday (includes first weekend)

        weekdays = get_weekdays_from_range(start, end)

        # Should not contain Saturday (March 4) or Sunday (March 5)
        weekend_days = [day for day in weekdays if day.weekday() >= 5]
        assert len(weekend_days) == 0

    def test_get_weekdays_from_range_single_day(self):
        # Test with same start and end date (weekday)
        single_day = date(2023, 3, 1)  # Wednesday
        weekdays = get_weekdays_from_range(single_day, single_day)

        assert len(weekdays) == 1
        assert weekdays[0] == single_day

    def test_get_weekdays_from_range_single_weekend_day(self):
        # Test with same start and end date (weekend)
        saturday = date(2023, 3, 4)  # Saturday
        weekdays = get_weekdays_from_range(saturday, saturday)

        assert len(weekdays) == 0  # Weekend day should be excluded

    def test_get_weekdays_from_range_single_holiday(self):
        # Test with New Year's Day
        new_years = date(2023, 1, 1)
        weekdays = get_weekdays_from_range(new_years, new_years)

        assert len(weekdays) == 0  # Holiday should be excluded

    def test_get_weekdays_from_range_performance_multi_year(self):
        # Test performance with a large range (should use holiday caching)
        start = date(2020, 1, 1)
        end = date(2023, 12, 31)

        weekdays = get_weekdays_from_range(start, end)

        # Should return a reasonable number of weekdays
        assert len(weekdays) > 1000  # 4 years of weekdays minus holidays
        assert all(isinstance(day, date) for day in weekdays)
        assert all(day.weekday() < 5 for day in weekdays)

    def test_get_weekdays_from_range_carnival_holidays(self):
        # Test that carnival holidays are properly excluded
        # Carnival 2023 was February 20-21
        start = date(2023, 2, 19)
        end = date(2023, 2, 22)

        weekdays = get_weekdays_from_range(start, end)

        # Should not contain Carnival Monday (Feb 20) or Tuesday (Feb 21)
        assert date(2023, 2, 20) not in weekdays  # Carnival Monday
        assert date(2023, 2, 21) not in weekdays  # Carnival Tuesday

        # Should contain Sunday Feb 19 is excluded (weekend)
        # Should contain Wednesday Feb 22 (if it's a weekday and not holiday)
        assert date(2023, 2, 19) not in weekdays  # Sunday

    def test_get_weekdays_from_range_empty_result(self):
        # Test range that contains only weekends and holidays
        # December 24-26, 2023: Sunday, Monday (not holiday), Tuesday (Christmas moved)
        start = date(2023, 12, 23)  # Saturday
        end = date(2023, 12, 25)  # Monday (Christmas)

        weekdays = get_weekdays_from_range(start, end)

        # Should exclude Saturday (23rd), Sunday (24th), and Christmas (25th)
        christmas_weekend = [date(2023, 12, 23), date(2023, 12, 24), date(2023, 12, 25)]
        for day in christmas_weekend:
            assert day not in weekdays


class TestWeekdaysIntegration:
    """Integration tests for the weekdays module."""

    def test_consistency_between_functions(self):
        # Test that get_weekdays and get_weekdays_from_range return consistent results
        # for the same month
        year, month = 2023, 3

        weekdays_monthly = get_weekdays(month, year)

        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)

        weekdays_range = get_weekdays_from_range(start, end)

        # Both functions now return date objects, so we can compare directly
        assert set(weekdays_monthly) == set(weekdays_range)

    def test_holiday_calculation_consistency(self):
        # Test that holiday calculations are consistent across years
        for year in [2020, 2021, 2022, 2023, 2024, 2025]:
            holidays = gethollidays(year)

            # Should always contain the fixed holidays
            fixed_holidays = [
                (1, 1),
                (21, 4),
                (1, 5),
                (7, 9),
                (12, 10),
                (2, 11),
                (15, 11),
                (25, 12),
            ]
            for holiday in fixed_holidays:
                assert (
                    holiday in holidays
                ), f"Fixed holiday {holiday} missing for year {year}"

            # Should contain Easter-related holidays (dates vary by year)
            easter_related = [h for h in holidays if h not in fixed_holidays]
            assert (
                len(easter_related) >= 3
            ), f"Missing Easter-related holidays for year {year}"  # Good Friday + 2 Carnival days
