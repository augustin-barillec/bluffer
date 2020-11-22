import base64


def build_topic_path(publisher, project_id, topic_name):
    return publisher.topic_path(project_id, topic_name)


def event_data_to_game_id(event_data):
    return base64.b64decode(event_data).decode('utf-8')


class Triggerer:

    def __init__(self, game):
        self.game = game

    def build_topic_path(self, topic_name):
        return build_topic_path(
            self.game.publisher, self.game.project_id, topic_name)

    def publish(self, topic_name):
        topic_path = self.build_topic_path(topic_name)
        self.game.publisher.publish(topic_path, data=self.game.code)

    def trigger_pre_guess_stage(self):
        self.publish('topic_pre_guess_stage')

    def trigger_guess_stage(self):
        self.publish('topic_guess_stage')

    def trigger_pre_vote_stage(self):
        self.publish('topic_pre_vote_stage')

    def trigger_vote_stage(self):
        self.publish('topic_vote_stage')

    def trigger_pre_result_stage(self):
        self.publish('topic_pre_result_stage')

    def trigger_result_stage(self):
        self.publish('topic_result_stage')
