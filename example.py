from flask import Flask, request, make_response
import json

from slackclient import SlackClient

SLACK_BOT_TOKEN = ""
slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

BLUFFER_CHANNEL = 'GNE9G4GBT'
QUESTION = "Quel était le slogan de coca en 1933 ?"


with open('question.json') as f:
    question_block = json.load(f)

with open('answer_button.json') as f:
    answer_button_block = json.load(f)

with open('contestants.json') as f:
    contestants_block = json.load(f)

with open('dialog.json') as f:
    dialog = json.load(f)

question_block['text']['text'] = QUESTION

dialog['elements'][0]['label'] = QUESTION

blocks = [question_block, answer_button_block]

ask_question = slack_client.api_call(
  "chat.postMessage",
  channel=BLUFFER_CHANNEL,
  text="",
  blocks=blocks)

print(ask_question)

guesses = {}


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():

    message_action = json.loads(request.form["payload"])

    print(message_action)

    user_id = message_action['user']['id']

    if message_action["type"] == "block_actions":

        open_dialog = slack_client.api_call(
            "dialog.open",
            trigger_id=message_action["trigger_id"],
            dialog=dialog
        )

    elif message_action["type"] == "dialog_submission":

        contestants_block['text']['text'] += ' <@{}>'.format(user_id)

        guesses[user_id] = message_action['submission']['comment']

        slack_client.api_call(
            "chat.update",
            channel=BLUFFER_CHANNEL,
            ts=ask_question["ts"],
            text="",
            blocks=[question_block, answer_button_block, contestants_block]
        )

    return make_response("", 200)


if __name__ == "__main__":
    app.run()
