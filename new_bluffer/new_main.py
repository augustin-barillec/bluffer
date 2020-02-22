import firebase_admin
from flask import Flask, Response, request, make_response
from firebase_admin import firestore
from google.cloud import storage
from slackclient import SlackClient

app = Flask(__name__)

firebase_admin.initialize_app()
db = firestore.client()
storage_client = storage.Client()
bucket = storage_client.bucket('bucket_bluffer')


def team_id_to_team_ref(db, team_id):
    return db.collection('teams').document(team_id)


def team_id_to_slack_token(db, team_id):
    team_ref = team_id_to_team_ref(db, team_id)
    team = team_ref.get().to_dict()
    if team is None:
        raise ValueError('Team not found')
    return team['token']


def team_id_to_slack_client(db, team_id):
    token = team_id_to_team_ref(db, team_id)
    return SlackClient(token=token)


def team_id_to_games(db, team_id):
    team_ref = team_id_to_team_ref(db, team_id)
    games_stream = team_ref.collection('games').stream()
    games = [g.to_dict() for g in games_stream]
    return games


def has_running_game(organizer_id, games):
    for g in games:
        if organizer_id == g['organizer_id'] and g['stage'] != 'over':
            return True
    return False


@app.route('/slack/command', methods=['POST'])
def command():
    team_id = request.form['team_id']
    channel_id = request.form['channel_id']
    organizer_id = request.form['user_id']
    trigger_id = request.form['trigger_id']

    slack_client = team_id_to_slack_client(db, team_id)

    games = team_id_to_games(db, team_id)

    if len(games) >= 3:
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





@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
