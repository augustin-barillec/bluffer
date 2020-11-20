from app.version import VERSION
from app import utils


def count_running_games(game_dicts):
    return len([g for g in game_dicts if 'result_stage_over' not in g])


def get_running_organizer_ids(game_dicts):
    return [utils.ids.game_id_to_organizer_id(gid) for gid in game_dicts
            if 'result_stage_over' not in game_dicts[gid]]


def max_nb_of_running_games_reached(game, game_dicts):
    nb_of_running_games = count_running_games(game_dicts)
    return nb_of_running_games >= game.max_running_games


def organizer_has_another_game_running(game, game_dicts):
    running_organizer_ids = get_running_organizer_ids(game_dicts)
    return game.organizer_id in running_organizer_ids


def app_is_in_conversation(game, app_conversations):
    return game.channel_id in [c['id'] for c in app_conversations]


def no_time_left_to_guess(game):
    return game.time_left_to_guess <= 0


def max_nb_of_guessers_reached(game):
    return len(game.guessers) >= game.max_guessers


def no_time_left_to_vote(game):
    return game.time_left_to_vote <= 0


def game_is_too_old(game):
    now = utils.time.get_now()
    delta = utils.time.datetime1_minus_datetime2(now, game.setup_submission)
    return delta >= max_life_span


def version_is_bad(version):
    return version != VERSION


def game_is_dead(game):
    if not game.exists:
        return True
    if game.setup_submission is None:
        return True
    if game_is_too_old(game.setup_submission, game.max_life_span):
        return True
    if game.version is None:
        return True
    if version_is_bad(game.version):
        return True
    return False


def stage_was_recently_trigger(last_trigger):
    if last_trigger is None:
        return False
    now = utils.time.get_now()
    delta = utils.time.datetime1_minus_datetime2(now, last_trigger)
    return delta < 30


def guess_stage_was_recently_trigger(game):
    return stage_was_recently_trigger(game.guess_stage_last_trigger)


def vote_stage_was_recently_trigger(game):
    return stage_was_recently_trigger(game.vote_stage_last_trigger)


def build_organizer_has_another_game_running_msg():
    return ('You are the organizer of a game which is sill running. '
            'You can only have one game running at a time.')


def build_game_is_dead_msg(game):
    if game_is_dead(game):
        return 'This game is dead!'


def build_aborted_cause_recently_triggered_msg(game):
    return 'aborted cause recently triggered, game_id={}'.format(game.id)


def build_aborted_cause_already_triggered_msg(game):
    return 'aborted cause already triggered, game_id={}'.format(game.id)


def build_slash_command_exception_msg(game, game_dicts, app_conversations):
    if max_nb_of_running_games_reached(game.max_running_games, game_dicts):
        msg_template = ('There are already {} games running! '
                        'This is the maximal number allowed.')
        msg = msg_template.format(game.max_running_games)
        return msg
    if organizer_has_another_game_running(game.organizer_id, game_dicts):
        return build_organizer_has_another_game_running_msg()
    if not app_is_in_conversation(game.channel_id, app_conversations):
        return 'Please invite me first to this conversation!'


def build_setup_view_exception_msg(game, game_dicts):
    if max_nb_of_running_games_reached(game.max_running_games, game_dicts):
        msg = ('Question: {}\n\n'
               'Answer: {}\n\n'
               'There are already {} games running! '
               'This is the maximal number allowed.'.format(
                game.question, game.truth, game.max_running_games))
        return msg
    if organizer_has_another_game_running(game.organizer_id, game_dicts):
        return build_organizer_has_another_game_running_msg()


def build_guess_view_exception_msg(guess, game):
    if no_time_left_to_vote(game.guess_deadline):
        msg = ('Your guess: {}\n\n'
               'It will not be taken into account '
               'because the guessing deadline '
               'has passed!'.format(game.guess))
        return msg
    if max_nb_of_guessers_reached(game.guessers, game.max_guessers):
        msg_template = ('Your guess: {}\n\n'
                        'It will not be taken into account '
                        'because there are already {} guessers. '
                        'This is the maximal number allowed.')
        msg = msg_template.format(guess, game.max_guessers)
        return msg


def build_vote_view_exception_msg(vote, game):
    if no_time_left_to_vote(game.vote_deadline):
        msg = ('Your vote: proposal {}.\n\n'
               'It will not be taken into account '
               'because the voting deadline has passed!'.format(vote))
        return msg


def build_guess_button_exception_msg(user_id, game):
    if user_id == game.organizer_id:
        return 'As the organizer of this game, you cannot guess!'
    if user_id in game.guessers:
        return 'You have already guessed!'
    if user_id not in game.potential_guessers:
        msg = ('You cannot guess because when the set up of this '
               'game started, you were not a member of this channel.')
        return msg
    if max_nb_of_guessers_reached(game.guessers, game.max_guessers):
        msg_template = ('You cannot guess because there are already {} '
                        'guessers. This is the maximal number allowed.')
        msg = msg_template.format(game.max_guessers)
        return msg
    if user_id == 'Truth':
        msg = ("You cannot play bluffer because your slack user_id is "
               "'Truth', which is a reserved word for the game.")
        return msg


def build_vote_button_exception_msg(user_id, game):
    if user_id not in game.potential_voters:
        return 'Only guessers can vote!'
    if user_id in game.voters:
        return 'You have already voted!'
