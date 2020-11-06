import pytz
from datetime import datetime, timedelta


def get_now():
    return datetime.now(pytz.UTC)


compact_format = '%Y%m%d_%H%M%S'


def datetime_to_compact(datetime_):
    return datetime_.strftime(compact_format)


def compact_to_datetime(compact):
    return datetime.strptime(compact, compact_format)


def compute_deadline(start_datetime, time_left):
    return start_datetime + timedelta(seconds=time_left)


def datetime1_minus_datetime2(d1, d2):
    return int((d1 - d2).total_seconds())


def compute_time_left(deadline):
    return datetime1_minus_datetime2(deadline, get_now())


def total_seconds_to_minutes_seconds(total_seconds):
    return total_seconds // 60, total_seconds % 60


def build_time_display(total_seconds):
    if total_seconds < 0:
        return '0min 0s'
    minutes, seconds = total_seconds_to_minutes_seconds(
        total_seconds)
    seconds_approx = seconds - seconds % 5
    return '{}min {}s'.format(minutes, seconds_approx)
