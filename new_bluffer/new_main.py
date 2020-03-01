import json
import firebase_admin
from flask import Flask, Response, request, make_response
from firebase_admin import firestore
from google.cloud import storage
from google.cloud import pubsub_v1
from slackclient import SlackClient
from bluffer.utils import *


app = Flask(__name__)

publisher = pubsub_v1.PublisherClient()
firebase_admin.initialize_app()
db = firestore.client()
storage_client = storage.Client()
bucket = storage_client.bucket('bucket_bluffer')

project_id = storage_client.project

# The `topic_path` method creates a fully qualified identifier
# in the form `projects/{project_id}/topics/{topic_name}`
topic_path = publisher.topic_path(project_id, 'bluffer_topic')

SECRET_PREFIX = 'secret_prefix'
LOCAL_DIR_PATH = '/tmp'


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


def team_id_to_slack_client(db, team_id):
    token = team_id_to_team_ref(db, team_id)
    return SlackClient(token=token)


def team_id_to_games(db, team_id):
    team_ref = team_id_to_team_ref(db, team_id)
    games_stream = team_ref.collection('games').stream()
    games = {g.id: g.to_dict() for g in games_stream}
    return games


def count_running_games(games):
    res = 0
    for game_id in games:
        if games[game_id]['stage'] != 'over':
            res += 1
    return res


def has_running_game(organizer_id, games):
    for game_id in games:
        g = games[game_id]
        if organizer_id == g['organizer_id'] and g['stage'] != 'over':
            return True
    return False


def get_players(db, team_id, game_id):
    team_ref = db.collection('teams').document(team_id)
    game_ref = team_ref.collection('games').document(game_id)
    players_stream = game_ref.collection('players').stream()
    players = {p.id: p.to_dict() for p in players_stream}
    return players


def get_guessers(players):
    return {}


def get_voters(players):
    return {}


def count_guessers(players):
    res = 0
    for player_id in players:
        if 'guess' in players[player_id]:
            res += 1
    return res


def set_guess(db, team_id, game_id, player_id, guess):
    team_ref = db.collection('teams').document(team_id)
    game_ref = team_ref.collection('games').document(game_id)
    player_ref = game_ref.collection('players').document(player_id)
    player_ref.set({'guess': guess})


def set_vote(db, team_id, game_id, player_id, vote):
    team_ref = db.collection('teams').document(team_id)
    game_ref = team_ref.collection('games').document(game_id)
    player_ref = game_ref.collection('players').document(player_id)
    player_ref.set({'vote': vote})


@app.route('/slack/command', methods=['POST'])
def command():
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    slack_client = team_id_to_slack_client(db, team_id)

    games = team_id_to_games(db, team_id)

    if count_running_games(games) >= 3:
        msg = ('There are already 3 games running! '
               'This is the maximal number allowed.')
        views.open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    if has_running_game(organizer_id, games):
        msg = ('You are the organizer of a game which is sill running. '
               'You can only have one game running at a time.')
        views.open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    app_conversations = slack_client.api_call(
        'users.conversations',
        types='public_channel, private_channel, mpim, im')['channels']
    if channel_id not in [c['id'] for c in app_conversations]:
        msg = 'Please invite me first to this conversation!'
        views.open_exception_view(slack_client, trigger_id, msg)
        return make_response('', 200)

    game_id = ids.build_game_id(team_id, channel_id, organizer_id, trigger_id)
    views.open_game_setup_view(slack_client, trigger_id,
                               SECRET_PREFIX, game_id)

    return make_response('', 200)


@app.route('/slack/message_actions', methods=['POST'])
def message_actions():
    message_action = json.loads(request.form['payload'])
    message_action_type = message_action['type']
    user_id = message_action['user']['id']
    trigger_id = message_action['trigger_id']

    if message_action_type not in ('block_actions', 'view_submission'):
        return make_response('', 200)

    if message_action_type == 'view_submission':
        view = message_action['view']
        view_callback_id = view['callback_id']

        if not view_callback_id.startswith(SECRET_PREFIX):
            return make_response('', 200)

        game_id = ids.slack_object_id_to_game_id(view_callback_id)
        team_id = ids.game_id_to_team_id(game_id)
        player_id = user_id

        game_ref = build_game_ref(db, team_id, game_id)

        bucket_dir_name = team_id

        slack_client = team_id_to_slack_client(db, team_id)
        debug = team_id_to_debug(db, team_id)
        games = team_id_to_games(db, team_id)

        if view_callback_id.startswith(SECRET_PREFIX + '#game_setup_view'):
            question, truth, time_to_guess = \
                views.collect_game_setup(view)

            if len(games) >= 3:
                msg = ('Question: {}\n\n'
                       'Answer: {}\n\n'
                       'Time to guess: {}s\n\n'
                       'There are already 3 games running! '
                       'This is the maximal number allowed.'.format(
                        question, truth, time_to_guess))
                exception_view_response = views.build_exception_view_response(
                    msg)
                return Response(json.dumps(exception_view_response),
                                mimetype='application/json',
                                status=200)
            if not debug[0]:
                time_to_vote = 600
            else:
                time_to_guess = debug[1]
                time_to_vote = debug[2]
                bucket_dir_name = 'test_' + bucket_dir_name

            game = {
                'question': question,
                'truth': truth,
                'time_to_guess': time_to_guess,
                'time_to_vote': time_to_vote,
                'bucket_dir_name': bucket_dir_name
            }

            game_ref.set(game)

            return make_response('', 200)

        game = get_game(db, team_id, game_id)
        if game is None:
            msg = 'This game is dead!'
            exception_view_response = views.build_exception_view_response(msg)
            return Response(json.dumps(exception_view_response),
                            mimetype='application/json',
                            status=200)

        if view_callback_id.startswith(SECRET_PREFIX + '#guess_view'):
            guess = views.collect_guess(view)
            if game['time_left_to_guess'] < 0:
                msg = ('Your guess: {}\n\n'
                       'It will not be taken into account '
                       'because the guessing deadline '
                       'has passed!'.format(guess))
                exception_view_response = (
                    views.build_exception_view_response(msg))
                return Response(json.dumps(exception_view_response),
                                mimetype='application/json',
                                status=200)
            players = get_players(db, team_id, game_id)
            if count_guessers(players) >= 80:
                msg = ('Your guess: {}\n\n'
                       'It will not be taken into account '
                       'because there are already 80 guessers. '
                       'This is the maximal number allowed.'.format(guess))
                exception_view_response = (
                    views.build_exception_view_response(msg))
                return Response(json.dumps(exception_view_response),
                                mimetype='application/json',
                                status=200)

            set_guess(db, team_id, game_id, player_id, guess)
            return make_response('', 200)

        if view_callback_id.startswith(SECRET_PREFIX + '#vote_view'):
            vote = views.collect_vote(view)
            if game['time_left_to_vote'] < 0:
                msg = ('Your vote: proposal {}.\n\n'
                       'It will not be taken into account '
                       'because the voting deadline has passed!'.format(vote))
                exception_view_response = (
                    views.build_exception_view_response(msg))
                return Response(json.dumps(exception_view_response),
                                mimetype='application/json',
                                status=200)
            set_vote(db, team_id, game_id, player_id, vote)
            return make_response('', 200)

    if message_action_type == 'block_actions':
        action_block_id = message_action['actions'][0]['block_id']

        if not action_block_id.startswith(SECRET_PREFIX):
            return make_response('', 200)

        game_id = ids.slack_object_id_to_game_id(action_block_id)
        team_id = ids.game_id_to_team_id(game_id)
        player_id = user_id

        slack_client = team_id_to_slack_client(db, team_id)

        game = get_game(db, team_id, game_id)
        players = get_players(db, team_id, game_id)
        guessers = get_guessers(players)
        voters = get_voters(players)
        potential_guessers = get_potential_guessers(db, team_id, game_id)

        if game is None:
            msg = 'This game is dead!'
            views.open_exception_view(slack_client, trigger_id, msg)
            return make_response('', 200)

        if action_block_id.startswith(SECRET_PREFIX + '#guess_button_block'):
            if player_id == game['organizer_id']:
                msg = 'As the organizer of this game, you cannot guess!'
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if player_id in guessers:
                msg = 'You have already guessed!'
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if player_id not in potential_guessers:
                msg = ('You cannot guess because when the set up of this '
                       'game started, you were not a member of this channel.')
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if len(guessers) >= 80:
                msg = ('You cannot guess because there are already 80 '
                       'guessers. This is the maximal number allowed.')
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if player_id == 'Truth':
                msg = ("You cannot play bluffer because your slack user_id is "
                       "'Truth', which is a reserved word for the game.")
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            open_guess_view(game, trigger_id)
            return make_response('', 200)

        if action_block_id.startswith(SECRET_PREFIX + '#vote_button_block'):
            if player_id not in guessers:
                msg = 'Only guessers can vote!'
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            if player_id in voters:
                msg = 'You have already voted!'
                views.open_exception_view(slack_client, trigger_id, msg)
                return make_response('', 200)
            open_vote_view(game, trigger_id, player_id)
            return make_response('', 200)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
