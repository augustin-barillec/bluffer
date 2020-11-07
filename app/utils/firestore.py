from app.utils.ids import game_id_to_organizer_id


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


def get_game_dicts(db, team_id):
    games_ref = get_games_ref(db, team_id)
    return {g.id: g.to_dict() for g in games_ref.stream()}


def count_running_games(game_dicts):
    return len([g for g in game_dicts if 'result_stage_over' not in g])


def get_running_organizer_ids(game_dicts):
    return [game_id_to_organizer_id(gid) for gid in game_dicts
            if 'result_stage_over' not in game_dicts[gid]]

