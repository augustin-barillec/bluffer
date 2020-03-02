import base64
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()

project_id = 'project-20190222-269014'
topic_name = 'hello_topic'
topic_path = publisher.topic_path(project_id, topic_name)


def toto(request):
    data = 'Hello hello'.encode('utf-8')
    publisher.publish(topic_path, data=data)


def triggered_by_pubsub(event, context):

    print("""This Function was triggered by messageId {} published at {}
    """.format(context.event_id, context.timestamp))

    if 'data' in event:
        name = base64.b64decode(event['data']).decode('utf-8')
    else:
        name = 'World'
    print('Hello {}!'.format(name))


def hello(request):
    return "Hello world!"


if __name__== '__main__':
    toto(None)
