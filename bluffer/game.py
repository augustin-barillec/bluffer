from bluffer.utils import *


class Game:
    def __init__(
            self,
            game_id,
            secret_prefix,
            project_id,
            publisher,
            db
    ):
        self.id = game_id
        self.code = self.id.encode("utf-8")
        self.secret_prefix = secret_prefix
        self.project_id = project_id
        self.publisher = publisher
        self.db = db

        self.team_id = ids.game_id_to_team_id(self.id)
        self.organizer_id = ids.game_id_to_organizer_id(self.id)
        self.channel_id = ids.game_id_to_channel_id(self.id)

    def get_slack_client(self):
        return firestore.team_id_to_slack_client(self.db, self.team_id)

    def get_game_ref(self):
        return firestore.get_game_ref(self.db, self.team_id, self.id)

    def get_game_dict(self):
        return firestore.get_game_dict(self.db, self.team_id, self.id)

    def get_question(self):
        return self.get_game_dict()['question']

    def get_debug(self):
        return firestore.team_id_to_debug(self.db, self.team_id)

    def build_slack_object_id(self, object_name):
        return ids.build_slack_object_id(self.secret_prefix,
                                         object_name, self.id)

    def build_game_setup_view_id(self):
        return self.build_slack_object_id('game_setup_view')

    def build_guess_view_id(self):
        return self.build_slack_object_id('guess_view')

    def build_vote_view_id(self):
        return self.build_slack_object_id('vote_view')

    def build_guess_button_block_id(self):
        return self.build_slack_object_id('guess_button_block')

    def build_vote_button_block_id(self):
        return self.build_slack_object_id('vote_button_block')

    def build_game_setup_view(self):
        id_ = self.build_game_setup_view_id()
        return views.build_game_setup_view(id_)

    def build_guess_view(self):
        id_ = self.build_guess_view_id()
        return views.build_guess_view(id_, self.get_question())

    def open_view(self, trigger_id, view):
        slack_client = self.get_slack_client()
        views.open_view(slack_client, trigger_id, view)

    def open_game_setup_view(self, trigger_id):
        self.open_view(trigger_id, self.build_game_setup_view())

    def open_guess_view(self, trigger_id):
        self.open_view(trigger_id, self.build_guess_view())

    def build_topic_path(self, topic_name):
        return pubsub.build_topic_path(
            self.publisher, self.project_id, topic_name)

    def publish(self, topic_name):
        topic_path = self.build_topic_path(topic_name)
        self.publisher.publish(topic_path, data=self.code)

    def trigger_pre_guess_stage(self):
        self.publish()










