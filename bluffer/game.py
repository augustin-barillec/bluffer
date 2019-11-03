from copy import deepcopy
from bluffer.utils import get_modal, get_block

game_setup = get_modal(__file__, 'game_setup.json')
button_block = get_block(__file__, 'button.json')
divider_block = get_block(__file__, 'divider.json')
image_block = get_block(__file__, 'image.json')
text_block = get_block(__file__, 'text.json')


class Game:
    def __init__(self, trigger_id, channel_id, organizer_id, slack_client):
        self.trigger_id = trigger_id
        self.channel_id = channel_id
        self.organizer_id = organizer_id
        self.slack_client = slack_client

        self.question = None
        self.answer = None
        self.time_to_guess = None
        self.time_to_vote = None

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

    def ask_setup(self):
        self.slack_client.api_call(
            "views.open",
            trigger_id=self.trigger_id,
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
        return 3

    @property
    def players(self):
        return ''

    @property
    def title_block(self):
        return self.text_block('*Bluffer game*')

    @property
    def organizer_block(self):
        msg = "Set up by <@{}> !".format(self.organizer_id)
        return self.text_block(msg)

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
        self.slack_client.api_call(
            "chat.postMessage",
            channel=self.channel_id,
            text="",
            blocks=self.starting_board)
