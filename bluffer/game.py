import time
import threading
import random
from copy import deepcopy
from collections import OrderedDict
from datetime import datetime, timedelta
from bluffer.utils import *


class Game:
    def __init__(self, question, truth,
                 time_to_guess, time_to_vote,
                 game_id, slack_client):

        self.question = question
        self.truth = truth
        self.time_to_guess = time_to_guess
        self.time_to_vote = time_to_vote
        self.game_id = game_id
        self.slack_client = slack_client

        self.channel_id = game_id_to_channel_id(game_id)
        self.organizer_id = game_id_to_organizer_id(game_id)

        self.guesses = OrderedDict()
        self.votes = OrderedDict()

        self.thread_update = threading.Thread(target=self.update)
        self.thread_update.daemon = True
        self.thread_update.start()

        self.potential_guessers = None
        self.guess_deadline = None
        self.start_call = None
        self.is_started = False

        self.vote_deadline = None
        self.has_sent_vote_reminders = False

        self.results_block = None
        self.win_block = None


    def update(self):
        while True:
            if self.stage == 'game_setup_stage':
                self.potential_guessers = get_potential_guessers(self.channel_id,
                                                                 self.organizer_id)
                self.guess_deadline = compute_deadline(self.time_to_guess)
                self.start_call = self.slack_client.api_call(
                    'chat.postMessage',
                    channel=self.channel_id,
                    blocks=self.board)
                self.is_started = True

            if self.stage == 'guess_stage':
                self.update_board()

            if self.stage == 'vote_stage':
                if self.vote_deadline is None:
                    self.vote_deadline = compute_deadline(self.time_to_vote)
                if self.has_sent_vote_reminders:
                    self.send_vote_reminders()
                    self.has_sent_vote_reminders = True
                self.update_board()

            if self.stage == 'computing_results_stage':
                if self.results_block is None:
                    self.results_block = self.compute_results_block()
                if self.win_block is None:
                    self.win_block = self.compute_win_block()
                self.update_board()

            if self.stage == 'result':
                self.update_board()
                self.is_over = True

            if self.stage == 'over':
                pass

            time.sleep(5)

    def stage(self):
        if not self.is_started:
            return 'game_setup_stage'
        if self.time_left_to_guess > 0 and self.remaining_potential_guessers:
            return 'guess_stage'
        if self.time_left_to_vote > 0 and self.remaining_voters:
            return 'vote_stage'
        if self.results_block is None:
            return 'computing_result_board'
        return 'result_stage'

    def update_board(self):
        self.slack_client.api_call(
            'chat.update',
            channel=self.channel_id,
            ts=self.start_call['ts'],
            blocks=self.board)

    @staticmethod
    def nice_display(user_id):
        return '<@{}>'.format(user_id)

    def nice_list_display(self, user_ids):
        return ' '.join([self.nice_display(id_) for id_ in user_ids])

    @property
    def id(self):
        return build_game_id(
            self.team_id, self.channel_id, self.organizer_id, self.trigger_id)

    def build_slack_object_id(self, object_name):
        return build_slack_object_id(object_name, self.id)

    @property
    def game_setup_view_id(self):
        return self.build_slack_object_id('game_setup_view')

    @property
    def guess_button_block_id(self):
        return self.build_slack_object_id('guess_button_block')

    @property
    def vote_button_block_id(self):
        return self.build_slack_object_id('vote_button_block')

    @property
    def guess_view_id(self):
        return self.build_slack_object_id('guess_view')

    @property
    def vote_view_id(self):
        return self.build_slack_object_id('vote_view')

    @property
    def title_block(self):
        msg = 'Game set up by <@{}>!'.format(self.organizer_id)
        return text_block(msg)

    @property
    def set_up_block(self):
        return text_block('The game is being set up.')

    @property
    def question_block(self):
        return text_block('{}'.format(self.question))

    @property
    def truth_block(self):
        index = self.author_to_index('Truth')
        return text_block('Truth: {}) {}'.format(index, self.truth))

    @property
    def computing_result_block(self):
        return text_block('Computing results :drum_with_drumsticks:')

    @property
    def guess_button_block(self):
        res = button_block('Your guess')
        res['block_id'] = self.guess_button_block_id
        return res

    @property
    def vote_button_block(self):
        res = button_block('Your vote')
        res['block_id'] = self.vote_button_block_id
        return res

    @property
    def guess_timer_block(self):
        return text_block('Time left to guess: {}'.format(
            nice_time_display(self.time_left_to_guess)))

    @property
    def vote_timer_block(self):
        return text_block('Time left to vote: {}'.format(
            nice_time_display(self.time_left_to_vote)))

    def own_guess_block(self, voter):
        index = self.author_to_index(voter)
        guess = self.author_to_proposal(voter)
        return text_block('Your guess is: {}) {}'.format(index, guess))

    @property
    def guessers_block(self):
        if not self.guessers:
            return text_block('No one has guessed yet.')
        guessers_for_display = self.nice_list_display(self.guessers)
        return text_block('Guessers: {}'.format(guessers_for_display))

    @property
    def voters_block(self):
        if not self.guessers:
            return text_block('No one has voted yet.')
        voters_for_display = self.nice_list_display(self.voters)
        return text_block('Voters: {}'.format(voters_for_display))

    @property
    def anonymous_proposals_block(self):
        msg = ['Proposals:']
        for index, author, proposal in self.signed_proposals:
            msg.append('{}) {}'.format(index, proposal))
        msg = '\n'.join(msg)
        return text_block(msg)

    def get_results_block(self):
        if not self.guessers:
            return text_block('No one played this game :sob:.')
        msg = ['Scores:']
        for r in deepcopy(self.results):
            player = r['guesser']
            index = r['index']
            guess = r['guess']
            r_msg = '{} wrote {}) {}'.format(
                self.nice_display(player), index, guess)
            if player in self.voters:
                voted_for = r['chosen_author']
                if voted_for != 'Truth':
                    voted_for = self.nice_display(voted_for)
                score = r['score']
                if score == 1:
                    p = 'point'
                else:
                    p = 'points'
                r_msg += ', voted for {} and scores {} {}.'.format(
                    voted_for, score, p)
            else:
                r_msg += ', did not vote and so scores 0 points.'
            msg.append(r_msg)
        msg = '\n'.join(msg)
        return text_block(msg)

    def get_win_block(self):
        res = None
        if not self.voters:
            msg = 'No one voted :sob:.'
            res = text_block(msg)
        if len(self.winners) == len(self.voters):
            msg = "Well, it's a draw between the voters! :scales:"
            res = text_block(msg)
        if len(self.winners) == 1:
            w = self.nice_display(self.winners[0])
            msg = "And the winner is {}! :first_place_medal:".format(w)
            res = text_block(msg)
        if len(self.winners) > 1:
            ws = [self.nice_display(w) for w in self.winners]
            msg_aux = ','.join(ws[:-1])
            msg_aux += ' and {}'.format(ws[-1])
            msg = "And the winners are {}! :clap:".format(msg_aux)
            res = text_block(msg)
        return res

    @property
    def game_setup_view(self):
        res = game_setup_view_template
        res['callback_id'] = self.game_setup_view_id
        return res

    @property
    def guess_view(self):
        res = deepcopy(guess_view_template)
        res['callback_id'] = self.guess_view_id
        input_block = deepcopy(res['blocks'][0])
        res['blocks'] = [self.question_block, input_block]
        return res

    def vote_view(self, voter):
        res = deepcopy(vote_view_template)
        res['callback_id'] = self.vote_view_id
        input_block_template = res['blocks'][0]
        option_template = input_block_template['element']['options'][0]
        vote_options = []
        for index, guess in self.votable_proposals(voter):
            vote_option = deepcopy(option_template)
            vote_option['text']['text'] = '{}) {}'.format(index, guess)
            vote_option['value'] = '{}'.format(index)
            vote_options.append(vote_option)
        input_block = input_block_template
        input_block['element']['options'] = vote_options
        res['blocks'] = [self.own_guess_block(voter), input_block]
        return res

    @property
    def board(self):

        if self.stage == 'set_up_stage':
            board = [
                divider_block,
                self.title_block,
                self.set_up_block,
                divider_block]
            return board

        if self.stage == 'guess_stage':

            board = [
                divider_block,
                self.title_block,
                self.question_block,
                self.guess_button_block,
                self.guess_timer_block,
                self.guessers_block,
                divider_block]
            return board

        if self.stage == 'vote_stage':

            if not self.has_set_vote_deadline:
                self.set_vote_deadline()
                self.has_set_vote_deadline = True

            if not self.guessers:
                board = [
                    divider_block,
                    self.title_block,
                    self.question_block,
                    divider_block
                ]
                return board
            board = [
                divider_block,
                self.title_block,
                self.question_block,
                self.guessers_block,
                self.anonymous_proposals_block,
                self.vote_button_block,
                self.vote_timer_block,
                self.voters_block,
                divider_block
            ]
            return board

        if self.stage == 'computing_result_stage':
            board = [
                divider_block,
                self.title_block,
                self.question_block,
                self.computing_result_block,
                divider_block
            ]
            return board

        if self.stage == 'result_stage':
            if not self.guessers:
                board = [
                    divider_block,
                    self.title_block,
                    self.question_block,
                    self.results_block,
                    divider_block]
                return board
            board = [
                divider_block,
                self.title_block,
                self.question_block,
                self.truth_block,
                self.results_block,
                self.win_block,
                divider_block]
            return board

    def set_guess_deadline(self):
        self.guess_deadline = (datetime.now()
                               + timedelta(seconds=self.time_to_guess))

    def set_vote_deadline(self):
        self.vote_deadline = (datetime.now()
                              + timedelta(seconds=self.time_to_vote))

    @property
    def time_left_to_guess(self):
        return time_left(self.guess_deadline)

    @property
    def time_left_to_vote(self):
        return time_left(self.vote_deadline)

    @property
    def stage(self):
        if self.potential_guessers is None:
            return 'set_up_stage'
        if self.time_left_to_guess > 0 and self.remaining_potential_guessers:
            return 'guess_stage'
        if not self.has_set_vote_deadline:
            return 'vote_stage'
        if self.time_left_to_vote > 0 and self.remaining_potential_voters:
            return 'vote_stage'
        if self.results_block is None or self.win_block is None:
            return 'computing_result_stage'
        return 'result_stage'

    @property
    def is_running(self):
        return self.is_started and not self.is_over

    @property
    def guessers(self):
        return self.guesses.keys()

    @property
    def voters(self):
        return self.votes.keys()

    @property
    def potential_voters(self):
        return set(self.guessers)

    @property
    def remaining_potential_guessers(self):
        return self.potential_guessers - set(self.guessers)

    @property
    def remaining_potential_voters(self):
        return self.potential_voters - set(self.voters)

    @property
    def signed_proposals(self):
        if self._signed_proposals is None:
            res = list(self.guesses.items()) + [('Truth', self.truth)]
            random.shuffle(res)
            res = [(index, author, proposal)
                   for index, (author, proposal) in enumerate(res, 1)]
            self._signed_proposals = res
        return self._signed_proposals

    def index_to_author(self, index):
        for index_, author, proposal in self.signed_proposals:
            if index_ == index:
                return author

    def author_to_index(self, author):
        for index, author_, proposal in self.signed_proposals:
            if author == author_:
                return index

    def index_to_proposal(self, index):
        for index_, author, proposal in self.signed_proposals:
            if index_ == index:
                return proposal

    def author_to_proposal(self, author):
        for index_, author_, proposal in self.signed_proposals:
            if author_ == author:
                return proposal

    def votable_proposals(self, voter):
        res = []
        for index, author, proposal in self.signed_proposals:
            if author != voter:
                res.append((index, proposal))
        return res

    def truth_score(self, voter):
        return int(self.votes[voter] == self.author_to_index('Truth'))

    def bluff_score(self, voter):
        res = 0
        for voter_ in self.votes.keys():
            voter_index = self.author_to_index(voter)
            if self.votes[voter_] == voter_index:
                res += 2
        return res

    @property
    def results(self):
        if self._results is None:
            results = []
            for index, author, proposal in self.signed_proposals:
                r = dict()
                if author == 'Truth':
                    continue
                r['index'] = index
                r['guesser'] = author
                r['guess'] = proposal
                if author not in self.voters:
                    r['score'] = 0
                    results.append(r)
                    continue
                vote_index = self.votes[author]
                r['vote_index'] = vote_index
                r['chosen_author'] = self.index_to_author(vote_index)
                r['chosen_proposal'] = self.index_to_proposal(vote_index)
                r['truth_score'] = self.truth_score(author)
                r['bluff_score'] = self.bluff_score(author)
                r['score'] = r['truth_score'] + r['bluff_score']
                results.append(r)

            def sort_key(r_):
                return 'vote_index' not in r_, -r_['score'], r_['guesser']
            results.sort(key=lambda r_: sort_key(r_))

            self._results = results
        return self._results

    @property
    def max_score(self):
        if self._max_score is None:
            scores = [r['score'] for r in self.results if 'score' in r]
            res = scores[0]
            self._max_score = res
        return self._max_score

    @property
    def winners(self):
        if self._winners is None:
            max_score = self.max_score
            res = []
            for r in self.results:
                if r['score'] == max_score:
                    res.append(r['guesser'])
            self._winners = res
        return self._winners

    def start(self):
        self.set_guess_deadline()

        self.start_call = self.slack_client.api_call(
            'chat.postMessage',
            channel=self.channel_id,
            blocks=self.board)

        self.thread_update_regularly = threading.Thread(
            target=self.update_regularly)
        self.thread_update_regularly.daemon = True
        self.thread_update_regularly.start()

        self.is_started = True

    def update_board(self):
        self.slack_client.api_call(
            'chat.update',
            channel=self.channel_id,
            ts=self.start_call['ts'],
            blocks=self.board)


    def update_regularly(self):
        while True:
            if not self.has_set_potential_guessers:
                self.potential_guessers = get_potential_guessers(
                    self.slack_client, self.channel_id) - {self.organizer_id}
                self.has_set_potential_guessers = True

            is_vote_stage = self.stage == 'vote_stage'
            if is_vote_stage and not self.has_sent_vote_reminders:
                self.send_vote_reminders()
                self.has_sent_vote_reminders = True

            if self.stage == 'computing_result_stage':
                self.results_block = self.get_results_block()
                if self.guessers:
                    self.win_block = self.get_win_block()
                else:
                    self.win_block = ''

            self.update()

            time.sleep(5)

    def open_game_setup_view(self, trigger_id):
        self.slack_client.api_call(
            'views.open',
            trigger_id=trigger_id,
            view=self.game_setup_view)

    def open_guess_view(self, trigger_id):
        self.slack_client.api_call(
            'views.open',
            trigger_id=trigger_id,
            view=self.guess_view)

    def open_vote_view(self, trigger_id, voter):
        self.slack_client.api_call(
            'views.open',
            trigger_id=trigger_id,
            view=self.vote_view(voter))

    def send_vote_reminders(self):
        for u in self.guessers:
            msg = ("Hey {}, you can now vote in the bluffer game organized "
                   "by {}. You have {} left. Will you find the truth ? :mag:"
                   .format(self.nice_display(u),
                           self.nice_display(self.organizer_id),
                           nice_time_display(self.time_to_vote)))
            self.slack_client.api_call(
                'chat.postEphemeral',
                channel=self.channel_id,
                user=u,
                text=msg)

    def collect_setup(self, view):
        values = view['state']['values']
        self.question = values['question']['question']['value']
        self.truth = values['truth']['truth']['value']
        if not self.debug:
            self.time_to_guess = int((values['time_to_guess']['time_to_guess']
                                      ['selected_option']['value']))*60
            self.time_to_vote = int((values['time_to_vote']['time_to_vote']
                                     ['selected_option']['value']))*60
        else:
            self.time_to_guess = 40
            self.time_to_vote = 35

    def add_guess(self, guesser, guess_view):
        values = guess_view['state']['values']
        guess = values['guess']['guess']['value']
        self.guesses[guesser] = guess

    def add_vote(self, voter, vote_view):
        values = vote_view['state']['values']
        vote = int(values['vote']['vote']['selected_option']['value'])
        self.votes[voter] = vote
