from datetime import datetime, timedelta

question_datetime = datetime.now()
deadline_1 = question_datetime + timedelta(seconds=100)
deadline_2 = deadline_1 + timedelta(seconds=50)


def send_time_remaining():

    previous_tr = None

    tr = (deadline_1 - question_datetime).seconds

    while tr >= 0:

        if previous_tr is not None and tr < previous_tr:

            time_remaining['text']['text'] = 'Time remaining: {}'.format(tr)

            slack_client.api_call(
                "chat.update",
                channel=BLUFFER_CHANNEL,
                ts=ask_question["ts"],
                text="",
                blocks=[question_block, time_remaining, answer_button_block, players_block]
            )

        time.sleep(0.001)

        previous_tr = tr

        tr = (deadline_1 - datetime.now()).seconds


t1 = threading.Thread(target=send_time_remaining)

t1.start()


time_remaining['text']['text'] = 'Time remaining: 120'
