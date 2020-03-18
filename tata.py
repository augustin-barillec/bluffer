from bluffer.utils import *


def game_db_to_game_dict(team_id, game_id):
    return None


def game_dict_to_game_instance(game_dict):
    return None


def game_instance_to_game_dict(game_instance):
    return None


def game_dict_to_game_db(game_dict):
    return None

def slack_command(request):
    open_guess_set_up_view()

def pre_guess_stage(request):
    game_id = context['game_id']
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_token = team_id_to_slack_token(team_id)
    slack_client = SlackClient(token=token)

    game_dict = game_id_to_game_dict(game_id)

    title_block = blocks.build_title_block(organizer_id)
    pre_guess_stage_block = blocks.build_pre_guess_stage_block()

    upper_blocks = [title_block]
    middle_blocks = [pre_guess_stage_block]
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

    question_block = blocks.build_text_block(game_dict['question'])

    msg = 'Your guess'
    id_ = ids.build_slack_object_id(secret_prefix, object_name, game_id)
    guess_button_block = blocks.build_button_block(msg, id_)

    start_guess_datetime = datetime.now()
    time_left_block = compute()

    update_upper(title_block, question_block, guess_button_block)
    update_lower(guess_timer_block, guesser_block)

    trigger(guess_stage, game_id)

    return


def guess_stage(request):

    start_process_datetime = datetime.now()


    game_id = context['game_id']
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_token = team_id_to_slack_token(team_id)
    slack_client = SlackClient(token=token)

    game_dict = game_id_to_game_dict(game_id)

    potential_players = game_dict['potential_players']
    remaining_potential_guessers = copy(potential_players)


    while True:
        if (datetime.now() - start_guess_datetime) > game_dict['time_to_left'] or len(remaining_potential_players) == 0:

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
      guessers_block = build_guessers_block()

      slack_client.api_call(
          'chat.update',
          channel=channel_id,
          ts=game_dict['lower_ts'],
          blocks=[time_left_to_guess_block, guessers_block])
      time.sleep(2)


def preparing_vote_stage(request):
    game_id = context['game_id']
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_token = team_id_to_slack_token(team_id)
    slack_client = SlackClient(token=token)

    game_dict = game_id_to_game_dict(game_id)

    if len(guessers) > 1:
        self.send_vote_reminders()

    signed_proposals = build_signed_proposals(game_dict)
    anonymous_proposals_block = build_anonymous_proposals_block()
    vote_button_block

    potential_voters = get_potential_voters()
    voters = ()

    time_left_to_vote_block = compute()

    update_upper(title_block, question_block, vote_button_block)
    update_lower(potential_voters_block, voters_block, time_left_to_vote_block)

    if len(self.guessers) > 1:
        self.send_vote_reminders()

    trigger_vote_stage




def vote_stage(request):
    start_process_datetime = datetime.now()

    game_id = context['game_id']
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_token = team_id_to_slack_token(team_id)
    slack_client = SlackClient(token=token)

    game_dict = game_id_to_game_dict(game_id)

    potential_players = game_dict['potential_players']
    remaining_potential_voters = compute


    while True:
        if (datetime.now() - start_guess_datetime) > game_dict['time_to_left_to_vote'] or len(remaining_potential_players) == 0:

            post preparing result message

            trigger(next, game_id)
            return

        if (datetime.now() - start_process_datetime) > 60:
            trigger(vote_stage, game_id)
            return


      game_dict = game_id_to_game_dict(game_id)

      time_left_to_vote_block = compute()
      remaining_potential_voters_blocks = (sorted by guess_timestamp)(game_dict)
      voter_blocks = (sorted_by guess_timestamp)(game_dict)

      time_left_to_guess_block = blocks.build_text_block((datetime.now() - start_guess_datetime))
      guessers_block = build_guessers_block()

      slack_client.api_call(
          'chat.update',
          channel=channel_id,
          ts=game_dict['lower_ts'],
          blocks=[time_left_to_guess_block, remaining_potential_voters_blocks, voters_block])
      time.sleep(2)

def results_stage(request):

    game_id = context['game_id']
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    truth_block = compute()
    signed_guesses_block = compute()
    graph_block = compute()
    conclusion_block = compute()

    update_upper(
        title_block,
        question_block,
        signed_guesses_block,
        graph_block,
        conclusion_block
    )
    update_lower(divider_block)
    delete_in_db
    self.send_game_over_notifications()

def guess_button_
