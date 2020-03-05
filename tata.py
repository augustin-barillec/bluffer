def game_db_to_game_dict(team_id, game_id):
    return None


def game_dict_to_game_instance(game_dict):
    return None


def game_instance_to_game_dict(game_instance):
    return None


def game_dict_to_game_db(game_dict):
    return None


def to_pre_guess_stage(request):
    publisher.publish(topic_path, data=data)


def pre_guess_stage_to_guess_stage(event, context):
    pass


def guess_stage_to_pre_vote_stage(event, context):
    pass


def pre_vote_stage_to_vote_stage(event, context):
    pass


def vote_stage_to_pre_results_stage(event, context):
    pass

def pre_results_stage_to_results_stage(event, context):
    pass

def


class Game:
    def __init__(
            self,
            game_id,
            slack_client,
            bucket,
            question,
            truth,
            time_to_guess,
            time_to_vote,
            stage,
            upper_ts=None,
            lower_ts=None,
            guess_start_datetime=None,
            vote_start_datetime=None,
            potential_players=None,
            players=None
    ):
        self.game_id = game_id
        self.question = question
        self.truth = truth
        self.time_to_guess = time_to_guess
        self.time_to_vote = time_to_vote
        self.stage = stage
        self.upper_ts = upper_ts
        self.lower_ts = lower_ts
        self.guess_start_datetime = guess_start_datetime
        self.vote_start_datetime = vote_start_datetime
        self.potential_players = potential_players
        self.players = players

        self.channel_id = ids.game_id_to_channel_id(game_id)
        self.organizer_id = ids.game_id_to_organizer_id(game_id)

    def pre_guess_stage_to_guess_stage(self):
        pass






