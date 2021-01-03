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


class IdBuilder:

    def __init__(self, secret_prefix, game_id):
        self.secret_prefix = secret_prefix
        self.game_id = game_id

    def get_team_id(self):
        return game_id_to_team_id(self.game_id)

    def get_organizer_id(self):
        return game_id_to_organizer_id(self.game_id)

    def get_channel_id(self):
        return game_id_to_channel_id(self.game_id)

    def build_slack_object_id(self, object_name):
        return build_slack_object_id(
            self.secret_prefix, object_name, self.game_id)

    def build_setup_view_id(self):
        return self.build_slack_object_id('game_setup_view')

    def build_guess_view_id(self):
        return self.build_slack_object_id('guess_view')

    def build_vote_view_id(self):
        return self.build_slack_object_id('vote_view')

    def build_guess_button_block_id(self):
        return self.build_slack_object_id('guess_button_block')

    def build_vote_button_block_id(self):
        return self.build_slack_object_id('vote_button_block')
