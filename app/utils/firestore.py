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


def get_game_dicts(db, team_id):
    games_ref = get_games_ref(db, team_id)
    return {g.id: g.to_dict() for g in games_ref.stream()}


def set_game_dict(db, team_id, game_id, data, merge):
    game_ref = get_game_ref(db, team_id, game_id)
    game_ref.set(data, merge=merge)


def delete_game(db, team_id, game_id):
    game_ref = get_game_ref(db, team_id, game_id)
    game_ref.delete()


class FirestoreReader:
    def __init__(self, db, team_id, game_id):
        self.db = db
        self.team_id = team_id
        self.game_id = game_id

    def get_team_dict(self):
        return get_team_dict(self.db, self.team_id)

    def get_game_dict(self):
        return get_game_dict(self.db, self.team_id, self.game_id)

    def get_game_dicts(self):
        return get_game_dicts(self.db, self.team_id)

    def build_game_ref(self):
        return get_game_ref(self.db, self.team_id, self.game_id)


class FirestoreEditor:

    def __init__(self, game):
        self.game = game

    def set_game_dict(self, merge=False):
        set_game_dict(self.game.db, self.game.team_id,
                      self.game.id, self.game.dict, merge=merge)

    def delete_game(self):
        self.game.ref.delete()
