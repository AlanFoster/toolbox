import math
from datetime import datetime


def pretty_date(date):
    now = datetime.now()
    difference = now - date

    if difference.seconds < 60:
        return f"{difference.seconds} seconds ago"
    elif difference.seconds < 3600:
        return f"{math.floor(difference.seconds / 3600)} minutes ago"
    elif difference.seconds < (3600 * 24):
        return f"{math.floor(difference.seconds / 3600)} hours ago"
    else:
        return f"{difference.days} days ago"
