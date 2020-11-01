def team_id_to_team_ref(db, team_id):
    return db.collection('teams').document(team_id)


def get_game_ref(db, team_id, game_id):
    team_ref = team_id_to_team_ref(db, team_id)
    return team_ref.collection('games').document(game_id)


def team_id_to_team_dict(db, team_id):
    team_ref = team_id_to_team_ref(db, team_id)
    return team_ref.get().to_dict()


def get_game_dict(db, team_id, game_id):
    return get_game_ref(db, team_id, game_id).get().to_dict()


def delete_game(db, team_id, game_id):
    get_game_ref(db, team_id, game_id).delete()
