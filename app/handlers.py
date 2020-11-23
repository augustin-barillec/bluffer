import app.utils as ut
from flask import make_response


def handle_setup_submission(game, game_setup_view, logger):
    question, truth, time_to_guess = ut.views.collect_game_setup(
        game_setup_view)
    game.setup_submission = ut.time.get_now()
    game.question = question
    game.truth = truth
    game.time_to_guess = time_to_guess
    game.max_life_span = ut.time.build_max_life_span(
        game.time_to_guess, game.time_to_vote)

    game_dicts = game.firestore_reader.get_game_dicts()
    exception_msg = ut.exceptions.Exceptions(game). \
        build_setup_view_exception_msg(game_dicts)
    if exception_msg:
        return ut.views.build_exception_view_response(exception_msg)

    game.dict = {
        'version': game.version,
        'setup_submission': game.setup_submission,
        'question': game.question,
        'truth': game.truth,
        'time_to_guess': game.time_to_guess,
        'max_life_span': game.max_life_span}
    ut.firestore.FirestoreEditor(game).set_game_dict()
    game.stage_triggerer.trigger_pre_guess_stage()
    logger.info('pre_guess_stage triggered, game_id={}'.format(
        game.id))
    return make_response('', 200)


def handle_guess_submission(user_id, game, guess_view, exceptions, logger):
    guess = ut.views.collect_guess(guess_view)
    exception_msg = exceptions.build_guess_view_exception_msg(guess)
    if exception_msg:
        return ut.views.build_exception_view_response(exception_msg)
    guess_ts = ut.time.get_now()
    game.dict['guessers'][user_id] = [guess_ts, guess]
    ut.firestore.FirestoreEditor(game).set_game_dict(merge=True)
    ut.slack.SlackOperator(game).update_guess_stage_lower()
    logger.info('guess recorded, guesser_id={}, game_id={}'.format(
        game.id, user_id))
    return make_response('', 200)


def handle_vote_submission(user_id, game, vote_view, exceptions, logger):
    vote = ut.views.collect_vote(vote_view)
    exception_msg = exceptions.build_vote_view_exception_msg(vote)
    if exception_msg:
        return ut.views.build_exception_view_response(exception_msg)
    vote_ts = ut.time.get_now()
    game.dict['voters'][user_id] = [vote_ts, vote]
    ut.firestore.FirestoreEditor(game).set_game_dict(merge=True)
    ut.slack.SlackOperator(game).update_guess_stage_lower()
    logger.info('vote recorded, voter_id={}, game_id={} '.format(
        game.id, user_id))
    return make_response('', 200)


def handle_guess_click(
        user_id, trigger_id, game, slack_operator, exceptions, logger):
    exception_msg = exceptions.build_guess_button_exception_msg(
        user_id)
    if exception_msg:
        slack_operator.open_exception_view(trigger_id, exception_msg)
        return make_response('', 200)
    slack_operator.open_guess_view(trigger_id)
    logger.info('guess_view opened, user_id={}, game_id={}'.format(
        game.id, user_id))
    return make_response('', 200)


def handle_vote_click(
        user_id, trigger_id, game, slack_operator, exceptions, logger):
    exception_msg = exceptions.build_vote_button_exception_msg(user_id)
    if exception_msg:
        slack_operator.open_exception_view(trigger_id, exception_msg)
        return make_response('', 200)
    slack_operator.open_vote_view(trigger_id, user_id)
    logger.info('vote_view opened, user_id={}, game_id={}'.format(
        game.id, user_id))
    return make_response('', 200)


def handle_view_submission(
        user_id, message_action, build_game_func, secret_prefix, logger):
    view = message_action['view']
    view_callback_id = view['callback_id']
    if not view_callback_id.startswith(secret_prefix):
        return make_response('', 200)

    game_id = ut.ids.slack_object_id_to_game_id(view_callback_id)
    game = build_game_func(game_id)

    if view_callback_id.startswith(secret_prefix + '#game_setup_view'):
        return handle_setup_submission(game, view, logger)

    exceptions = ut.exceptions.Exceptions(game)
    exception_msg = exceptions.build_game_is_dead_msg()
    if exception_msg:
        return ut.views.build_exception_view_response(exception_msg)

    if view_callback_id.startswith(secret_prefix + '#guess_view'):
        return handle_guess_submission(user_id, game, view, exceptions, logger)

    if view_callback_id.startswith(secret_prefix + '#vote_view'):
        return handle_vote_submission(user_id, game, view, exceptions, logger)


def handle_button_click(
        user_id, message_action, build_game_func, secret_prefix, logger):
    trigger_id = message_action['trigger_id']
    action_block_id = message_action['actions'][0]['block_id']
    if not action_block_id.startswith(secret_prefix):
        return make_response('', 200)
    game_id = ut.ids.slack_object_id_to_game_id(action_block_id)
    game = build_game_func(game_id)
    exceptions = ut.exceptions.Exceptions(game)
    slack_operator = ut.slack.SlackOperator(game)

    exception_msg = exceptions.build_game_is_dead_msg()
    if exception_msg:
        return ut.views.build_exception_view_response(exception_msg)

    if action_block_id.startswith(secret_prefix + '#guess_button_block'):
        return handle_guess_click(
            user_id, trigger_id, game, slack_operator, exceptions, logger)

    if action_block_id.startswith(secret_prefix + '#vote_button_block'):
        return handle_vote_click(
            user_id, trigger_id, game, slack_operator, exceptions, logger)
