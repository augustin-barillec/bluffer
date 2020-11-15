def build_game_id(
        slash_command_compact,
        team_id,
        channel_id,
        organizer_id,
        trigger_id):

    return '{}&{}&{}&{}&{}'.format(
        slash_command_compact, team_id, channel_id, organizer_id, trigger_id)


def build_slack_object_id(secret_prefix, object_name, game_id):
    return '{}#{}#{}'.format(secret_prefix, object_name, game_id)


def slack_object_id_to_game_id(slack_object_id):
    ids = slack_object_id.split('#')
    return ids[-1]


def split_game_id(game_id):
    return game_id.split('&')


def game_id_to_slash_command_compact(game_id):
    splitted_game_id = split_game_id(game_id)
    return splitted_game_id[0]


def game_id_to_ids(game_id):
    splitted_game_id = split_game_id(game_id)
    return splitted_game_id[1:]


def game_id_to_team_id(game_id):
    return game_id_to_ids(game_id)[0]


def game_id_to_channel_id(game_id):
    return game_id_to_ids(game_id)[1]


def game_id_to_organizer_id(game_id):
    return game_id_to_ids(game_id)[2]


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
