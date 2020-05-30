import os
import base64
import time
import json
from flask import Flask, Response, make_response
from google.cloud import pubsub_v1
from slackclient import SlackClient
from datetime import datetime
from bluffer.utils import *
from google.cloud import firestore

db = firestore.Client()
publisher = pubsub_v1.PublisherClient()

SECRET_PREFIX = 'secret_prefix'

dir_path = os.path.realpath(os.path.dirname(__file__))
with open(os.path.join(dir_path, 'project_id.txt')) as f:
    project_id = list(f)[0]


def team_id_to_team_ref(db, team_id):
    return db.collection('teams').document(team_id)


def build_game_ref(db, team_id, game_id):
    team_ref = team_id_to_team_ref(db, team_id)
    return team_ref.collection('games').document(game_id)


def get_game(db, team_id, game_id):
    return build_game_ref(db, team_id, game_id).get().to_dict()


def team_id_to_team_dict(db, team_id):
    team_ref = team_id_to_team_ref(db, team_id)
    return team_ref.get().to_dict()


def team_id_to_slack_token(db, team_id):
    return team_id_to_team_dict(db, team_id)['token']


def team_id_to_debug(db, team_id):
    return team_id_to_team_dict(db, team_id)['debug']


def team_id_to_games(db, team_id):
    team_ref = team_id_to_team_ref(db, team_id)
    games_stream = team_ref.collection('games').stream()
    games = {g.id: g.to_dict() for g in games_stream}
    return games


def team_id_to_slack_client(db, team_id):
    token = team_id_to_slack_token(db, team_id)
    return SlackClient(token=token)


def slack_command(request):
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    slack_client = team_id_to_slack_client(db, team_id)

    game_id = ids.build_game_id(team_id, channel_id, organizer_id, trigger_id)
    views.open_game_setup_view(
        slack_client,
        trigger_id,
        SECRET_PREFIX,
        game_id)

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
        team_id = ids.game_id_to_team_id(game_id)

        game_ref = build_game_ref(db, team_id, game_id)
        debug = team_id_to_debug(db, team_id)

        if view_callback_id.startswith(SECRET_PREFIX + '#game_setup_view'):
            question, truth, time_to_guess = \
                views.collect_game_setup(view)

            if not debug[0]:
                time_to_vote = 600
            else:
                time_to_guess = debug[1]
                time_to_vote = debug[2]

            game = {
                'question': question,
                'truth': truth,
                'time_to_guess': time_to_guess,
                'time_to_vote': time_to_vote,
            }

            game_ref.set(game)

            topic_path = publisher.topic_path(
                project_id, 'pre_guess_stage_topic')

            data = game_id.encode("utf-8")

            publisher.publish(topic_path, data=data)

            return make_response('', 200)


def pre_guess_stage(event, context):

    game_id = base64.b64decode(event['data']).decode('utf-8')
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

    potential_players = members.get_potential_guessers(
        slack_client, channel_id, organizer_id)

    game_dict['potential_players'] = potential_players

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

    topic_path = publisher.topic_path(project_id, 'guess_stage_topic')

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
        c1 = time_elapsed > time_to_guess

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
                'pre_vote_stage_topic')

            data = game_id.encode("utf-8")

            publisher.publish(topic_path, data=data)
            return make_response('', 200)

        if int((datetime.now() - start_call_datetime).total_seconds()) > 60:

            topic_path = publisher.topic_path(project_id, 'guess_stage_topic')

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
    guessers = game_dict['guessers']

    print(guessers)
    return make_response('', 200)


def vote_stage(event, context):
    return make_response('', 200)


def result_stage(event, context):
    return make_response('', 200)
