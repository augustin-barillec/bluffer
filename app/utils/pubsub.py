def build_topic_path(publisher, project_id, topic_name):
    return publisher.topic_path(project_id, topic_name)


class StageTriggerer:

    def __init__(self, publisher, project_id, game_id):
        self.publisher = publisher
        self.project_id = project_id
        self.game_id = game_id

    def build_topic_path(self, topic_name):
        return build_topic_path(
            self.publisher, self.project_id, topic_name)

    def publish(self, topic_name):
        topic_path = self.build_topic_path(topic_name)
        self.publisher.publish(
            topic_path,
            data='no_data'.encode('utf-8'),
            game_id=self.game_id)

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
