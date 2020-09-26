from slackclient import SlackClient


def team_id_to_team_ref(db, team_id):
    return db.collection('teams').document(team_id)


def get_game_ref(db, team_id, game_id):
    team_ref = team_id_to_team_ref(db, team_id)
    return team_ref.collection('games').document(game_id)


def get_game_dict(db, team_id, game_id):
    return get_game_ref(db, team_id, game_id).get().to_dict()


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