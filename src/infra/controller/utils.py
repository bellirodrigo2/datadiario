from datetime import date, datetime

from dateutil import parser as date_parser


def parse_date(date_str: str) -> date:
    """Parse date string in multiple formats using dateutil as primary method"""
    # First try dateutil parser - it's very flexible and handles most formats
    try:
        parsed_dt = date_parser.parse(
            date_str, dayfirst=True
        )  # Assume DD/MM/YYYY format by default
        return parsed_dt.date()
    except (ValueError, TypeError):
        pass

    # Fallback to manual format parsing
    formats = [
        "%Y-%m-%d",  # 2022-12-25
        "%d/%m/%Y",  # 25/12/2022
        "%m/%d/%Y",  # 12/25/2022
        "%d-%m-%Y",  # 25-12-2022
        "%Y%m%d",  # 20221225
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # Final fallback to ISO format
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(
            f"Unable to parse date '{date_str}'. Supported formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, YYYYMMDD, and most common date formats"
        )
