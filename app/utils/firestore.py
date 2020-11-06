def get_teams_ref(db):
    return db.collection('teams')


def get_team_ref(db, team_id):
    teams_ref = get_teams_ref(db)
    return teams_ref.document(team_id)


def get_games_ref(db, team_id):
    team_ref = get_team_ref(db, team_id)
    return team_ref.collection('games')


def get_game_ref(db, team_id, game_id):
    games_ref = get_games_ref(db, team_id)
    return games_ref.document(game_id)


def get_team_dict(db, team_id):
    team_ref = get_team_ref(db, team_id)
    return team_ref.get().to_dict()


def get_game_dict(db, team_id, game_id):
    game_ref = get_game_ref(db, team_id, game_id)
    return game_ref.get().to_dict()


def delete_game(db, team_id, game_id):
    get_game_ref(db, team_id, game_id).delete()
