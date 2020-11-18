def compute_remaining_potential_guessers(potential_guessers, guessers):
    return {pv: potential_guessers[pv]
            for pv in potential_guessers
            if pv not in guessers}


def compute_remaining_potential_voters(potential_voters, voters):
    return {pv: potential_voters[pv]
            for pv in potential_voters
            if pv not in voters}


def user_display(user_id):
    return '<@{}>'.format(user_id)


def user_displays(user_ids):
    return ' '.join([user_display(id_) for id_ in user_ids])


def sort_users(users):
    res = sorted(users, key=lambda k: users[k][0])
    return res


def build_users_msg(users, kind, no_users_msg):
    if not users:
        return no_users_msg
    users = sort_users(users)
    msg = '{}: {}'.format(kind, user_displays(users))
    return msg
