import time
import threading
import random
from copy import deepcopy
from datetime import datetime, timedelta
from bluffer.utils import time_remaining, game_setup_view_template, \
    guess_view_template, divider_block, text_block, button_block


class Game:
    def __init__(self, team_id, channel_id, organizer_id,
                 trigger_id, slack_client):
        self.team_id = team_id
        self.channel_id = channel_id
        self.organizer_id = organizer_id
        self.trigger_id = trigger_id
        self.slack_client = slack_client

        self.question = None
        self.answer = None
        self.time_to_guess = None
        self.time_to_vote = None

        self.start_datetime = None
        self.guess_deadline = None
        self.vote_deadline = None
        self.thread_update_board_regularly = None

        self.start_call = None

        self.guessers = []
        self.voters = set()

        self.guesses = dict()
        self.votes = dict()

    def ask_for_setup(self, trigger_id):
        self.slack_client.api_call(
            "views.open",
            trigger_id=trigger_id,
            view=self.game_setup_view)

    def collect_setup(self, view):
        values = view['state']['values']
        self.question = values['question']['question']['value']
        self.answer = values['answer']['answer']['value']
        self.time_to_guess = int((values['time_to_guess']['time_to_guess']
                                  ['selected_option']['value']))*60
        self.time_to_vote = int((values['time_to_vote']['time_to_vote']
                                 ['selected_option']['value']))

    @property
    def time_remaining_to_guess(self):
        return time_remaining(self.guess_deadline)

    @property
    def time_remaining_to_vote(self):
        return time_remaining(self.vote_deadline)

    @property
    def stage(self):
        if self.time_remaining_to_guess > 0:
            return 'guess_stage'
        elif self.time_remaining_to_vote > 0:
            return 'vote_stage'
        else:
            return 'result_stage'

    @property
    def title_block(self):
        return text_block('*Bluffer game*')

    @property
    def organizer_block(self):
        msg = "Set up by <@{}> !".format(self.organizer_id)
        res = text_block(msg)
        res['block_id'] = self.organizer_id
        return text_block(msg)

    @property
    def question_block(self):
        return text_block('{}'.format(self.question))

    @property
    def answer_block(self):
        return text_block('The answer is: {}'.format(self.answer))

    @property
    def guess_button_block(self):
        res = button_block('Your guess')
        res['block_id'] = self.guess_button_id
        return res

    @property
    def vote_button_block(self):
        return button_block('Your vote')

    @property
    def guess_timer_block(self):
        return text_block('Time remaining to guess: {}'.format(
            self.time_remaining_to_guess))

    @property
    def vote_timer_block(self):
        return text_block('Time remaining to vote: {}'.format(
            self.time_remaining_to_vote))

    @staticmethod
    def users_for_display(users):
        res = ['<@{}>'.format(u) for u in users]
        res = ' '.join(res)
        return res

    @property
    def guessers_block(self):
        guessers_for_display = self.users_for_display(self.guessers)
        return text_block('Guessers are: {}'.format(guessers_for_display))

    @property
    def voters_block(self):
        voters_for_display = self.users_for_display(self.voters)
        return text_block('Voters are: {}'.format(voters_for_display))

    @property
    def scores_block(self):
        return text_block('The scores are...')

    @property
    def graph_block(self):
        return text_block('The graph is...')

    @property
    def board(self):
        guess_stage_board = [
            divider_block,
            self.title_block,
            divider_block,
            self.organizer_block,
            divider_block,
            self.question_block,
            divider_block,
            self.guess_button_block,
            self.guess_timer_block,
            self.guessers_block,
            divider_block
        ]

        vote_stage_board = [
            divider_block,
            self.title_block,
            divider_block,
            self.organizer_block,
            divider_block,
            self.question_block,
            self.guessers_block,
            divider_block,
            self.vote_button_block,
            self.vote_timer_block,
            self.voters_block,
            divider_block
        ]

        result_stage_board = [
            divider_block,
            self.title_block,
            divider_block,
            self.organizer_block,
            divider_block,
            self.question_block,
            divider_block,
            self.guessers_block,
            divider_block,
            self.voters_block,
            divider_block,
            self.answer_block,
            self.scores_block,
            self.graph_block
        ]

        if self.stage == 'guess_stage':
            return guess_stage_board
        if self.stage == 'vote_stage':
            return vote_stage_board
        if self.stage == 'result_stage':
            return result_stage_board

    def start(self):
        self.start_datetime = datetime.now()
        self.guess_deadline = (self.start_datetime
                               + timedelta(seconds=self.time_to_guess))
        self.vote_deadline = (self.guess_deadline
                              + timedelta(seconds=self.time_to_vote))
        self.start_call = self.slack_client.api_call(
            "chat.postMessage",
            channel=self.channel_id,
            text="",
            blocks=self.board)

        self.thread_update_board_regularly = threading.Thread(
            target=self.update_board_regularly)
        self.thread_update_board_regularly.start()

    def update_board(self):
        self.slack_client.api_call(
            "chat.update",
            channel=self.channel_id,
            ts=self.start_call["ts"],
            text="",
            blocks=self.board)

    def update_board_regularly(self):
        while True:
            self.update_board()
            time.sleep(1)

    @property
    def id(self):
        return '{}#{}#{}#{}'.format(
            self.team_id, self.channel_id, self.organizer_id, self.trigger_id
        )

    def build_object_id(self, object_name):
        return "bluffer#{}#{}".format(object_name, self.id)

    @property
    def game_setup_view_id(self):
        return self.build_object_id('game_setup_view')

    @property
    def guess_button_id(self):
        return self.build_object_id('guess_button')

    @property
    def guess_view_id(self):
        return self.build_object_id('guess_view')

    @property
    def game_setup_view(self):
        res = game_setup_view_template
        res['callback_id'] = self.game_setup_view_id
        return res

    @staticmethod
    def previous_guess_block(previous_guess):
        return text_block('Your previous guess: {}'.format(previous_guess))

    def guess_view(self, previous_guess=None):
        res = deepcopy(guess_view_template)
        if previous_guess is not None:
            res['blocks'] = [res['blocks'][0]] + res['blocks']
            res['blocks'][1] = self.previous_guess_block(previous_guess)
        res['blocks'][0] = self.question_block
        res['callback_id'] = self.guess_view_id
        return res

    def open_guess_view(self, trigger_id, previous_guess):
        self.slack_client.api_call(
            "views.open",
            trigger_id=trigger_id,
            view=self.guess_view(previous_guess))

    def add_or_update_guess(self, user_id, view):
        values = view['state']['values']
        guess = values['guess']['guess']['value']
        self.guesses[user_id] = guess

    @property
    def signed_propositions(self):
        numbers = list(range(1, len(self.guesses) + 1))
        shuffle(numbers)
        res0 = list(self.guesses.items()) + [(None, self.answer)]
        res = dict()
        for n, p in zip(numbers, res0):
            res[n] = p
        return res

    d


    def vote_view(self, user_id):