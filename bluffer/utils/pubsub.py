import base64


def build_topic_path(publisher, project_id, topic_name):
    return publisher.topic_path(project_id, topic_name)


def event_data_to_game_id(event_data):
    return base64.b64decode(event_data).decode('utf-8')
