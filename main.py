import os
import pytz
import json
import yaml
import logging
from time import sleep
import google.cloud.pubsub_v1
import google.cloud.firestore
import google.cloud.storage
from copy import deepcopy
from datetime import datetime
from flask import make_response
from app.game import Game
from app.utils import firestore, ids, pubsub, time, views, users, proposals, \
    results, graph, slack, exceptions

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level='INFO')
logger = logging.getLogger()

dir_path = os.path.realpath(os.path.dirname(__file__))
with open(os.path.join(dir_path, 'conf.yaml')) as f:
    conf = yaml.safe_load(f)
secret_prefix = conf['secret_prefix']
project_id = conf['project_id']
bucket_name = conf['bucket_name']
local_dir_path = conf['local_dir_path']
publisher = google.cloud.pubsub_v1.PublisherClient()
db = google.cloud.firestore.Client(project=project_id)
storage_client = google.cloud.storage.Client(project=project_id)
bucket = storage_client.bucket(bucket_name)


def build_game(game_id):
    return Game(
        game_id=game_id,
        secret_prefix=secret_prefix,
        project_id=project_id,
        publisher=publisher,
        db=db,
        bucket=bucket,
        logger=logger,
        local_dir_path=local_dir_path)


def slash_command(request):
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    slash_command_compact = time.datetime_to_compact(
        time.get_now())
    game_id = ids.build_game_id(
        slash_command_compact, team_id, channel_id, organizer_id, trigger_id)
    logger.info('game_id built, game_id={}'.format(game_id))
    game = build_game(game_id)

    game_dicts = game.firestore_reader.get_game_dicts()
    app_conversations = game.firestore_reader.get_app_conversations()
    exception_msg = exceptions.build_slash_command_exception_msg(
        game, game_dicts, app_conversations)
    if exception_msg:
        game.slack_operator.open_exception_view(trigger_id, exception_msg)
        return make_response('', 200)

    game.slack_operator.open_setup_view(trigger_id)
    logger.info('setup_view opened, game_id={}'.format(game_id))
    return make_response('', 200)


def message_actions(request):
    message_action = json.loads(request.form['payload'])
    message_action_type = message_action['type']
    user_id = message_action['user']['id']
    if message_action_type not in ('block_actions', 'view_submission'):
        return make_response('', 200)

    if message_action_type == 'view_submission':
        view = message_action['view']
        view_callback_id = view['callback_id']
        if not view_callback_id.startswith(secret_prefix):
            return make_response('', 200)
        game_id = ids.slack_object_id_to_game_id(view_callback_id)
        game = build_game(game_id)

        if view_callback_id.startswith(secret_prefix + '#game_setup_view'):
            question, truth, time_to_guess = views.collect_game_setup(
                view)
            game.setup_submission = time.get_now()
            game.question = question
            game.truth = truth
            game.time_to_guess = time_to_guess
            game.max_life_span = time.build_max_life_span(
                game.time_to_guess, game.time_to_vote)

            game_dicts = game.firestore_reader.get_game_dicts()
            exception_msg = exceptions.build_setup_view_exception_msg(
                game, game_dicts)
            if exception_msg:
                return views.build_exception_view_response(exception_msg)

            game.dict = {
                'version': game.version,
                'setup_submission': game.setup_submission,
                'question': game.question,
                'truth': game.truth,
                'time_to_guess': game.time_to_guess,
                'max_life_span': game.max_life_span}
            game.firestore_editor.set_dict()
            game.stage_triggerer.trigger_pre_guess_stage()
            logger.info('pre_guess_stage triggered, game_id={}'.format(
                game_id))
            return make_response('', 200)

        exception_msg = exceptions.build_game_is_dead_msg(game)
        if exception_msg:
            return views.build_exception_view_response(exception_msg)

        if view_callback_id.startswith(secret_prefix + '#guess_view'):
            guess = views.collect_guess(view)
            exception_msg = exceptions.build_guess_view_exception_msg(
                guess, game)
            if exception_msg:
                return views.build_exception_view_response(exception_msg)
            guess_start = time.get_now()
            game.dict['guessers'][user_id] = [guess_start, guess]
            game.firestore_editor.set_dict(merge=True)
            slack.update_guess_stage_lower(game)
            logger.info('guess recorded, guesser_id={}, game_id={}'.format(
                game_id, user_id))
            return make_response('', 200)

        if view_callback_id.startswith(secret_prefix + '#vote_view'):
            vote = views.collect_vote(view)
            exception_msg = exceptions.build_vote_view_exception_msg(
                vote, game)
            if exception_msg:
                return views.build_exception_view_response(exception_msg)
            vote_start = time.get_now()
            game.dict['voters'][user_id] = [vote_start, vote]
            game.firestore_editor.set_dict(merge=True)
            slack.update_guess_stage_lower(game)
            logger.info('vote recorded, voter_id={}, game_id={} '.format(
                game_id, user_id))
            return make_response('', 200)

    if message_action_type == 'block_actions':
        trigger_id = message_action['trigger_id']
        action_block_id = message_action['actions'][0]['block_id']
        if not action_block_id.startswith(secret_prefix):
            return make_response('', 200)
        game_id = ids.slack_object_id_to_game_id(action_block_id)
        game = build_game(game_id)

        exception_msg = exceptions.build_game_is_dead_msg(game)
        if exception_msg:
            return views.build_exception_view_response(exception_msg)

        if action_block_id.startswith(secret_prefix + '#guess_button_block'):
            exception_msg = exceptions.build_guess_button_exception_msg(
                user_id, game)
            if exception_msg:
                game.slack_operator.open_exception_view(
                    trigger_id, exception_msg)
                return make_response('', 200)
            game.slack_operator.open_guess_view(trigger_id)
            logger.info('guess_view opened, user_id={}, game_id={}'.format(
                game_id, user_id))
            return make_response('', 200)

        if action_block_id.startswith(secret_prefix + '#vote_button_block'):
            exception_msg = exceptions.build_vote_button_exception_msg(
                user_id, game)
            if exception_msg:
                game.slack_operator.open_exception_view(
                    trigger_id, exception_msg)
                return make_response('', 200)
            game.slack_operator.open_vote_view(trigger_id, user_id)
            logger.info('vote_view opened, user_id={}, game_id={}'.format(
                game_id, user_id))
            return make_response('', 200)


def pre_guess_stage(event, context):
    assert context == context
    game_id = pubsub.event_data_to_game_id(event['data'])
    game = build_game(game_id)

    if exceptions.game_is_dead(game):
        return make_response('', 200)
    if game.pre_guess_stage_already_triggered:
        logger.info(exceptions.build_aborted_cause_already_triggered_msg(game))
        return make_response('', 200)
    else:
        game.dict['pre_guess_stage_already_triggered'] = True
        game.firestore_editor.set_dict(merge=True)

    game.upper_ts, game.lower_ts = game.slack_operator.post_pre_guess_stage()
    game.potential_guessers = game.slack_operator.get_potential_guessers()
    game.guessers = dict()
    game.guess_start = time.get_now()
    game.guess_deadline = time.compute_deadline(
        game.guess_start, game.time_to_guess)

    game.dict['upper_ts'] = game.upper_ts
    game.dict['lower_ts'] = game.potential_guessers
    game.dict['potential_guessers'] = game.potential_guessers
    game.dict['guessers'] = game.guessers
    game.dict['guess_start'] = game.guess_start
    game.dict['guess_deadline'] = game.guess_deadline
    for attribute in [
        'upper_ts',
        'lower_ts',
        'potential_guessers',
        'guessers',
        'guess_start',
        'guess_deadline'
    ]:
        game.dict[attribute] = game.__dict__[attribute]
    game.firestore_editor.set_dict(merge=True)

    slack.update_guess_stage(game)
    game.slack_operator.trigger_guess_stage()
    logger.info('guess_stage triggered, game_id={}'.format(game_id))
    return make_response('', 200)


def guess_stage(event, context):
    assert context == context
    call_datetime = datetime.now(pytz.UTC)
    game_id = pubsub.event_data_to_game_id(event['data'])
    game = build_game(game_id)

    if exceptions.game_is_dead(game):
        return make_response('', 200)
    if game.guess_stage_over:
        return make_response('', 200)
    if exceptions.guess_stage_was_recently_trigger(game):
        logger.info(exceptions.build_aborted_cause_recently_triggered_msg(
            game))
        return make_response('', 200)
    game.dict['guess_stage_last_trigger'] = time.get_now()
    game.firestore_editor.set_dict(merge=True)

    while True:
        game = build_game(game_id)
        slack.update_guess_stage_lower(game)
        if game.time_left_to_guess <= 0 \
                or not game.remaining_potential_guessers:
            game.dict['frozen_guessers'] = deepcopy(game.dict['guessers'])
            game.dict['guess_stage_over'] = True
            game.firestore_editor.set_dict(merge=True)
            game.stage_triggerer.trigger_pre_vote_stage()
            logger.info('pre_vote_stage triggered, game_id={}'.format(
                game_id))
            return make_response('', 200)
        if time.datetime1_minus_datetime2(
                time.get_now(), call_datetime) > 60:
            game.stage_triggerer.trigger_guess_stage()
            logger.info('guess_stage self-triggered, game_id={}'.format(
                game_id))
            return make_response('', 200)
        sleep(5)


def pre_vote_stage(event, context):
    assert context == context
    game_id = pubsub.event_data_to_game_id(event['data'])
    game = build_game(game_id)

    if exceptions.build_game_is_dead_msg(game):
        return make_response('', 200)
    if game.pre_vote_stage_already_triggered:
        logger.info(exceptions.build_aborted_cause_already_triggered_msg(game))
        return make_response('', 200)
    else:
        game.dict['pre_vote_stage_already_triggered'] = True
        game.firestore_editor.set_dict(merge=True)

    game.stage_triggerer.update_pre_vote_stage()

    game.indexed_signed_proposals = \
        proposals.build_indexed_signed_proposals(
            game.frozen_guessers, game.truth, game.id)
    proposals_browser = proposals.ProposalsBrowser(
        game.indexed_signed_proposals)
    game.truth_index = proposals_browser.compute_truth_index()
    game.potential_voters = game.frozen_guessers
    game.voters = dict()
    game.vote_start = time.get_now()
    game.vote_deadline = time.compute_deadline(
        game.vote_start, game.time_to_vote)
    for attribute in [
        'indexed_signed_proposals',
        'truth_index',
        'potential_voters',
        'voters',
        'vote_start',
        'vote_deadline'
    ]:
        game.dict[attribute] = game.__dict__[attribute]
    game.firestore_editor.set_dict(merge=True)

    slack.update_vote_stage(game)
    slack.send_vote_reminders(game)
    game.stage_triggerer.trigger_vote_stage()
    logger.info('vote_stage triggered, game_id={}'.format(game_id))
    return make_response('', 200)


def vote_stage(event, context):
    assert context == context
    call_datetime = datetime.now(pytz.UTC)
    game_id = pubsub.event_data_to_game_id(event['data'])
    game = build_game(game_id)

    if exceptions.game_is_dead(game):
        return make_response('', 200)
    if game.vote_stage_over:
        return make_response('', 200)
    if exceptions.vote_stage_was_recently_trigger(game):
        logger.info(exceptions.build_aborted_cause_recently_triggered_msg(
            game))
        return make_response('', 200)
    game.dict['vote_stage_last_trigger'] = time.get_now()
    game.firestore_editor.set_dict(merge=True)

    while True:
        game = build_game(game_id)
        slack.update_vote_stage_lower(game)
        if game.time_left_to_vote <= 0 or \
                not game.remaining_potential_voters:
            game.dict['frozen_voters'] = deepcopy(game.dict['voters'])
            game.dict['vote_stage_over'] = True
            game.firestore_editor.set_dict(merge=True)
            game.stage_triggerer.trigger_pre_result_stage()
            logger.info('pre_result_stage triggered, game_id={}'.format(
                game_id))
            return make_response('', 200)
        if time.datetime1_minus_datetime2(
                datetime.now(pytz.UTC),
                call_datetime) > 60:
            game.stage_triggerer.trigger_vote_stage()
            logger.info('vote_stage self-triggered, game_id={}'.format(
                game_id))
            return make_response('', 200)
        sleep(5)


def pre_result_stage(event, context):
    assert context == context
    game_id = pubsub.event_data_to_game_id(event['data'])
    game = build_game(game_id)

    if exceptions.build_game_is_dead_msg(game):
        return make_response('', 200)
    if game.pre_result_stage_already_triggered:
        logger.info(exceptions.build_aborted_cause_already_triggered_msg(game))
        return make_response('', 200)
    else:
        game.dict['pre_result_stage_already_triggered'] = True
        game.firestore_editor.set_dict(merge=True)

    game.slack_operator.update_pre_result_stage()

    game.results = game.results_builder.build_results()
    game.max_score = results.compute_max_score(game)
    game.winners = results.compute_winners(game)
    game.graph = graph.build_graph(game)
    graph.draw_graph(game)
    game.graph_url = graph.upload_graph_to_gs(game)
    for attribute in ['results', 'max_score', 'winners', 'graph_url']:
        game.dict[attribute] = game.__dict__[attribute]
    game.firestore_editor.set_dict(merge=True)

    slack.update_result_stage(game)
    slack.send_is_over_notifications(game)
    game.stage_triggerer.trigger_result_stage()
    logger.info('result_stage triggered, game_id={}'.format(game_id))
    return make_response('', 200)


def result_stage(event, context):
    assert context == context
    game_id = pubsub.event_data_to_game_id(event['data'])
    game = build_game(game_id)

    if exceptions.game_is_dead(game):
        return make_response('', 200)
    if game.result_stage_over:
        return make_response('', 200)

    game.dict['result_stage_over'] = True
    game.firestore_editor.set_game_dict(merge=True)

    if game.post_clean:
        game.firestore_editor.delete_game()
    logger.info('sucessfully ended, game_id={}'.format(game_id))
    return make_response('', 200)


def erase(event, context):
    assert event == event and context == context
    teams_ref = firestore.get_teams_ref(db)
    for t in teams_ref.stream():
        games_ref = firestore.get_games_ref(db, t.id)
        for g in games_ref.stream():
            game = build_game(g.id)
            if exceptions.game_is_dead(game):
                game.firestore_editor.delete_game()
                logger.info('game deleted, game_id={}'.format(g.id))
