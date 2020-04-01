from functions_framework import create_app

source = '/home/augustin/PycharmProjects/bluffer/test2/main.py'
target = "triggered_by_pubsub"

background_json = {
        "context": {
            "eventId": "some-eventId",
            "timestamp": "some-timestamp",
            "eventType": "some-eventType",
            "resource": "some-resource",
        },
        "data": {"filename": "toto", "value": "some-value"},
    }


client = create_app(target, source, "event").test_client()

resp = client.post("/", json=background_json)

print(resp)