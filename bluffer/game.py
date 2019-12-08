import time
import threading
import random
from copy import deepcopy
from collections import OrderedDict
from datetime import datetime, timedelta
from bluffer.utils import time_remaining, time_for_display,\
    game_setup_view_template, guess_view_template, vote_view_template, \
    divider_block, text_block, button_block


class Game:
    def __init__(self, team_id, channel_id, organizer_id,
                 trigger_id, slack_client, is_test):
        self.team_id = team_id
        self.channel_id = channel_id
        self.organizer_id = organizer_id
        self.trigger_id = trigger_id
        self.slack_client = slack_client
        self.is_test = is_test

        self.question = None
        self.truth = None
        self.time_to_guess = None
        self.time_to_vote = None

        self.start_datetime = None
        self.guess_deadline = None
        self.vote_deadline = None
        self.thread_update_board_regularly = None

        self.start_call = None

        self.guesses = OrderedDict()
        self.votes = OrderedDict()

    @property
    def title_block(self):
        return text_block('*bluffer game*')

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
    def truth_block(self):
        return text_block('The truth is: {}){}'.format(
            self.truth_index, self.truth))

    @property
    def guess_button_block(self):
        res = button_block('Your guess')
        res['block_id'] = self.guess_button_id
        return res

    @property
    def vote_button_block(self):
        res = button_block('Your vote')
        res['block_id'] = self.vote_button_id
        return res

    @property
    def guess_timer_block(self):
        return text_block('Time remaining to guess: {}'.format(
            time_for_display(self.time_remaining_to_guess)))

    @property
    def vote_timer_block(self):
        return text_block('Time remaining to vote: {}'.format(
            time_for_display(self.time_remaining_to_vote)))

    def own_proposition_block(self, user_id):
        index, proposition = self.own_proposition(user_id)
        return text_block('Your guess is: {}) {}'.format(index, proposition))

    @staticmethod
    def previous_guess_block(previous_guess):
        return text_block('Your previous guess: {}'.format(previous_guess))

    @staticmethod
    def previous_vote_block(previous_vote):
        return text_block('Your previous vote: {}'.format(previous_vote))

    @property
    def guessers_block(self):
        guessers_for_display = self.user_ids_for_display(self.guessers)
        return text_block('Guessers are: {}'.format(guessers_for_display))

    @property
    def voters_block(self):
        voters_for_display = self.user_ids_for_display(self.voters)
        return text_block('Voters are: {}'.format(voters_for_display))

    @property
    def results_block(self):
        msg = 'The results are: '
        for result in self.results:
            msg += '\n'
            (user_id, guess_index, guess, vote,
             truth_score, bluff_score, score) = result
            u = self.user_id_for_display(user_id)
            msg += '{} guesses {}){}'.format(u, guess_index, guess)
            msg += ' and votes for {}.'.format(vote)
            msg += ' Truth score = {}.'.format(truth_score)
            msg += ' Bluff score = {}.'.format(bluff_score)
            msg += ' Score = {}.'.format(score)
        return text_block(msg)

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
            self.truth_block,
            self.results_block
        ]

        if self.stage == 'guess_stage':
            return guess_stage_board
        if self.stage == 'vote_stage':
            return vote_stage_board
        if self.stage == 'result_stage':
            return result_stage_board

    @property
    def game_setup_view(self):
        res = game_setup_view_template
        res['callback_id'] = self.game_setup_view_id
        return res

    def guess_view(self, previous_guess):
        res = deepcopy(guess_view_template)
        res['callback_id'] = self.guess_view_id
        input_block = deepcopy(res['blocks'][1])
        res['blocks'] = [self.question_block]
        if previous_guess is not None:
            res['blocks'].append(self.previous_guess_block(previous_guess))
        res['blocks'].append(input_block)
        return res

    def vote_view(self, user_id, previous_vote):
        res = deepcopy(vote_view_template)
        res['callback_id'] = self.vote_view_id
        input_block_template = res['blocks'][0]
        option_template = input_block_template['element']['options'][0]
        vote_options = []
        for index, proposition in self.votable_propositions(user_id):
            vote_option = deepcopy(option_template)
            vote_option['text']['text'] = '{}) {}'.format(index, proposition)
            vote_option['value'] = '{}'.format(index)
            vote_options.append(vote_option)
        input_block = input_block_template
        input_block['element']['options'] = vote_options
        res['blocks'] = []
        if previous_vote is not None:
            res['blocks'].append(self.previous_vote_block(previous_vote))
        res['blocks'] += [self.own_proposition_block(user_id), input_block]
        return res

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
    def vote_button_id(self):
        return self.build_object_id('vote_button')

    @property
    def guess_view_id(self):
        return self.build_object_id('guess_view')

    @property
    def vote_view_id(self):
        return self.build_object_id('vote_view')

    @property
    def signed_propositions(self):
        res = list(self.guesses.items()) + [(None, self.truth)]
        random.Random(self.id).shuffle(res)
        res = [(i, author, proposition)
               for i, (author, proposition) in enumerate(res, 1)]
        return res

    @property
    def truth_index(self):
        for index, author, proposition in self.signed_propositions:
            if author is None:
                return index

    def guess_index(self, user_id):
        for index, author, proposition in self.signed_propositions:
            if author == user_id:
                return index

    def votable_propositions(self, user_id):
        res = []
        for index, author, proposition in self.signed_propositions:
            if author != user_id:
                res.append((index, proposition))
        return res

    def own_proposition(self, user_id):
        for index, author, proposition in self.signed_propositions:
            if author == user_id:
                return index, proposition

    @property
    def guessers(self):
        return self.guesses.keys()

    @property
    def voters(self):
        return self.votes.keys()

    @staticmethod
    def user_id_for_display(user_id):
        return '<@{}>'.format(user_id)

    def user_ids_for_display(self, user_ids):
        res = [self.user_id_for_display(u) for u in user_ids]
        res = ' '.join(res)
        return res

    def start(self):
        self.start_datetime = datetime.now()
        self.guess_deadline = (self.start_datetime
                               + timedelta(seconds=self.time_to_guess))
        self.vote_deadline = (self.guess_deadline
                              + timedelta(seconds=self.time_to_vote))
        self.start_call = self.slack_client.api_call(
            'chat.postMessage',
            channel=self.channel_id,
            text="",
            blocks=self.board)

        self.thread_update_board_regularly = threading.Thread(
            target=self.update_board_regularly)
        self.thread_update_board_regularly.daemon = True
        self.thread_update_board_regularly.start()

    def update_board(self):
        self.slack_client.api_call(
            'chat.update',
            channel=self.channel_id,
            ts=self.start_call["ts"],
            text="",
            blocks=self.board)

    def update_board_regularly(self):
        while True:
            self.update_board()
            time.sleep(5)

    def open_game_setup_view(self, trigger_id):
        self.slack_client.api_call(
            'views.open',
            trigger_id=trigger_id,
            view=self.game_setup_view)

    def open_guess_view(self, trigger_id, previous_guess):
        self.slack_client.api_call(
            'views.open',
            trigger_id=trigger_id,
            view=self.guess_view(previous_guess))

    def open_vote_view(self, trigger_id, user_id, previous_vote):
        self.slack_client.api_call(
            'views.open',
            trigger_id=trigger_id,
            view=self.vote_view(user_id, previous_vote))

    def collect_setup(self, view):
        values = view['state']['values']
        self.question = values['question']['question']['value']
        self.truth = values['truth']['truth']['value']
        if not self.is_test:
            self.time_to_guess = int((values['time_to_guess']['time_to_guess']
                                      ['selected_option']['value']))*60
            self.time_to_vote = int((values['time_to_vote']['time_to_vote']
                                     ['selected_option']['value']))*60
        else:
            self.time_to_guess = 40
            self.time_to_vote = 40

    def add_or_update_guess(self, user_id, guess_view):
        values = guess_view['state']['values']
        guess = values['guess']['guess']['value']
        self.guesses[user_id] = guess

    def add_or_update_vote(self, user_id, vote_view):
        values = vote_view['state']['values']
        vote = int(values['vote']['vote']['selected_option']['value'])
        self.votes[user_id] = vote

    def truth_score(self, user_id):
        return int(self.votes[user_id] == self.truth_index)

    def bluff_score(self, user_id):
        res = 0
        for voter in self.votes.keys():
            if self.votes[voter] == self.guess_index(user_id):
                res += 2
        return res

    def score(self, user_id):
        return self.truth_score(user_id) + self.bluff_score(user_id)

    def result(self, user_id):
        return (
            user_id,
            self.guess_index(user_id),
            self.guesses[user_id],
            self.votes[user_id],
            self.truth_score(user_id),
            self.bluff_score(user_id),
            self.score(user_id)
        )

    @property
    def results(self):
        res = [self.result(voter) for voter in self.votes.keys()]
        res = sorted(res, key=lambda r: -r[-1])
        return res

    @property
    def time_remaining_to_guess(self):
        return time_remaining(self.guess_deadline)

    @property
    def time_remaining_to_vote(self):
        return time_remaining(self.vote_deadline)

    @property
    def stage(self):
        if self.time_to_guess is None:
            return 'setup_stage'
        if self.time_remaining_to_guess > 0:
            return 'guess_stage'
        if self.time_remaining_to_vote > 0:
            return 'vote_stage'
        return 'result_stage'
