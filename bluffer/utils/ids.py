def build_game_id(team_id, channel_id, organizer_id, trigger_id):
    return '{}&{}&{}&{}'.format(team_id, channel_id, organizer_id, trigger_id)


def build_slack_object_id(secret_prefix, object_name, game_id):
    return '{}#{}#{}'.format(secret_prefix, object_name, game_id)


def slack_object_id_to_game_id(slack_object_id):
    ids = slack_object_id.split('#')
    return ids[-1]


def game_id_to_ids(game_id):
    return game_id.split('&')


def game_id_to_channel_id(game_id):
    return game_id_to_ids(game_id)[1]


def game_id_to_organizer_id(game_id):
    return game_id_to_ids(game_id)[2]


def user_display(user_id):
    return '<@{}>'.format(user_id)


def user_displays(user_ids):
    return ' '.join([user_display(id_) for id_ in user_ids])
