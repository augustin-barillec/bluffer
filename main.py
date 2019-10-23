import json
import os
from flask import Flask, request, make_response
from slackclient import SlackClient

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

BLUFFER_CHANNEL = 'GNE9G4GBT'


with open('jsons/question.json') as f:
    question_block = json.load(f)

with open('jsons/answer_button.json') as f:
    answer_button_block = json.load(f)

with open('jsons/players.json') as f:
    players_block = json.load(f)

with open('jsons/answer_dialog.json') as f:
    answer_dialog = json.load(f)

with open('jsons/question_dialog.json') as f:
    question_dialog = json.load(f)

with open('jsons/time_remaining.json') as f:
    time_remaining = json.load(f)



blocks = [question_block, time_remaining, answer_button_block]


game = dict()





@app.route("/slack/command", methods=["POST"])
def launch_game():

    if 'ask_question' in game:

        slack_client.api_call(
            "chat.postEphemeral",
            channel=BLUFFER_CHANNEL,
            text='A game is already running',
            user=request.form['user_id'])

    else:
        slack_client.api_call(
            "dialog.open",
            trigger_id=request.form['trigger_id'],
            dialog=question_dialog
        )

    return make_response("", 200)


@app.route("/slack/message_actions", methods=["POST"])
def message_actions():

    message_action = json.loads(request.form["payload"])

    print(message_action)

    user_id = message_action['user']['id']

    if message_action["type"] == "block_actions":

        slack_client.api_call(
            "dialog.open",
            trigger_id=message_action["trigger_id"],
            dialog=answer_dialog
        )

    elif message_action["type"] == "dialog_submission":

        if 'guess' in message_action['submission']:

            if user_id not in guesses:
                players_block['text']['text'] += ' <@{}>'.format(user_id)

            guess = message_action['submission']['guess']

            guesses[user_id] = guess

            slack_client.api_call(
                "chat.update",
                channel=BLUFFER_CHANNEL,
                ts=d['ask_question']["ts"],
                text="",
                blocks=[question_block, time_remaining, answer_button_block, players_block]
            )

            slack_client.api_call(
                "chat.postEphemeral",
                channel=BLUFFER_CHANNEL,
                text='Your answer is: {}'.format(guess),
                user=user_id

            )

        elif 'question' in message_action['submission']:

            question_block['text']['text'] = message_action['submission']['question']

            d['ask_question'] = slack_client.api_call(
                "chat.postMessage",
                channel=BLUFFER_CHANNEL,
                text="",
                blocks=blocks)

    return make_response("", 200)


if __name__ == "__main__":
    app.run()
