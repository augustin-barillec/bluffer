import base64


def build_topic_path(project_id, topic_name):
    return 'projects/{}/topics/{}'.format(project_id, topic_name)


class Triggerer:

    def __init__(self, publisher, project_id, game_id=None):
        self.publisher = publisher
        self.project_id = project_id
        self.game_id = game_id

    def build_topic_path(self, topic_name):
        return build_topic_path(self.project_id, topic_name)

    def trigger_handle_slash_command(self):
        topic_path = self.build_topic_path('topic_handle_slash_command')
        self.publisher.publish(
            topic_path, game_id=self.game_id)

    def trigger_handle_message_actions(self, message_action):
        topic_path = self.build_topic_path('topic_handle_message_actions')
        message_action = message_action.encode("utf-8")
        self.publisher.publish(topic_path, data=message_action)

    def trigger_stage(self, topic_name):
        topic_path = self.build_topic_path(topic_name)
        self.publisher.publish(topic_path, game_id=self.game_id)

    def trigger_pre_guess_stage(self):
        self.trigger_stage('topic_pre_guess_stage')

    def trigger_guess_stage(self):
        self.trigger_stage('topic_guess_stage')

    def trigger_pre_vote_stage(self):
        self.trigger_stage('topic_pre_vote_stage')

    def trigger_vote_stage(self):
        self.trigger_stage('topic_vote_stage')

    def trigger_pre_result_stage(self):
        self.trigger_stage('topic_pre_result_stage')

    def trigger_result_stage(self):
        self.trigger_stage('topic_result_stage')
