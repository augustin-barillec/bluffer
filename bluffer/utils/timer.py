from datetime import datetime, timedelta


def compute_deadline(start_datetime, time_left):
    return start_datetime + timedelta(seconds=time_left)


def compute_time_left(deadline):
    return int((deadline - datetime.now()).total_seconds())


def convert_to_min_sec(time):
    nb_of_minutes = time // 60
    nb_of_seconds = time % 60
    return nb_of_minutes, nb_of_seconds


def build_time_display(time):
    if time < 0:
        return '0min 0s'
    nb_of_minutes, nb_of_seconds = convert_to_min_sec(time)
    nb_of_seconds_approx = nb_of_seconds - nb_of_seconds % 5
    return '{}min {}s'.format(nb_of_minutes, nb_of_seconds_approx)



