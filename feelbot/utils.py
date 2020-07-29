from datetime import datetime


def convert_datetime(
    date: str,
    clock: str = None,
    date_deliminator='/',
    clock_deliminator=':'
) -> datetime:
    date = list(map(int, date.strip().split(date_deliminator)))
    if len(date) == 2:
        month, day = date
        year = datetime.now().year
    elif len(date) == 3:
        year, month, day = date
    else:
        raise ValueError('Invalid date format')

    if clock is not None:
        hour, minute = map(int, clock.strip().split(clock_deliminator))
    else:
        hour, minute = 0, 0
    return datetime(year, month, day, hour=hour, minute=minute)
