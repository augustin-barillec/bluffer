def compute_remaining_potential_users(potential_users, users):
    return {pu: potential_users[pu]
            for pu in potential_users
            if pu not in users}


def compute_remaining_potential_guessers(potential_guessers, guessers):
    return compute_remaining_potential_users(potential_guessers, guessers)


def compute_remaining_potential_voters(potential_voters, voters):
    return compute_remaining_potential_users(potential_voters, voters)


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
