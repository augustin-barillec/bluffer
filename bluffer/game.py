import time
import os
import threading
import logging
import random
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime
from collections import OrderedDict
from copy import deepcopy
from fpdf import FPDF
from apiclient import http
from bluffer.utils import *


logger = logging.getLogger(__name__)


class Game:
    def __init__(self,
                 question, truth,
                 time_to_guess, time_to_vote,
                 game_id, secret_prefix,
                 bucket_dir_name,
                 drive_dir_id,
                 local_dir_path,
                 slack_client,
                 bucket,
                 drive_service):

        self.question = question
        self.truth = truth
        self.time_to_guess = time_to_guess
        self.time_to_vote = time_to_vote
        self.id = game_id
        self.secret_prefix = secret_prefix
        self.bucket_dir_name = bucket_dir_name
        self.drive_dir_id = drive_dir_id
        self.local_dir_path = local_dir_path
        self.slack_client = slack_client
        self.bucket = bucket
        self.drive_service = drive_service

        self.channel_id = ids.game_id_to_channel_id(game_id)
        self.organizer_id = ids.game_id_to_organizer_id(game_id)

        self.title_block = blocks.build_title_block(self.organizer_id)
        self.pre_guess_stage_block = blocks.build_pre_guess_stage_block()

        self.stage = 'pre_guess_stage'

        self.upper_ts = None
        self.lower_ts = None

        self.start_datetime = datetime.now()
        self.guess_deadline = None
        self.vote_deadline = None

        self.guesses = OrderedDict()
        self.votes = OrderedDict()
        self.signed_proposals = None
        self.truth_index = None
        self.results = None
        self.max_score = None
        self.winners = None
        self.graph = None

        self.potential_guessers = None

        self.vote_view_id = None

        self.pre_vote_stage_block = None
        self.pre_results_stage_block = None
        self.question_block = None
        self.guess_button_block = None
        self.vote_button_block = None
        self.anonymous_proposals_block = None
        self.truth_block = None
        self.signed_guesses_block = None
        self.conclusion_block = None
        self.graph_block = None

        self.guess_view = None

        self.graph_basename = None
        self.report_basename = None
        self.graph_local_path = None
        self.report_local_path = None
        self.graph_url = None

        self.thread_update_regularly = threading.Thread(
            target=self.update_regularly)
        self.thread_update_regularly.daemon = True
        self.thread_update_regularly.start()

    def update_regularly(self):
        while self.stage != 'over':
            start = datetime.now()
            post_action = self.update()
            end = datetime.now()
            if post_action == 'sleep':
                delta = (end - start).total_seconds()
                if delta < 5:
                    time.sleep(5 - delta)

    def update(self):

        if self.stage == 'pre_guess_stage':
            self.upper_ts = self.post_board('upper')
            self.lower_ts = self.post_board('lower')
            self.question_block = blocks.build_text_block(self.question)
            self.guess_button_block = self.build_guess_button_block()
            self.guess_view = self.build_guess_view()
            self.start_datetime = datetime.now()
            self.guess_deadline = timer.compute_deadline(
                self.start_datetime, self.time_to_guess)
            self.potential_guessers = members.get_potential_guessers(
                self.slack_client, self.channel_id, self.organizer_id)
            self.stage = 'guess_stage'
            self.update_board('all')
            return

        if self.stage == 'guess_stage':
            self.update_board('lower')
            c1 = self.time_left_to_guess > 0
            c2 = self.remaining_potential_guessers
            if not(c1 and c2):
                self.pre_vote_stage_block = \
                    blocks.build_pre_vote_stage_block()
                self.stage = 'pre_vote_stage'
                self.update_board('all')
            return 'sleep'

        if self.stage == 'pre_vote_stage':
            self.signed_proposals = self.build_signed_proposals()
            self.anonymous_proposals_block = \
                self.build_anonymous_proposals_block()
            self.vote_view_id = self.build_vote_view_id()
            self.vote_button_block = self.build_vote_button_block()
            self.vote_deadline = timer.compute_deadline(
                datetime.now(), self.time_to_vote)
            self.stage = 'vote_stage'
            self.update_board('all')
            if len(self.guessers) > 1:
                self.send_vote_reminders()
            return

        if self.stage == 'vote_stage':
            self.update_board('lower')
            c1 = self.time_left_to_vote > 0
            c2 = self.remaining_potential_voters
            c3 = len(self.guessers) > 1
            if not(c1 and c2 and c3):
                self.pre_results_stage_block = \
                    blocks.build_pre_results_stage_block()
                self.stage = 'pre_results_stage'
                self.update_board('all')
            return 'sleep'

        if self.stage == 'pre_results_stage':
            self.truth_index = self.compute_truth_index()
            self.truth_block = self.build_truth_block()
            self.results = self.build_results()
            logger.info(str(self.results))
            self.signed_guesses_block = self.build_signed_guesses_block()
            if len(self.guessers) > 1:
                self.max_score = self.compute_max_score()
                self.winners = self.compute_winners()
                self.graph = self.build_graph()
                self.graph_basename = self.compute_graph_basename()
                self.graph_local_path = self.compute_graph_local_path()
                self.report_basename = self.compute_report_basename()
                self.report_local_path = self.compute_report_local_path()
                self.draw_graph()
                self.graph_url = self.upload_graph_to_gs()
                try:
                    self.build_report()
                    self.upload_report_to_gs()
                    self.upload_report_to_drive()
                    os.remove(self.report_local_path)
                except IndexError:
                    logger.warning('Unable to build report')
                os.remove(self.graph_local_path)
                self.graph_block = self.build_graph_block()
            self.conclusion_block = self.build_conclusion_block()
            self.stage = 'results_stage'
            self.update_board('all')
            self.send_game_over_notifications()
            return

        if self.stage == 'results_stage':
            self.stage = 'over'
            return

        if self.stage == 'over':
            return

    def post_board(self, part):
        return self.slack_client.api_call(
            'chat.postMessage',
            channel=self.channel_id,
            blocks=getattr(self, part + '_board'))['ts']

    def update_board(self, part):
        if part == 'all':
            self.update_board('upper')
            self.update_board('lower')
            return
        self.slack_client.api_call(
            'chat.update',
            channel=self.channel_id,
            ts=getattr(self, part + '_ts'),
            blocks=getattr(self, part + '_board'))

    @property
    def upper_board(self):

        if self.stage == 'pre_guess_stage':
            return [blocks.divider_block,
                    self.title_block,
                    self.pre_guess_stage_block]

        if self.stage == 'guess_stage':
            return [blocks.divider_block,
                    self.title_block,
                    self.question_block,
                    self.guess_button_block]

        if self.stage == 'pre_vote_stage':
            return [blocks.divider_block,
                    self.title_block,
                    self.question_block,
                    self.guessers_block,
                    self.pre_vote_stage_block]

        if self.stage == 'vote_stage':
            return [blocks.divider_block,
                    self.title_block,
                    self.question_block,
                    self.anonymous_proposals_block,
                    self.vote_button_block]

        if self.stage == 'pre_results_stage':
            lg = len(self.guessers)
            res = [blocks.divider_block,
                   self.title_block,
                   self.question_block]
            if lg > 0:
                res.append(self.anonymous_proposals_block)
            if lg > 1:
                res += [self.remaining_potential_voters_block,
                        self.voters_block]
            res.append(self.pre_results_stage_block)
            return res

        if self.stage == 'results_stage':
            lg = len(self.guessers)
            res = [blocks.divider_block,
                   self.title_block,
                   self.question_block,
                   self.truth_block]
            if lg > 0:
                res.append(self.signed_guesses_block)
            if lg > 1:
                res.append(self.graph_block)
            res.append(self.conclusion_block)
            return res

    @property
    def lower_board(self):

        if self.stage == 'pre_guess_stage':
            return [blocks.divider_block]

        if self.stage == 'guess_stage':
            return [self.guess_timer_block,
                    self.guessers_block,
                    blocks.divider_block]

        if self.stage == 'pre_vote_stage':
            return [blocks.divider_block]

        if self.stage == 'vote_stage':
            return [self.vote_timer_block,
                    self.remaining_potential_voters_block,
                    self.voters_block,
                    blocks.divider_block]

        if self.stage == 'pre_results_stage':
            return [blocks.divider_block]

        if self.stage == 'results_stage':
            return [blocks.divider_block]

    def build_slack_object_id(self, object_name):
        return ids.build_slack_object_id(self.secret_prefix,
                                         object_name, self.id)

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

    @property
    def remaining_potential_voters_block(self):
        if not self.remaining_potential_voters:
            return blocks.build_text_block('Everyone has voted!')
        rpv_for_display = ids.user_displays(
            sorted(self.remaining_potential_voters))
        msg = 'Potential voters: {}'.format(rpv_for_display)
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
        msg = 'Your guess: {}) {}'.format(index, guess)
        return blocks.build_text_block(msg)

    def build_truth_block(self):
        msg = '• Truth: '
        if len(self.guessers) == 0:
            msg += '{}'.format(self.truth)
        else:
            index = self.truth_index
            msg += '{}) {}'.format(index, self.truth)
        return blocks.build_text_block(msg)

    def build_signed_guesses_block(self):
        msg = self.build_signed_guesses_msg('slack')
        return blocks.build_text_block(msg)

    def build_conclusion_block(self):
        msg = self.build_conclusion_msg('slack')
        return blocks.build_text_block(msg)

    def build_graph_block(self):
        return blocks.build_image_block(url=self.graph_url,
                                        alt_text='Voting graph')

    def build_signed_guesses_msg(self, fmt):
        assert fmt in ('slack', 'pdf')
        msg = []
        lg = len(self.guessers)
        for r in deepcopy(self.results):
            if fmt == 'slack':
                player = ids.user_display(r['guesser'])
            else:
                player = r['guesser_name']
            score = r['score']
            p = r['p']
            index = r['index']
            guess = r['guess']
            if lg > 1:
                r_msg = '• {} [{} {}]: {}) {}'.format(
                    player, score, p, index, guess)
            else:
                r_msg = '• {}: {}) {}'.format(player, index, guess)
            msg.append(r_msg)
        msg = '\n'.join(msg)
        return msg

    def build_conclusion_msg(self, fmt):
        assert fmt in ('slack', 'pdf')
        lg = len(self.guessers)
        lv = len(self.voters)
        if lg == 0:
            return 'No one played this game :sob:.'
        if lg == 1:
            g = ids.user_display(self.guessers[0])
            return 'Thanks for your guess, {}!'.format(g)
        if lv == 0:
            res = 'No one voted'
            if fmt == 'slack':
                res += ' :sob:.'
                return res
            else:
                res += ' :/.'
                return res
        if lv == 1:
            r = self.results[0]
            if fmt == 'slack':
                g = ids.user_display(r['guesser'])
            else:
                g = r['guesser_name']
            ca = r['chosen_author']
            if ca == 'Truth':
                msg = 'Bravo {}! You found the truth!'.format(g)
                if fmt == 'slack':
                    msg += ' :v:'
                else:
                    msg += ' :)'
                return msg
            else:
                msg = 'Hey {}, at least you voted!'.format(g)
                if fmt == 'slack':
                    msg += ' :grimacing:'
                else:
                    msg += ' :|'
                return msg
        if self.max_score == 0:
            return 'Zero points scored!'
        lw = len(self.winners)
        if lw == lv:
            msg = "Well, it's a draw!"
            if fmt == 'slack':
                msg += ' :scales:'
            return msg
        if lw == 1:
            if fmt == 'slack':
                w = ids.user_display(self.winners[0])
                emoji = ' :first_place_medal:'
            else:
                w = self.get_guesser_name(self.winners[0])
                emoji = ''
            return 'And the winner is {}!{}'.format(w, emoji)
        if lw > 1:
            if fmt == 'slack':
                ws = [ids.user_display(w) for w in self.winners]
                emoji = ' :clap:'
            else:
                ws = [self.get_guesser_name(w) for w in self.winners]
                emoji = ''
            msg_aux = ','.join(ws[:-1])
            msg_aux += ' and {}'.format(ws[-1])
            return 'And the winners are {}!{}'.format(msg_aux, emoji)

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
        votable_proposals_msg = ['Voting options:']
        option_template = input_block_template['element']['options'][0]
        vote_options = []
        for index, proposal in self.build_votable_proposals(voter):
            votable_proposals_msg.append('{}) {}'.format(index, proposal))
            vote_option = deepcopy(option_template)
            vote_option['text']['text'] = '{}'.format(index)
            vote_option['value'] = '{}'.format(index)
            vote_options.append(vote_option)
        votable_proposals_msg = '\n'.join(votable_proposals_msg)
        input_block = input_block_template
        input_block['element']['options'] = vote_options
        res['blocks'] = [self.build_own_guess_block(voter),
                         blocks.build_text_block(votable_proposals_msg),
                         input_block]
        return res

    @property
    def time_left_to_guess(self):
        return timer.compute_time_left(self.guess_deadline)

    @property
    def time_left_to_vote(self):
        return timer.compute_time_left(self.vote_deadline)

    @property
    def guessers(self):
        if self.results is None:
            return self.guesses.keys()
        else:
            return [r['guesser'] for r in self.results]

    @property
    def voters(self):
        if self.results is None:
            return self.votes.keys()
        else:
            return [r['guesser'] for r in self.results if 'vote_index' in r]

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
            msg = ('Hey {}, you can now vote in the bluffer game organized '
                   'by {}!'
                   .format(ids.user_display(u),
                           ids.user_display(self.organizer_id),
                           timer.build_time_display(self.time_to_vote)))
            self.slack_client.api_call(
                'chat.postEphemeral',
                channel=self.channel_id,
                user=u,
                text=msg)

    def send_game_over_notifications(self):
        for u in self.guessers:
            msg = ("The bluffer game organized by {} is over!"
                   .format(ids.user_display(self.organizer_id)))
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
                r['p'] = 'points'
                results.append(r)
                continue
            vote_index = self.votes[author]
            r['vote_index'] = vote_index
            r['chosen_author'] = self.index_to_author(vote_index)
            r['truth_score'] = self.compute_truth_score(author)
            r['bluff_score'] = self.compute_bluff_score(author)
            r['score'] = r['truth_score'] + r['bluff_score']
            if r['score'] == 1:
                r['p'] = 'point'
            else:
                r['p'] = 'points'
            results.append(r)

        def sort_key(r_):
            return 'vote_index' not in r_, -r_['score'], r_['guesser']

        results.sort(key=lambda r_: sort_key(r_))

        return results

    def compute_winners(self):
        res = []
        for r in self.results:
            if r['score'] == self.max_score:
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

    def draw_graph(self):
        g = self.graph

        side_length = int(len(self.guessers)/2) + 7

        plt.figure(figsize=(side_length, side_length))

        plt.title('Voting graph')
        pos = nx.circular_layout(g)

        nx.draw_networkx_nodes(g, pos, node_color='#cc66ff', alpha=0.3,
                               node_size=1000)

        nx.draw_networkx_edges(g, pos, alpha=1.0, arrows=True, width=1.0)

        truth_label = {self.truth_index: 'Truth'}
        nx.draw_networkx_labels(g, pos, labels=truth_label, font_color='r')

        guesser_labels = {r['index']: '{}'.format(r['guesser_name'])
                          for r in self.results}

        indexes_of_winners = set(r['index'] for r in self.results
                                 if r['guesser'] in self.winners)
        indexes_of_losers = set(r['index'] for r in self.results
                                if r['guesser'] not in self.winners)

        winner_labels = {k: guesser_labels[k] for k in indexes_of_winners}
        loser_labels = {k: guesser_labels[k] for k in indexes_of_losers}

        nx.draw_networkx_labels(g, pos, labels=loser_labels, font_color='b')
        nx.draw_networkx_labels(g, pos, labels=winner_labels, font_color='g')

        plt.savefig(self.graph_local_path)

    def build_report(self):
        pdf = FPDF('L')
        pdf.add_page()

        pdf.image(self.graph_local_path, x=158.5, y=40, w=119, h=119)

        font_family = fonts.get_font_family()
        font_path = fonts.get_font_path()

        pdf.add_font(font_family, '', font_path, uni=True)
        pdf.set_right_margin(148.5)

        organizer_name = members.user_id_to_user_name(
            self.slack_client, self.organizer_id)
        title = 'Game set up by {}'.format(organizer_name)

        pdf.set_font(font_family, '', 14)
        pdf.write(8, title)
        pdf.write(8, '\n\n')

        pdf.set_font(font_family, '', 24)
        pdf.write(11, self.question)
        pdf.write(11, '\n\n')

        pdf.set_font(font_family, '', 14)
        msg = ['Truth: {}'.format(self.truth),
               self.build_signed_guesses_msg('pdf'),
               self.build_conclusion_msg('pdf')]

        msg = '\n\n'.join(msg)

        pdf.write(8, msg)

        pdf.output(self.report_local_path, 'F')

    def upload_to_gs(self, local_file_path, sub_dir_name):
        assert sub_dir_name in ('graphs', 'reports')
        basename = os.path.basename(local_file_path)

        blob_name = '{}/{}/{}'.format(
            self.bucket_dir_name, sub_dir_name, basename)

        blob = self.bucket.blob(blob_name)

        blob.upload_from_filename(local_file_path)

        return blob.public_url

    def upload_graph_to_gs(self):
        return self.upload_to_gs(self.graph_local_path, 'graphs')

    def upload_report_to_gs(self):
        return self.upload_to_gs(self.report_local_path, 'reports')

    def upload_report_to_drive(self):

        file_metadata = {'name': self.start_datetime.strftime('%Y%m%d_%H%M%S'),
                         'parents': [self.drive_dir_id]}
        media = http.MediaFileUpload(self.report_local_path,
                                     mimetype='application/pdf')
        self.drive_service.files().create(
            body=file_metadata,
            media_body=media).execute()

    def compute_basename(self, core_name, ext):
        return '{}_{}_{}.{}'.format(
                    self.start_datetime.strftime('%Y%m%d_%H%M%S'),
                    core_name, self.id, ext)

    def compute_graph_basename(self):
        return self.compute_basename('graph', 'png')

    def compute_report_basename(self):
        return self.compute_basename('report', 'pdf')

    def compute_local_path(self, basename):
        return self.local_dir_path + '/' + basename

    def compute_graph_local_path(self):
        return self.compute_local_path(self.graph_basename)

    def compute_report_local_path(self):
        return self.compute_local_path(self.report_basename)
