from flask import make_response
from app import utils as ut


def handle_submission(
        user_id, message_action, build_game_func, secret_prefix, logger):
    view = message_action['view']
    view_callback_id = view['callback_id']
    if not view_callback_id.startswith(secret_prefix):
        return make_response('', 200)

    game_id = ut.ids.slack_object_id_to_game_id(view_callback_id)
    game = build_game_func(game_id)

    if view_callback_id.startswith(secret_prefix + '#setup_view'):
        return handle_setup_submission(game, view, logger)

    eh = ut.exceptions.ExceptionsHandler(game)
    resp = eh.handle_is_dead_exception()
    if resp:
        return resp

    if view_callback_id.startswith(secret_prefix + '#guess_view'):
        return handle_guess_submission(user_id, game, view, eh, logger)

    if view_callback_id.startswith(secret_prefix + '#vote_view'):
        return handle_vote_submission(user_id, game, view, eh, logger)


def handle_click(
        user_id, message_action, build_game_func, secret_prefix, logger):
    trigger_id = message_action['trigger_id']
    action_block_id = message_action['actions'][0]['block_id']
    if not action_block_id.startswith(secret_prefix):
        return make_response('', 200)
    game_id = ut.ids.slack_object_id_to_game_id(action_block_id)
    game = build_game_func(game_id)
    slack_operator = ut.slack.SlackOperator(game)
    eh = ut.exceptions.ExceptionsHandler(game)
    resp = eh.handle_is_dead_exception(trigger_id)
    if resp:
        return resp

    if action_block_id.startswith(secret_prefix + '#guess_button_block'):
        return handle_guess_click(
            user_id, trigger_id, game, slack_operator, eh, logger)

    if action_block_id.startswith(secret_prefix + '#vote_button_block'):
        return handle_vote_click(
            user_id, trigger_id, game, slack_operator, eh, logger)


def handle_setup_submission(game, setup_view, logger):
    question, truth, time_to_guess = ut.views.collect_setup(
        setup_view)
    game.setup_submission = ut.time.get_now()
    game.question = question
    game.truth = truth
    game.time_to_guess = time_to_guess
    game.max_life_span = ut.time.build_max_life_span(
        game.time_to_guess, game.time_to_vote)
    resp = ut.exceptions.ExceptionsHandler(
        game).handle_setup_submission_exceptions()
    if resp:
        return resp

    game.dict = dict()
    for attribute in [
        'version',
        'setup_submission',
        'question',
        'truth',
        'time_to_guess',
        'max_life_span'
    ]:
        game.dict[attribute] = game.__dict__[attribute]
    ut.firestore.FirestoreEditor(game).set_game_dict()
    game.stage_triggerer.trigger_pre_guess_stage()
    logger.info('pre_guess_stage triggered, game_id={}'.format(game.id))
    return make_response('', 200)


def handle_guess_submission(
        user_id, game, guess_view, exceptions_handler, logger):
    guess = ut.views.collect_guess(guess_view)
    resp = exceptions_handler.handle_guess_submission_exceptions(guess)
    if resp:
        return resp
    guess_ts = ut.time.get_now()
    game.dict['guessers'][user_id] = [guess_ts, guess]
    ut.firestore.FirestoreEditor(game).set_game_dict(merge=True)
    ut.slack.SlackOperator(game).update_guess_stage_lower()
    logger.info('guess recorded, guesser_id={}, game_id={}'.format(
        user_id, game.id))
    return make_response('', 200)


def handle_vote_submission(
        user_id, game, vote_view, exceptions_handler, logger):
    vote = ut.views.collect_vote(vote_view)
    resp = exceptions_handler.handle_vote_submission_exceptions(vote)
    if resp:
        return resp
    vote_ts = ut.time.get_now()
    game.dict['voters'][user_id] = [vote_ts, vote]
    ut.firestore.FirestoreEditor(game).set_game_dict(merge=True)
    ut.slack.SlackOperator(game).update_guess_stage_lower()
    logger.info('vote recorded, voter_id={}, game_id={} '.format(
        user_id, game.id))
    return make_response('', 200)


def handle_guess_click(
        user_id, trigger_id, game, slack_operator, exceptions_handler, logger):
    resp = exceptions_handler.handle_guess_click_exceptions(
        user_id, trigger_id)
    if resp:
        return resp
    slack_operator.open_guess_view(trigger_id)
    logger.info('guess_view opened, user_id={}, game_id={}'.format(
        user_id, game.id))
    return make_response('', 200)


def handle_vote_click(
        user_id, trigger_id, game, slack_operator, exceptions_handler, logger):
    resp = exceptions_handler.handle_vote_click_exceptions(user_id, trigger_id)
    if resp:
        return resp
    slack_operator.open_vote_view(trigger_id, user_id)
    logger.info('vote_view opened, user_id={}, game_id={}'.format(
        user_id, game.id))
    return make_response('', 200)
