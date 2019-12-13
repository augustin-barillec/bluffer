import time
import threading
import random
from copy import deepcopy
from collections import OrderedDict
from datetime import datetime, timedelta
from bluffer.utils import \
    game_setup_view_template, guess_view_template, vote_view_template, \
    divider_block, text_block, button_block, \
    build_game_id, build_slack_object_id, \
    time_left, nice_time_display, \
    get_channel_non_bot_members


class Game:
    def __init__(self, team_id, channel_id, organizer_id,
                 trigger_id, slack_client, debug):
        self.team_id = team_id
        self.channel_id = channel_id
        self.organizer_id = organizer_id
        self.trigger_id = trigger_id
        self.slack_client = slack_client
        self.debug = debug

        self.potential_guessers = None

        self.question = None
        self.truth = None
        self.time_to_guess = None
        self.time_to_vote = None

        self.start_datetime = None
        self.guess_deadline = None
        self.vote_deadline = None
        self.thread_update_regularly = None

        self.start_call = None

        self.is_started = False
        self.is_over = False

        self.has_set_potential_guessers = False
        self.has_set_vote_deadline = False
        self.has_sent_vote_reminders = False
        self._signed_propositions = None

        self.guesses = OrderedDict()
        self.votes = OrderedDict()

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
        return text_block('*bluffer game*')

    @property
    def organizer_block(self):
        msg = 'Set up by <@{}>!'.format(self.organizer_id)
        return text_block(msg)

    @property
    def set_up_block(self):
        return text_block('The game is being set up.')

    @property
    def question_block(self):
        return text_block('{}'.format(self.question))

    @property
    def truth_block(self):
        return text_block('Truth: {}'.format(self.truth))

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
        return text_block('Your guess is: {}'.format(self.own_guess(voter)))

    @property
    def guessers_block(self):
        guessers_for_display = self.nice_list_display(self.guessers)
        return text_block('Guessers: {}'.format(guessers_for_display))

    @property
    def voters_block(self):
        voters_for_display = self.nice_list_display(self.voters)
        return text_block('Voters: {}'.format(voters_for_display))

    @property
    def guesses_block(self):
        msg = ['Guesses:']
        for result in self.results:
            guesser = self.nice_display(result['guesser'])
            guess = result['guess']
            msg.append('{}: {}'.format(guesser, guess))
        msg = '\n'.join(msg)
        return text_block(msg)

    @property
    def votes_block(self):
        msg = ['Votes:']
        for result in self.results:
            if result['guesser'] not in self.voters:
                continue
            voter = self.nice_display(result['guesser'])
            chosen_guesser = result['chosen_guesser']
            if chosen_guesser is None:
                chosen_guesser = 'Truth'
            else:
                chosen_guesser = self.nice_display(chosen_guesser)
            chosen_guess = result['chosen_guess']
            msg.append('{} votes for {}: {}'.format(voter, chosen_guesser,
                                                    chosen_guess))
        msg = '\n'.join(msg)
        return text_block(msg)

    @property
    def scores_block(self):
        msg = ['Scores:']
        for result in self.results:
            if result['guesser'] not in self.voters:
                continue
            voter = self.nice_display(result['guesser'])
            truth_score = result['truth_score']
            bluff_score = result['bluff_score']
            score = result['score']
            msg.append('{}: {} + 2 x {} = {}'
                       .format(voter, truth_score, bluff_score//2, score))
        msg = '\n'.join(msg)
        return text_block(msg)

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
        for index, guess in self.votable_propositions(voter):
            vote_option = deepcopy(option_template)
            vote_option['text']['text'] = '{}'.format(guess)
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
                self.organizer_block,
                self.set_up_block,
                divider_block]
            return board

        if self.stage == 'guess_stage':

            board = [
                divider_block,
                self.title_block,
                self.organizer_block,
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

            board = [
                divider_block,
                self.title_block,
                self.organizer_block,
                self.question_block,
                self.guessers_block,
                self.vote_button_block,
                self.vote_timer_block,
                self.voters_block,
                divider_block
            ]
            return board

        if self.stage == 'result_stage':
            board = [
                divider_block,
                self.title_block,
                self.organizer_block,
                self.question_block,
                self.truth_block,
                self.guesses_block,
                self.votes_block,
                self.scores_block,
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
    def signed_propositions(self):
        if self._signed_propositions is None:
            res = list(self.guesses.items()) + [(None, self.truth)]
            random.Random(self.id).shuffle(res)
            res = [(index, author, proposition)
                   for index, (author, proposition) in enumerate(res, 1)]
            self._signed_propositions = res
        return self._signed_propositions

    def own_guess(self, voter):
        for index, author, proposition in self.signed_propositions:
            if author == voter:
                return proposition

    def votable_propositions(self, voter):
        res = []
        for index, author, proposition in self.signed_propositions:
            if author != voter:
                res.append((index, proposition))
        return res

    @property
    def truth_index(self):
        for index, author, proposition in self.signed_propositions:
            if author is None:
                return index

    def guesser_to_index(self, guesser):
        for index, author, proposition in self.signed_propositions:
            if author == guesser:
                return index

    def index_to_guesser(self, index):
        for index_, author, proposition in self.signed_propositions:
            if index_ == index:
                return author

    def index_to_guess(self, index):
        for index_, author, proposition in self.signed_propositions:
            if index_ == index:
                return proposition

    def truth_score(self, voter):
        return int(self.votes[voter] == self.truth_index)

    def bluff_score(self, voter):
        res = 0
        for voter_ in self.votes.keys():
            if self.votes[voter_] == self.guesser_to_index(voter):
                res += 2
        return res

    def score(self, voter):
        return self.truth_score(voter) + self.bluff_score(voter)

    @property
    def results(self):
        results = []
        for index, author, proposition in self.signed_propositions:
            result = dict()
            if author is None:
                continue
            result['guesser'] = author
            result['guess'] = proposition
            if author not in self.voters:
                continue
            vote_index = self.votes[author]
            result['chosen_guesser'] = self.index_to_guesser(vote_index)
            result['chosen_guess'] = self.index_to_guess(vote_index)
            result['truth_score'] = self.truth_score(author)
            result['bluff_score'] = self.bluff_score(author)
            result['score'] = self.score(author)
            results.append(result)

        def sort_key(r):
            return 'score' not in r, -r['score'], r['guesser']

        results.sort(key=lambda r: sort_key(r))
        return results

    def start(self):
        self.set_guess_deadline()

        self.start_call = self.slack_client.api_call(
            'chat.postMessage',
            channel=self.channel_id,
            text='',
            blocks=self.board)

        self.thread_update_regularly = threading.Thread(
            target=self.update_regularly)
        self.thread_update_regularly.daemon = True
        self.thread_update_regularly.start()

        self.is_started = True

    def update(self):
        is_result_stage = self.stage == 'result_stage'

        self.slack_client.api_call(
            'chat.update',
            channel=self.channel_id,
            ts=self.start_call['ts'],
            text='',
            blocks=self.board)

        if is_result_stage and not self.is_over:
            self.is_over = True

    def update_regularly(self):
        while True:
            self.update()

            if not self.has_set_potential_guessers:
                self.potential_guessers = set(get_channel_non_bot_members(
                    self.slack_client, self.channel_id)) - {self.organizer_id}
                self.has_set_potential_guessers = True

            is_vote_stage = self.stage == 'vote_stage'
            if is_vote_stage and not self.has_sent_vote_reminders:
                self.send_vote_reminders()
                self.has_sent_vote_reminders = True

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
            self.slack_client.api_call(
                'chat.postMessage',
                channel=u,
                text="{} \n It's time to vote!".format(self.question),
                as_user=True)

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
