import time
import io
import threading
import random
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime
from collections import OrderedDict
from copy import deepcopy
from google.cloud import storage
from bluffer.utils import *


class Game:
    def __init__(self,
                 question, truth,
                 time_to_guess, time_to_vote,
                 will_send_vote_reminders,
                 game_id, app_id,
                 slack_client):

        self.question = question
        self.truth = truth
        self.time_to_guess = time_to_guess
        self.time_to_vote = time_to_vote
        self.will_send_vote_reminders = will_send_vote_reminders
        self.id = game_id
        self.app_id = app_id
        self.slack_client = slack_client

        self.channel_id = ids.game_id_to_channel_id(game_id)
        self.organizer_id = ids.game_id_to_organizer_id(game_id)

        self.title_block = blocks.build_title_block(self.organizer_id)
        self.pre_guess_stage_block = blocks.build_pre_guess_stage_block()

        self.stage = 'pre_guess_stage'

        self.start_call = None

        self.guess_deadline = None
        self.vote_deadline = None

        self.guesses = OrderedDict()
        self.votes = OrderedDict()
        self.signed_proposals = None
        self.truth_index = None
        self.timestamps_of_vote_reminders = None
        self.results = None
        self.graph = None
        self.graph_url = None

        self.potential_guessers = None

        self.vote_view_id = None

        self.pre_vote_stage_block = None
        self.pre_results_stage_block = None
        self.question_block = None
        self.guess_button_block = None
        self.vote_button_block = None
        self.anonymous_proposals_block = None
        self.truth_block = None
        self.results_block = None
        self.winners_block = None
        self.graph_block = None

        self.guess_view = None

        self.graph_basename = 'graph_{}.png'.format(self.id)

        self.thread_update_regularly = threading.Thread(
            target=self.update_regularly)
        self.thread_update_regularly.daemon = True
        self.thread_update_regularly.start()

    def update_regularly(self):
        while True:
            start = datetime.now()
            post_action = self.update()
            end = datetime.now()
            if post_action == 'sleep':
                delta = (end - start).total_seconds()
                if delta < 5:
                    time.sleep(5-delta)

    def update(self):

        if self.stage == 'pre_guess_stage':
            self.start_call = self.slack_client.api_call(
                'chat.postMessage',
                channel=self.channel_id,
                blocks=self.board)
            self.question_block = blocks.build_text_block(self.question)
            self.guess_button_block = self.build_guess_button_block()
            self.guess_view = self.build_guess_view()
            self.guess_deadline = timer.compute_deadline(self.time_to_guess)
            self.potential_guessers = members.get_potential_guessers(
                self.slack_client, self.channel_id, self.organizer_id)
            self.stage = 'guess_stage'
            return

        if self.stage == 'guess_stage':
            self.update_board()
            c1 = self.time_left_to_guess > 0
            c2 = self.remaining_potential_guessers
            if not(c1 and c2):
                self.pre_vote_stage_block = \
                    blocks.build_pre_vote_stage_block()
                self.stage = 'pre_vote_stage'
            return 'sleep'

        if self.stage == 'pre_vote_stage':
            self.update_board()
            self.vote_view_id = self.build_vote_view_id()
            self.signed_proposals = self.build_signed_proposals()
            self.anonymous_proposals_block = \
                self.build_anonymous_proposals_block()
            self.vote_button_block = self.build_vote_button_block()
            self.vote_deadline = timer.compute_deadline(self.time_to_vote)
            if self.will_send_vote_reminders:
                self.send_vote_reminders()
            self.stage = 'vote_stage'
            return

        if self.stage == 'vote_stage':
            self.update_board()
            c1 = self.time_left_to_vote > 0
            c2 = self.remaining_potential_voters
            if not(c1 and c2):
                self.pre_results_stage_block = \
                    blocks.build_pre_results_stage_block()
                self.stage = 'pre_results_stage'
            return 'sleep'

        if self.stage == 'pre_results_stage':
            self.update_board()
            self.truth_index = self.compute_truth_index()
            self.results = self.build_results()
            self.graph = self.build_graph()
            self.graph_url = self.upload_graph()
            self.truth_block = self.build_truth_block()
            self.results_block = self.build_results_block()
            if self.guessers:
                self.winners_block = self.build_winners_block()
                self.graph_block = self.build_graph_block()
            self.stage = 'results_stage'
            return

        if self.stage == 'results_stage':
            self.update_board()
            self.stage = 'over'
            return

        if self.stage == 'over':
            return

    def update_board(self):
        self.slack_client.api_call(
            'chat.update',
            channel=self.channel_id,
            ts=self.start_call['ts'],
            blocks=self.board)

    @property
    def board(self):

        if self.stage == 'pre_guess_stage':
            return [blocks.divider_block,
                    self.title_block,
                    self.pre_guess_stage_block,
                    blocks.divider_block]

        if self.stage == 'guess_stage':
            return [blocks.divider_block,
                    self.title_block,
                    self.question_block,
                    self.guess_button_block,
                    self.guess_timer_block,
                    self.guessers_block,
                    blocks.divider_block]

        if self.stage == 'pre_vote_stage':
            return [blocks.divider_block,
                    self.title_block,
                    self.question_block,
                    self.guessers_block,
                    self.pre_vote_stage_block,
                    blocks.divider_block]

        if self.stage == 'vote_stage':
            return [blocks.divider_block,
                    self.title_block,
                    self.question_block,
                    self.guessers_block,
                    self.vote_button_block,
                    self.vote_timer_block,
                    self.voters_block,
                    blocks.divider_block]

        if self.stage == 'pre_results_stage':
            return [blocks.divider_block,
                    self.title_block,
                    self.question_block,
                    self.guessers_block,
                    self.voters_block,
                    self.anonymous_proposals_block,
                    self.pre_results_stage_block,
                    blocks.divider_block]

        if self.stage == 'results_stage':
            if not self.guessers:
                return [blocks.divider_block,
                        self.title_block,
                        self.question_block,
                        self.truth_block,
                        self.results_block,
                        blocks.divider_block]
            else:
                return [blocks.divider_block,
                        self.title_block,
                        self.question_block,
                        self.truth_block,
                        self.results_block,
                        self.winners_block,
                        self.graph_block,
                        blocks.divider_block]

    def build_slack_object_id(self, object_name):
        return ids.build_slack_object_id(self.app_id, object_name, self.id)

    def build_guess_button_block_id(self):
        return self.build_slack_object_id('guess_button_block')

    def build_vote_button_block_id(self):
        return self.build_slack_object_id('vote_button_block')

    def build_guess_view_id(self):
        return self.build_slack_object_id('guess_view')

    def build_vote_view_id(self):
        return self.build_slack_object_id('vote_view')

    @property
    def guess_timer_block(self):
        msg = 'Time left to guess: {}'.format(
            timer.build_time_display(self.time_left_to_guess))
        return blocks.build_text_block(msg)

    @property
    def vote_timer_block(self):
        msg = 'Time left to vote: {}'.format(
            timer.build_time_display(self.time_left_to_vote))
        return blocks.build_text_block(msg)

    @property
    def guessers_block(self):
        if not self.guessers:
            return blocks.build_text_block('No one has guessed yet.')
        guessers_for_display = ids.user_displays(self.guessers)
        msg = 'Guessers: {}'.format(guessers_for_display)
        return blocks.build_text_block(msg)

    @property
    def voters_block(self):
        if not self.voters:
            return blocks.build_text_block('No one has voted yet.')
        voters_for_display = ids.user_displays(self.voters)
        msg = 'Voters: {}'.format(voters_for_display)
        return blocks.build_text_block(msg)

    def build_guess_button_block(self):
        msg = 'Your guess'
        id_ = self.build_guess_button_block_id()
        return blocks.build_button_block(msg,  id_)

    def build_vote_button_block(self):
        msg = 'Your vote'
        id_ = self.build_vote_button_block_id()
        return blocks.build_button_block(msg,  id_)

    def build_anonymous_proposals_block(self):
        msg = ['Proposals:']
        for index, author, proposal in self.signed_proposals:
            msg.append('{}) {}'.format(index, proposal))
        msg = '\n'.join(msg)
        return blocks.build_text_block(msg)

    def build_own_guess_block(self, voter):
        index = self.author_to_index(voter)
        guess = self.author_to_proposal(voter)
        msg = 'Your guess is: {}) {}'.format(index, guess)
        return blocks.build_text_block(msg)

    def build_truth_block(self):
        index = self.truth_index
        msg = 'Truth: {}) {}'.format(index, self.truth)
        return blocks.build_text_block(msg)

    def build_results_block(self):
        msg = self.build_results_msg()
        return blocks.build_text_block(msg)

    def build_winners_block(self):
        msg = self.build_winners_msg()
        return blocks.build_text_block(msg)

    def build_graph_block(self):
        return blocks.build_image_block(url=self.graph_url,
                                        alt_text='Voting graph')

    def build_results_msg(self):
        if not self.guessers:
            return 'No one played this game :sob:.'
        msg = ['Scores:']
        for r in deepcopy(self.results):
            player = r['guesser']
            index = r['index']
            guess = r['guess']
            r_msg = '• {} wrote {}) {}'.format(
                ids.user_display(player), index, guess)
            if player in self.voters:
                if r['chosen_author'] == 'Truth':
                    voted_for = 'the truth'
                else:
                    voted_for = ids.user_display(r['chosen_author'])
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
        return msg

    def build_winners_msg(self):
        winners = self.compute_winners()
        if not self.voters:
            return 'No one voted :sob:.'
        if len(self.voters) == 1:
            r = self.results[0]
            g = ids.user_display(r['guesser'])
            ca = r['chosen_author']
            if set(self.guessers) == set(self.voters):
                assert ca == 'Truth'
                msg = ("Thank you for your vote {}! :pray:".format(g))
                return msg
            if ca == 'Truth':
                msg = ('Bravo {}! You found the truth! :v:'.format(g))
                return msg
            else:
                msg = 'Hey {}, at least you voted! :grimacing:'.format(g)
                return msg
        if len(winners) == len(self.voters):
            return "Well, it's a draw between the voters! :scales:"
        if len(winners) == 1:
            w = ids.user_display(winners[0])
            return "And the winner is {}! :first_place_medal:".format(w)
        if len(winners) > 1:
            ws = [ids.user_display(w) for w in winners]
            msg_aux = ','.join(ws[:-1])
            msg_aux += ' and {}'.format(ws[-1])
            return "And the winners are {}! :clap:".format(msg_aux)

    def build_guess_view(self):
        res = deepcopy(views.guess_view_template)
        res['callback_id'] = self.build_guess_view_id()
        input_block = deepcopy(res['blocks'][0])
        res['blocks'] = [self.question_block, input_block]
        return res

    def build_vote_view(self, voter):
        res = deepcopy(views.vote_view_template)
        res['callback_id'] = self.vote_view_id
        input_block_template = res['blocks'][0]
        option_template = input_block_template['element']['options'][0]
        vote_options = []
        for index, guess in self.build_votable_proposals(voter):
            vote_option = deepcopy(option_template)
            vote_option['text']['text'] = '{}) {}'.format(index, guess)
            vote_option['value'] = '{}'.format(index)
            vote_options.append(vote_option)
        input_block = input_block_template
        input_block['element']['options'] = vote_options
        res['blocks'] = [self.build_own_guess_block(voter), input_block]
        return res

    @property
    def time_left_to_guess(self):
        return timer.compute_time_left(self.guess_deadline)

    @property
    def time_left_to_vote(self):
        return timer.compute_time_left(self.vote_deadline)

    @property
    def guessers(self):
        return self.guesses.keys()

    @property
    def voters(self):
        return self.votes.keys()

    @property
    def remaining_potential_guessers(self):
        return set(self.potential_guessers) - set(self.guessers)

    @property
    def potential_voters(self):
        return set(self.guessers)

    @property
    def remaining_potential_voters(self):
        return self.potential_voters - set(self.voters)

    @property
    def is_over(self):
        return self.stage == 'over'

    def open_view(self, trigger_id, view):
        views.open_view(self.slack_client, trigger_id, view)

    def open_guess_view(self, trigger_id):
        self.open_view(trigger_id, self.guess_view)

    def open_vote_view(self, trigger_id, voter):
        view = self.build_vote_view(voter)
        self.open_view(trigger_id, view)

    def send_vote_reminders(self):
        for u in self.guessers:
            msg = ("Hey {}, you can now vote in the bluffer game organized "
                   "by {}. You have {} left. Will you find the truth? :mag:"
                   .format(ids.user_display(u),
                           ids.user_display(self.organizer_id),
                           timer.build_time_display(self.time_to_vote)))
            self.slack_client.api_call(
                'chat.postEphemeral',
                channel=self.channel_id,
                user=u,
                text=msg)

    def build_signed_proposals(self):
        res = list(self.guesses.items()) + [('Truth', self.truth)]
        random.shuffle(res)
        res = [(index, author, proposal)
               for index, (author, proposal) in enumerate(res, 1)]
        return res

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

    def get_guesser_name(self, guesser):
        return self.potential_guessers[guesser]

    def build_votable_proposals(self, voter):
        res = []
        for index, author, proposal in self.signed_proposals:
            if author != voter:
                res.append((index, proposal))
        return res

    def compute_truth_index(self):
        return self.author_to_index('Truth')

    def compute_truth_score(self, voter):
        return int(self.votes[voter] == self.author_to_index('Truth'))

    def compute_bluff_score(self, voter):
        res = 0
        for voter_ in self.votes.keys():
            voter_index = self.author_to_index(voter)
            if self.votes[voter_] == voter_index:
                res += 2
        return res

    def compute_max_score(self):
        scores = [r['score'] for r in self.results if 'score' in r]
        return scores[0]

    def build_results(self):
        results = []
        for index, author, proposal in self.signed_proposals:
            r = dict()
            if author == 'Truth':
                continue
            r['index'] = index
            r['guesser'] = author
            r['guesser_name'] = self.get_guesser_name(author)
            r['guess'] = proposal
            if author not in self.voters:
                r['score'] = 0
                results.append(r)
                continue
            vote_index = self.votes[author]
            r['vote_index'] = vote_index
            r['chosen_author'] = self.index_to_author(vote_index)
            r['chosen_proposal'] = self.index_to_proposal(vote_index)
            r['truth_score'] = self.compute_truth_score(author)
            r['bluff_score'] = self.compute_bluff_score(author)
            r['score'] = r['truth_score'] + r['bluff_score']
            results.append(r)

        def sort_key(r_):
            return 'vote_index' not in r_, -r_['score'], r_['guesser']

        results.sort(key=lambda r_: sort_key(r_))

        return results

    def compute_winners(self):
        max_score = self.compute_max_score()
        res = []
        for r in self.results:
            if r['score'] == max_score:
                res.append(r['guesser'])
        return res

    def build_graph(self):
        res = nx.DiGraph()
        res.add_node(self.truth_index)
        for r in self.results:
            res.add_node(r['index'])
            if 'vote_index' in r:
                res.add_edge(r['index'], r['vote_index'])
        return res

    def upload_graph(self):
        g = self.graph

        plt.figure(figsize=(6, 6))

        plt.title('Voting graph')
        pos = nx.spring_layout(g)

        nx.draw_networkx_nodes(g, pos, node_color='#cc66ff', alpha=0.3,
                               node_size=1000)

        nx.draw_networkx_edges(g, pos, alpha=1.0, arrows=True, width=1.0)

        truth_label = {self.truth_index: '{}) Truth'.format(self.truth_index)}
        nx.draw_networkx_labels(g, pos, labels=truth_label, font_color='r')

        guesser_labels = {r['index']: '{}) {}'.format(r['index'],
                                                      r['guesser_name'])
                          for r in self.results}
        nx.draw_networkx_labels(g, pos, labels=guesser_labels, font_color='b')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')

        client = storage.Client()
        bucket = client.bucket('bucket_bluffer')
        blob = bucket.blob(self.graph_basename)

        blob.upload_from_string(
            buf.getvalue(),
            content_type='image/png')

        buf.close()

        return blob.public_url
