import os
import time
import json
from bluffer.game import Game


from copy import deepcopy
from flask import Flask, Response, make_response
from google.cloud import pubsub_v1
from slackclient import SlackClient
from datetime import datetime
from utils import *
from google.cloud import firestore

db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

SECRET_PREFIX = 'secret_prefix'

dir_path = os.path.realpath(os.path.dirname(__file__))
with open(os.path.join(dir_path, 'project_id.txt')) as f:
    project_id = list(f)[0]


def build_game(game_id):
    return Game(game_id, SECRET_PREFIX, project_id, publisher, db)


def slack_command(request):
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    game_id = ids.build_game_id(team_id, channel_id, organizer_id, trigger_id)
    game = build_game(game_id)

    game.open_game_setup_view(trigger_id)

    return make_response('', 200)


def message_actions(request):
    message_action = json.loads(request.form['payload'])
    message_action_type = message_action['type']
    user_id = message_action['user']['id']
    trigger_id = message_action['trigger_id']

    if message_action_type == 'view_submission':
        view = message_action['view']
        view_callback_id = view['callback_id']

        game_id = ids.slack_object_id_to_game_id(view_callback_id)
        game = build_game(game_id)
        debug = game.get_debug()
        game_ref = game.get_game_ref()

        if view_callback_id.startswith(SECRET_PREFIX + '#game_setup_view'):
            question, truth, time_to_guess = views.collect_game_setup(view)

            if not debug[0]:
                time_to_vote = 600
            else:
                time_to_guess = debug[1]
                time_to_vote = debug[2]

            game_dict = {
                'question': question,
                'truth': truth,
                'time_to_guess': time_to_guess,
                'time_to_vote': time_to_vote,
            }

            game_ref.set(game_dict)

            game.publish('topic_pre_guess_stage')

            return make_response('', 200)

        game_dict = game.get_game_dict()
        if view_callback_id.startswith(SECRET_PREFIX + '#guess_view'):
            guess = views.collect_guess(view)
            game_dict['guessers'][user_id] = guess
            game_ref.set(game_dict, merge=True)
            return make_response('', 200)

    if message_action_type == 'block_actions':

        action_block_id = message_action['actions'][0]['block_id']
        game_id = ids.slack_object_id_to_game_id(action_block_id)
        game = build_game(game_id)

        if action_block_id.startswith(SECRET_PREFIX + '#guess_button_block'):
            game.open_guess_view(trigger_id)
            return make_response('', 200)

        if action_block_id.startswith(SECRET_PREFIX + '#vote_button_block'):
            return make_response('', 200)


def pre_guess_stage(event, context):

    game_id = pubsub.event_data_to_game_id(event['data'])



    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_client = team_id_to_slack_client(db, team_id)

    game_dict = get_game(db, team_id, game_id)

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
        blocks=lower_blocks)['ts']

    game_dict['upper_ts'] = upper_ts
    game_dict['lower_ts'] = lower_ts

    potential_guessers = members.get_potential_guessers(
        slack_client, channel_id, organizer_id)

    game_dict['potential_guessers'] = potential_guessers

    game_ref = build_game_ref(db, team_id, game_id)

    question_block = blocks.build_text_block(game_dict['question'])

    msg = 'Your guess'
    id_ = ids.build_slack_object_id(
        SECRET_PREFIX, 'guess_button_block', game_id)
    guess_button_block = blocks.build_button_block(msg, id_)

    start_guess_datetime = datetime.now()
    game_dict['start_guess_datetime'] = str(start_guess_datetime)

    game_dict['guessers'] = dict()

    game_ref.set(game_dict, merge=True)

    guess_timer_block = blocks.build_text_block(
        str(game_dict['time_to_guess']))

    guessers_block = blocks.build_text_block('Guessers are:')

    slack_client.api_call(
        'chat.update',
        channel=channel_id,
        ts=upper_ts,
        blocks=[title_block, question_block, guess_button_block])

    slack_client.api_call(
        'chat.update',
        channel=channel_id,
        ts=lower_ts,
        blocks=[guess_timer_block, guessers_block])

    topic_path = publisher.topic_path(project_id, 'topic_guess_stage')

    data = game_id.encode("utf-8")

    publisher.publish(topic_path, data=data)

    return make_response('', 200)


def guess_stage(event, context):

    start_call_datetime = datetime.now()

    game_id = base64.b64decode(event['data']).decode('utf-8')
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_client = team_id_to_slack_client(db, team_id)

    while True:
        game_dict = get_game(db, team_id, game_id)

        start_guess_datetime = datetime.fromisoformat(
            game_dict['start_guess_datetime'])
        time_to_guess = game_dict['time_to_guess']
        time_elapsed = datetime.now()-start_guess_datetime
        time_elapsed = int(time_elapsed.total_seconds())

        potential_guessers = game_dict['potential_guessers']
        guessers = game_dict['guessers']
        remaining_potential_guessers = set(potential_guessers) - set(guessers)

        if time_elapsed > time_to_guess or not remaining_potential_guessers:

            title_block = blocks.build_title_block(organizer_id)
            question_block = blocks.build_text_block(game_dict['question'])
            pre_vote_stage_block = blocks.build_pre_vote_stage_block()
            slack_client.api_call(
                'chat.update',
                channel=channel_id,
                ts=game_dict['upper_ts'],
                blocks=[
                    title_block,
                    question_block,
                    pre_vote_stage_block
                ])
            slack_client.api_call(
                'chat.update',
                channel=channel_id,
                ts=game_dict['lower_ts'],
                blocks=[blocks.divider_block])

            topic_path = publisher.topic_path(
                project_id,
                'topic_pre_vote_stage')

            data = game_id.encode("utf-8")

            publisher.publish(topic_path, data=data)
            return make_response('', 200)

        if int((datetime.now() - start_call_datetime).total_seconds()) > 60:

            topic_path = publisher.topic_path(project_id, 'topic_guess_stage')

            data = game_id.encode("utf-8")

            publisher.publish(topic_path, data=data)
            return make_response('', 200)

        time.sleep(5)


def pre_vote_stage(event, context):

    game_id = base64.b64decode(event['data']).decode('utf-8')
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_client = team_id_to_slack_client(db, team_id)

    game_dict = get_game(db, team_id, game_id)
    truth = game_dict['truth']
    guessers = game_dict['guessers']

    def build_signed_proposals(guessers_, truth_):
        import random
        res = list(guessers_.items()) + [('Truth', truth_)]
        random.shuffle(res)
        res = [(index, author, proposal) for index, (author, proposal) in
               enumerate(res, 1)]
        return res

    def build_anonymous_proposals_block(signed_proposals_):
        msg = ['Proposals:']
        for index, author, proposal in signed_proposals_:
            msg.append('{}) {}'.format(index, proposal))
        msg = '\n'.join(msg)
        return blocks.build_text_block(msg)

    start_vote_datetime = datetime.now()
    game_dict['start_vote_datetime'] = str(start_vote_datetime)
    game_ref = build_game_ref(db, team_id, game_id)
    game_ref.set(game_dict, merge=True)

    signed_proposals = build_signed_proposals(guessers, truth)
    anonymous_proposals_block = build_anonymous_proposals_block(
        signed_proposals)

    title_block = blocks.build_title_block(organizer_id)
    question_block = blocks.build_text_block(game_dict['question'])

    msg = 'Your vote'
    id_ = ids.build_slack_object_id(
        SECRET_PREFIX, 'vote_button_block', game_id)
    vote_button_block = blocks.build_button_block(msg, id_)

    slack_client.api_call(
        'chat.update',
        channel=channel_id,
        ts=game_dict['upper_ts'],
        blocks=[
            title_block,
            question_block,
            blocks.build_text_block('Preparing vote stage...'),
            anonymous_proposals_block,
            vote_button_block
        ])
    slack_client.api_call(
        'chat.update',
        channel=channel_id,
        ts=game_dict['lower_ts'],
        blocks=[blocks.divider_block])

    topic_path = publisher.topic_path(project_id, 'vote_stage')
    data = game_id.encode("utf-8")
    publisher.publish(topic_path, data=data)
    return make_response('', 200)


def vote_stage(event, context):

    game_id = base64.b64decode(event['data']).decode('utf-8')
    team_id = ids.game_id_to_team_id(game_id)
    organizer_id = ids.game_id_to_organizer_id(game_id)
    channel_id = ids.game_id_to_channel_id(game_id)

    slack_client = team_id_to_slack_client(db, team_id)

    game_dict = get_game(db, team_id, game_id)


    return make_response('', 200)


def result_stage(event, context):
    return make_response('', 200)
