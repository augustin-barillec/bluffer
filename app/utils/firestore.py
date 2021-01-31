def get_teams_ref(db):
    return db.collection('teams')


def get_team_ref(db, team_id):
    teams_ref = get_teams_ref(db)
    return teams_ref.document(team_id)


def get_team_dict(db, team_id):
    team_ref = get_team_ref(db, team_id)
    return team_ref.get().to_dict()


def get_items_ref(db, team_id, kind):
    assert kind in ('games', 'channels')
    team_ref = get_team_ref(db, team_id)
    return team_ref.collection(kind)


def get_item_ref(db, team_id, kind, item_id):
    items_ref = get_items_ref(db, team_id, kind)
    return items_ref.document(item_id)


def get_item_dict(db, team_id, kind, item_id):
    item_ref = get_item_ref(db, team_id, kind, item_id)
    return item_ref.get().to_dict()


def get_item_dicts(db, team_id, kind):
    items_ref = get_items_ref(db, team_id, kind)
    return {item.id: item.to_dict() for item in items_ref.stream()}


def get_channels_ref(db, team_id):
    return get_items_ref(db, team_id, 'channels')


def get_games_ref(db, team_id):
    return get_items_ref(db, team_id, 'games')


def get_channel_ref(db, team_id, channel_id):
    return get_item_ref(db, team_id, 'channels', channel_id)


def get_game_ref(db, team_id, game_id):
    return get_item_ref(db, team_id, 'games', game_id)


def get_channel_dict(db, team_id, channel_id):
    return get_item_dict(db, team_id, 'channels', channel_id)


def get_game_dict(db, team_id, game_id):
    return get_item_dict(db, team_id, 'games', game_id)


def get_channel_dicts(db, team_id):
    return get_item_dicts(db, team_id, 'channels')


def get_game_dicts(db, team_id):
    return get_item_dicts(db, team_id, 'games')


def set_game_dict(db, team_id, game_id, data, merge):
    game_ref = get_game_ref(db, team_id, game_id)
    game_ref.set(data, merge=merge)


class FirestoreReader:
    def __init__(self, db, team_id, channel_id, game_id):
        self.db = db
        self.team_id = team_id
        self.channel_id = channel_id
        self.game_id = game_id

    def get_team_dict(self):
        return get_team_dict(self.db, self.team_id)

    def get_channel_dict(self):
        return get_channel_dict(self.db, self.team_id, self.channel_id)

    def get_game_dict(self):
        return get_game_dict(self.db, self.team_id, self.game_id)

    def get_channel_dicts(self):
        return get_channel_dicts(self.db, self.team_id)

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
