from copy import deepcopy
from datetime import datetime, timedelta
import time
import threading
from bluffer.utils import get_modal, get_block

game_setup = get_modal(__file__, 'game_setup.json')
your_guess = get_modal(__file__, 'your_guess.json')
button_block = get_block(__file__, 'button.json')
divider_block = get_block(__file__, 'divider.json')
image_block = get_block(__file__, 'image.json')
text_block = get_block(__file__, 'text.json')


class Game:
    def __init__(self, channel_id, organizer_id, slack_client):
        self.channel_id = channel_id
        self.organizer_id = organizer_id
        self.slack_client = slack_client

        self.question = None
        self.answer = None
        self.time_to_guess = None
        self.time_to_vote = None

        self.start_call = None

        self.players = ''

        self.guesses = dict()

        self.start_datetime = None
        self.deadline_1 = None
        self.t1 = None

    @staticmethod
    def text_block(message):
        res = deepcopy(text_block)
        res['text']['text'] = message
        return res

    @staticmethod
    def button_block(message):
        res = deepcopy(button_block)
        res['elements'][0]['text']['text'] = message
        return res

    def ask_setup(self, trigger_id):
        self.slack_client.api_call(
            "views.open",
            trigger_id=trigger_id,
            view=game_setup)

    def collect_setup(self, view):
        values = view['state']['values']
        self.question = values['question']['question']['value']
        self.answer = values['answer']['answer']['value']
        self.time_to_guess = (values['time_to_guess']['time_to_guess']
                              ['selected_option']['value'])
        self.time_to_vote = (values['time_to_vote']['time_to_vote']
                             ['selected_option']['value'])

    @property
    def time_remaining_to_guess(self):
        return (self.deadline_1 - datetime.now()).seconds

    @property
    def title_block(self):
        return self.text_block('*Bluffer game*')

    @property
    def organizer_block(self):
        msg = "Set up by <@{}> !".format(self.organizer_id)
        res = self.text_block(msg)
        res['block_id'] = self.organizer_id
        return res

    @property
    def question_block(self):
        return self.text_block('{}'.format(self.question))

    @property
    def guess_button_block(self):
        return self.button_block('Your guess')

    @property
    def time_to_guess_block(self):
        return self.text_block('Time remaining to guess: {}'.format(
            self.time_remaining_to_guess))

    @property
    def players_block(self):
        return self.text_block('Players are: {}'.format(self.players))

    @property
    def starting_board(self):
        return [
            divider_block,
            self.title_block,
            divider_block,
            self.organizer_block,
            divider_block,
            self.question_block,
            self.guess_button_block,
            self.time_to_guess_block,
            self.players_block,
            divider_block
        ]

    def start(self):
        self.start_datetime = datetime.now()
        self.deadline_1 = self.start_datetime + timedelta(
            seconds=int(self.time_to_guess)*60)

        self.start_call = self.slack_client.api_call(
            "chat.postMessage",
            channel=self.channel_id,
            text="",
            blocks=self.starting_board)

        self.t1 = threading.Thread(target=self.update_regularly_starting_board)
        self.t1.start()

    @property
    def your_guess_modal(self):
        res = your_guess
        res['blocks'][0] = self.question_block
        res['callback_id'] = 'your_guess#{}'.format(self.organizer_id)
        return res

    def send_your_guess_modal(self, trigger_id):
        self.slack_client.api_call(
            "views.open",
            trigger_id=trigger_id,
            view=self.your_guess_modal)

    def update_starting_board(self):
        self.slack_client.api_call(
            "chat.update",
            channel=self.channel_id,
            ts=self.start_call["ts"],
            text="",
            blocks=self.starting_board)

    def update_regularly_starting_board(self):
        while True:
            self.update_starting_board()
            time.sleep(0.01)

    def add_guess(self, user_id, view):
        values = view['state']['values']
        guess = values['your_guess']['your_guess']['value']
        self.guesses[user_id] = guess
