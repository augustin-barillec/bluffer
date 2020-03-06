from bluffer.utils import *


def game_db_to_game_dict(team_id, game_id):
    return None


def game_dict_to_game_instance(game_dict):
    return None


def game_instance_to_game_dict(game_instance):
    return None


def game_dict_to_game_db(game_dict):
    return None

def slack_command_to_open_guess_set_up_view(request):
    open_guess_set_up_view()

def guess_set_up_view_submission_to_post_preparing_guess_stage_message(request):
    game_id = context['game_id']
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_token = team_id_to_slack_token(team_id)
    slack_client = SlackClient(token=token)

    game_dict = game_id_to_game_dict(game_id)

    title_block = blocks.build_title_block(organizer_id)
    pre_guess_stage_block = blocks.build_pre_guess_stage_block()

    upper_blocks = [title_block, pre_guess_stage_block]
    lower_blocks = [blocks.divider_block]

    upper_ts = slack_client.api_call(
        'chat.postMessage',
        channel=channel_id,
        blocks=upper_blocks)['ts']
    lower_ts = slack_client.api_call(
        'chat.postMessage',
        channel=channel_id,
        blocks=upper_blocks)['ts']

    game_dict['upper_ts'] = upper_ts
    game_dict['lower_ts'] = lower_ts

    potential_players = members.get_potential_players(
        slack_client, channel_id, organizer_id)

    game_dict['potential_players'] = potential_players

    game_dict_to_game_db(game_dict)

    trigger(guess_stage_to_vote_stage, game_id)

    return

def post_preparing_guess_stage_message_to_post_preparing_vote_message(request):

    start_process_datetime = datetime.now()


    game_id = context['game_id']
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_token = team_id_to_slack_token(team_id)
    slack_client = SlackClient(token=token)

    game_dict = game_id_to_game_dict(game_id)

    question_block = blocks.build_text_block(game_dict['question'])


    msg = 'Your guess'
    id_ = ids.build_slack_object_id(secret_prefix, object_name, game_id)
    guess_button_block = blocks.build_button_block(msg, id_)

    start_guess_datetime = datetime.now()
    time_left = compute_time_left(game_dict['time_left_to_guess'], start_guess_datetime)

    potential_players = game_dict['potential_players']
    remaining_potential_guessers = copy(potential_players)


    while True:
        if (datetime.now() - start_guess_datetime) > game_dict['time_to_left'] or
          len(remaining_potential_players) == 0:

            post preparing vote message

            trigger(next, game_id)
            return


        if (datetime.now() - start_process_datetime) > 60:
            trigger(post_preparing_guess_stage_message_to_post_preparing_vote_message, game_id)
            return


      game_dict = game_id_to_game_dict(game_id)

      guessers = get_guessers(game_dict)
      remaining_potential_guessers = potential_players - guessers

      time_left_to_guess_block = blocks.build_text_block((datetime.now() - start_guess_datetime))
      guessers_block = build_guessers_blocks(guessers)

      slack_client.api_call(
          'chat.update',
          channel=channel_id,
          ts=game_dict['lower_ts'],
          blocks=[guessers_block, time_left_to_guess_block])

      time.sleep(2)

def post_preparing_vote_message_to_post_computing_results_message(request):
    pass

def post_computing_results_message_to_post_results_message(request):
    pass

def post_results_message_to_delete_in_db(request):
    pass
















def preparing


def to_pre_guess_stage(request):

    publisher.publish(topic_path, data=data)


def pre_guess_stage_to_guess_stage(event, context):
    game_id = context['game_id']
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_token = team_id_to_slack_token(team_id)
    slack_client = SlackClient(token=token)

    game_dict = game_id_to_game_dict(game_id)

    title_block = blocks.build_title_block(organizer_id)
    pre_guess_stage_block = blocks.build_pre_guess_stage_block()

    upper_blocks = [title_block, pre_guess_stage_block]
    lower_blocks = [blocks.divider_block]

    upper_ts = slack_client.api_call(
        'chat.postMessage',
        channel=channel_id,
        blocks=upper_blocks)['ts']
    lower_ts = slack_client.api_call(
        'chat.postMessage',
        channel=channel_id,
        blocks=upper_blocks)['ts']

    game_dict['upper_ts'] = upper_ts
    game_dict['lower_ts'] = lower_ts

    potential_players = members.get_potential_players(
        slack_client, channel_id, organizer_id)

    game_dict['potential_players'] = potential_players

    game_dict_to_game_db(game_dict)

    trigger(guess_stage_to_vote_stage, game_id)

    return




def guess_stage_to_pre_vote_stage(event, context):
    call_datetime = datetime.now()
    while delta(datetime.now(), call_datetime) < 5 min or


def pre_vote_stage_to_vote_stage(event, context):
    pass


def vote_stage_to_pre_results_stage(event, context):
    pass


def pre_results_stage_to_results_stage(event, context):
    pass


def results_stage_to_over_stage(event, context):
    pass


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
        self.slack_client = slack_client
        self.bucket = bucket
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
        self.upper_ts = self.post_board('upper')
        self.lower_ts = self.post_board('lower')
        self.question_block = blocks.build_text_block(self.question)
        self.guess_button_block = self.build_guess_button_block()
        self.guess_view = self.build_guess_view()
        self.start_datetime = datetime.now()
        self.guess_deadline = timer.compute_deadline(
            self.start_datetime, self.time_to_guess)
        self.potential_guessers = members.get_potential_guessers(
            self.slack_client, self.channel_id, self.organizer_id)
        self.stage = 'guess_stage'
        self.update_board('all')

    def post_board(self, part):
        return self.slack_client.api_call(
            'chat.postMessage',
            channel=self.channel_id,
            blocks=getattr(self, part + '_board'))['ts']

    def update_board(self, part):
        if part == 'all':
            self.update_board('upper')
            self.update_board('lower')
            return
        self.slack_client.api_call(
            'chat.update',
            channel=self.channel_id,
            ts=getattr(self, part + '_ts'),
            blocks=getattr(self, part + '_board'))






