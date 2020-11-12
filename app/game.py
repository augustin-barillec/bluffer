import os
import random
import networkx as nx
import matplotlib.pyplot as plt
from copy import deepcopy
from slackclient import SlackClient
from app.utils import blocks, firestore, ids, slack, pubsub, time, views


class Version:

    version_latest = 1
    version = None


class Question:

    question = None


class Truth:

    truth = None
    truth_index = None


class Guessers:

    potential_guessers = None
    guessers = None
    frozen_guessers = None

    def get_guesser_name(self, guesser):
        return self.potential_guessers[guesser]

    def compute_remaining_potential_guessers(self):
        return {pv: self.potential_guessers[pv]
                for pv in self.potential_guessers
                if pv not in self.guessers}


class Voters:

    potential_voters = None
    voters = None
    frozen_voters = None

    def compute_remaining_potential_voters(self):
        return {pv: self.potential_voters[pv]
                for pv in self.potential_voters
                if pv not in self.voters}


class Ids:

    secret_prefix = None
    id = None
    code = None
    team_id = None
    organizer_id = None
    channel_id = None

    def get_team_id(self):
        return ids.game_id_to_team_id(self.id)

    def get_organizer_id(self):
        return ids.game_id_to_organizer_id(self.id)

    def get_channel_id(self):
        return ids.game_id_to_channel_id(self.id)

    def build_code(self):
        return self.id.encode("utf-8")

    def build_slack_object_id(self, object_name):
        return ids.build_slack_object_id(self.secret_prefix,
                                         object_name, self.id)

    def build_setup_view_id(self):
        return self.build_slack_object_id('game_setup_view')

    def build_guess_view_id(self):
        return self.build_slack_object_id('guess_view')

    def build_vote_view_id(self):
        return self.build_slack_object_id('vote_view')

    def build_guess_button_block_id(self):
        return self.build_slack_object_id('guess_button_block')

    def build_vote_button_block_id(self):
        return self.build_slack_object_id('vote_button_block')


class Proposals(Ids, Truth, Guessers):

    indexed_signed_proposals = None

    @staticmethod
    def sort_users(users):
        res = sorted(users, key=lambda k: users[k][0])
        return res

    def build_indexed_signed_proposals(self):
        sorted_frozen_guessers = self.sort_users(self.frozen_guessers)
        res = [(k, self.frozen_guessers[k][1]) for k in sorted_frozen_guessers]
        res.append(('Truth', self.truth))
        random.seed(self.id)
        random.shuffle(res)
        res = [(index, author, proposal)
               for index, (author, proposal) in enumerate(res, 1)]
        res = [{'index': index, 'author': author, 'proposal': proposal}
               for index, author, proposal in res]
        return res

    def index_to_author(self, index):
        for isp in self.indexed_signed_proposals:
            if isp['index'] == index:
                return isp['author']

    def author_to_index(self, author):
        for isp in self.indexed_signed_proposals:
            if isp['author'] == author:
                return isp['index']

    def author_to_proposal(self, author):
        for isp in self.indexed_signed_proposals:
            if isp['author'] == author:
                return isp['proposal']

    def build_own_indexed_guess(self, guesser):
        index = self.author_to_index(guesser)
        guess = self.author_to_proposal(guesser)
        return index, guess

    def build_votable_indexed_anonymous_proposals(self, voter):
        res = []
        for isp in self.indexed_signed_proposals:
            if isp['author'] != voter:
                res.append({'index': isp['index'],
                            'proposal': isp['proposal']})
        return res

    def build_indexed_anonymous_proposals(self):
        res = []
        for isp in self.indexed_signed_proposals:
            res.append({'index': isp['index'], 'proposal': isp['proposal']})
        return res

    def compute_truth_index(self):
        return self.author_to_index('Truth')


class Results(Proposals, Voters):

    results = None
    winners = None
    max_score = None

    def compute_truth_score(self, voter):
        return int(self.frozen_voters[voter][1] == self.truth_index)

    def compute_bluff_score(self, voter):
        res = 0
        for voter_ in self.frozen_voters:
            voter_index = self.author_to_index(voter)
            if self.frozen_voters[voter_][1] == voter_index:
                res += 2
        return res

    def build_results(self):
        results = []
        for isp in self.indexed_signed_proposals:
            index = isp['index']
            author = isp['author']
            proposal = isp['proposal']
            r = dict()
            if author == 'Truth':
                continue
            r['index'] = index
            r['guesser'] = author
            r['guesser_name'] = self.get_guesser_name(author)
            r['guess'] = proposal
            if author not in self.frozen_voters:
                r['score'] = 0
                results.append(r)
                continue
            vote_index = self.frozen_voters[author][1]
            r['vote_index'] = vote_index
            r['chosen_author'] = self.index_to_author(vote_index)
            r['truth_score'] = self.compute_truth_score(author)
            r['bluff_score'] = self.compute_bluff_score(author)
            r['score'] = r['truth_score'] + r['bluff_score']
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

    def compute_max_score(self):
        scores = [r['score'] for r in self.results if 'score' in r]
        return scores[0]


class Time(Ids):

    slash_command_compact = None

    setup_submission = None
    max_life_span = None

    time_to_guess = None
    time_to_vote = None

    upper_ts = None
    lower_ts = None

    guess_start = None
    vote_start = None

    guess_deadline = None
    vote_deadline = None

    def get_slash_command_compact(self):
        return ids.game_id_to_slash_command_compact(self.id)

    def compute_guess_deadline(self):
        return time.compute_deadline(self.guess_start, self.time_to_guess)

    def compute_vote_deadline(self):
        return time.compute_deadline(self.vote_start, self.time_to_vote)

    def compute_time_left_to_guess(self):
        return time.compute_time_left(self.guess_deadline)

    def compute_time_left_to_vote(self):
        return time.compute_time_left(self.vote_deadline)


class PubSub(Ids):

    project_id = None
    publisher = None

    pre_guess_stage_already_triggered = False
    pre_vote_stage_already_triggered = False
    pre_result_stage_already_triggered = False

    guess_stage_over = False
    vote_stage_over = False
    result_stage_over = False

    def build_topic_path(self, topic_name):
        return pubsub.build_topic_path(
            self.publisher, self.project_id, topic_name)

    def publish(self, topic_name):
        topic_path = self.build_topic_path(topic_name)
        self.publisher.publish(topic_path, data=self.code)

    def trigger_pre_guess_stage(self):
        self.publish('topic_pre_guess_stage')

    def trigger_guess_stage(self):
        self.publish('topic_guess_stage')

    def trigger_pre_vote_stage(self):
        self.publish('topic_pre_vote_stage')

    def trigger_vote_stage(self):
        self.publish('topic_vote_stage')

    def trigger_pre_result_stage(self):
        self.publish('topic_pre_result_stage')

    def trigger_result_stage(self):
        self.publish('topic_result_stage')


class Firestore(Ids):

    db = None

    team_dict = None
    dict = None
    ref = None

    def get_team_dict(self):
        return firestore.get_team_dict(self.db, self.team_id)

    def get_dict(self):
        return firestore.get_game_dict(self.db, self.team_id, self.id)

    def get_game_dicts(self):
        return firestore.get_game_dicts(self.db, self.team_id)

    def build_ref(self):
        return firestore.get_game_ref(self.db, self.team_id, self.id)

    def set_dict(self, merge=False):
        self.ref.set(self.dict, merge=merge)

    def delete(self):
        firestore.delete_game(self.db, self.team_id, self.id)


class Local(Ids):

    local_dir_path = None
    graph_local_path = None

    def build_basename(self, kind, ext):
        return '{}_{}.{}'.format(kind, self.id, ext)

    def build_local_file_path(self, basename):
        return self.local_dir_path + '/' + basename


class Storage:

    bucket = None
    bucket_dir_name = None

    def upload_to_gs(self, local_file_path):
        basename = os.path.basename(local_file_path)
        blob_name = '{}/{}'.format(self.bucket_dir_name, basename)
        blob = self.bucket.blob(blob_name)
        blob.upload_from_filename(local_file_path)
        return blob.public_url


class Graph(Local, Storage, Results):

    graph = None
    graph_local_path = None
    graph_url = None

    def build_graph_basename(self):
        return self.build_basename('graph', 'png')

    def build_graph_local_path(self):
        return self.build_local_file_path(self.build_graph_basename())

    def upload_graph_to_gs(self):
        return self.upload_to_gs(self.graph_local_path)

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

        side_length = int(len(self.frozen_guessers)/2) + 7

        plt.figure(figsize=(side_length, side_length))

        plt.title('Voting graph')
        pos = nx.circular_layout(g)

        nx.draw_networkx_nodes(g, pos, node_color='#cc66ff', alpha=0.3,
                               node_size=1000)

        nx.draw_networkx_edges(g, pos, alpha=1.0, arrows=True, width=1.0)

        truth_label = {self.truth_index: 'Truth'}
        nx.draw_networkx_labels(g, pos, labels=truth_label, font_color='r')

        guesser_labels = {r['index']: '{}\n{}'.format(r['guesser_name'],
                                                      r['score'])
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


class Blocks(Question, Time, Graph):

    def build_title_block(self):
        msg = 'Game set up by {}!'.format(ids.user_display(self.organizer_id))
        return blocks.build_text_block(msg)

    def build_question_block(self):
        return blocks.build_text_block(self.question)

    @staticmethod
    def build_preparing_guess_stage_block():
        return blocks.build_text_block('Preparing guess stage...')

    @staticmethod
    def build_preparing_vote_stage_block():
        return blocks.build_text_block('Preparing vote stage...')

    @staticmethod
    def build_computing_results_stage_block():
        return blocks.build_text_block(
            'Computing results :drum_with_drumsticks:')

    def build_guess_button_block(self):
        id_ = self.build_guess_button_block_id()
        return blocks.build_button_block('Your guess', id_)

    def build_vote_button_block(self):
        id_ = self.build_vote_button_block_id()
        return blocks.build_button_block('Your vote', id_)

    def build_guess_timer_block(self):
        time_left = self.compute_time_left_to_guess()
        return blocks.build_guess_timer_block(time_left)

    def build_vote_timer_block(self):
        time_left = self.compute_time_left_to_vote()
        return blocks.build_vote_timer_block(time_left)

    def build_users_msg(self, users, kind, no_users_msg):
        if not users:
            return no_users_msg
        users = self.sort_users(users)
        user_displays = ids.user_displays(users)
        msg = '{}: {}'.format(kind, user_displays)
        return msg

    def build_users_blocks(self, users, kind, no_users_msg):
        msg = self.build_users_msg(users, kind, no_users_msg)
        return blocks.build_text_block(msg)

    def build_remaining_potential_voters_block(self):
        users = self.compute_remaining_potential_voters()
        kind = 'Potential voters'
        no_users_msg = 'Everyone has voted!'
        return self.build_users_blocks(users, kind, no_users_msg)

    def build_guessers_block(self):
        users = self.guessers
        kind = 'Guessers'
        no_users_msg = 'No one has guessed yet.'
        return self.build_users_blocks(users, kind, no_users_msg)

    def build_voters_block(self):
        users = self.voters
        kind = 'Voters'
        no_users_msg = 'No one has voted yet.'
        return self.build_users_blocks(users, kind, no_users_msg)

    def build_indexed_anonymous_proposals_block(self):
        msg = ['Proposals:']
        indexed_anonymous_proposals = self.build_indexed_anonymous_proposals()
        for iap in indexed_anonymous_proposals:
            index = iap['index']
            proposal = iap['proposal']
            msg.append('{}) {}'.format(index, proposal))
        msg = '\n'.join(msg)
        return blocks.build_text_block(msg)

    def build_own_guess_block(self, voter):
        index, guess = self.build_own_indexed_guess(voter)
        msg = 'Your guess: {}) {}'.format(index, guess)
        return blocks.build_text_block(msg)

    def build_indexed_signed_guesses_msg(self):
        msg = []
        for r in deepcopy(self.results):
            player = ids.user_display(r['guesser'])
            index = r['index']
            guess = r['guess']
            r_msg = '• {}: {}) {}'.format(player, index, guess)
            msg.append(r_msg)
        msg = '\n'.join(msg)
        return msg

    def build_conclusion_msg(self):
        lg = len(self.frozen_guessers)
        lv = len(self.frozen_voters)
        if lg == 0:
            return 'No one played this game :sob:.'
        if lg == 1:
            g = ids.user_display(list(self.frozen_guessers)[0])
            return 'Thanks for your guess, {}!'.format(g)
        if lv == 0:
            return 'No one voted :sob:.'
        if lv == 1:
            r = self.results[0]
            g = ids.user_display(r['guesser'])
            ca = r['chosen_author']
            if ca == 'Truth':
                return 'Bravo {}! You found the truth! :v:'.format(g)
            else:
                return 'Hey {}, at least you voted! :grimacing:'.format(g)
        if self.max_score == 0:
            return 'Zero points scored!'
        lw = len(self.winners)
        if lw == lv:
            return "Well, it's a draw! :scales:"
        if lw == 1:
            w = ids.user_display(self.winners[0])
            return 'And the winner is {}! :first_place_medal:'.format(w)
        if lw > 1:
            ws = [ids.user_display(w) for w in self.winners]
            msg_aux = ','.join(ws[:-1])
            msg_aux += ' and {}'.format(ws[-1])
            return 'And the winners are {}! :clap:'.format(msg_aux)

    def build_truth_block(self):
        msg = '• Truth: '
        if len(self.frozen_guessers) == 0:
            msg += '{}'.format(self.truth)
        else:
            index = self.truth_index
            msg += '{}) {}'.format(index, self.truth)
        return blocks.build_text_block(msg)

    def build_indexed_signed_guesses_block(self):
        msg = self.build_indexed_signed_guesses_msg()
        return blocks.build_text_block(msg)

    def build_graph_block(self):
        return blocks.build_image_block(url=self.graph_url,
                                        alt_text='Voting graph')

    def build_conclusion_block(self):
        msg = self.build_conclusion_msg()
        return blocks.build_text_block(msg)

    def build_pre_guess_stage_upper_blocks(self):
        title_block = self.build_title_block()
        preparing_guess_stage_block = self.build_preparing_guess_stage_block()
        return blocks.u([title_block, preparing_guess_stage_block])

    @staticmethod
    def build_pre_guess_stage_lower_blocks():
        return blocks.d([])

    def build_pre_vote_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        preparing_vote_stage_block = self.build_preparing_vote_stage_block()
        return blocks.u(
            [title_block, question_block, preparing_vote_stage_block])

    @staticmethod
    def build_pre_vote_stage_lower_blocks():
        return blocks.d([])

    def build_pre_result_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        computing_results_stage_block = \
            self.build_computing_results_stage_block()
        return blocks.u(
            [title_block, question_block, computing_results_stage_block])

    @staticmethod
    def build_pre_result_stage_lower_blocks():
        return blocks.d([])

    def build_guess_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        guess_button_block = self.build_guess_button_block()
        return blocks.u([title_block, question_block, guess_button_block])

    def build_guess_stage_lower_blocks(self):
        guess_timer_block = self.build_guess_timer_block()
        guessers_block = self.build_guessers_block()
        return blocks.d([guess_timer_block, guessers_block])

    def build_vote_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        anonymous_proposals_block = \
            self.build_indexed_anonymous_proposals_block()
        vote_button_block = self.build_vote_button_block()
        return blocks.u([title_block, question_block,
                         anonymous_proposals_block, vote_button_block])

    def build_vote_stage_lower_blocks(self):
        vote_timer_block = self.build_vote_timer_block()
        remaining_potential_voters_block = \
            self.build_remaining_potential_voters_block()
        voters_block = self.build_voters_block()
        return blocks.d(
            [vote_timer_block, remaining_potential_voters_block, voters_block])

    def build_result_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        truth_block = self.build_truth_block()
        indexed_signed_guesses_block = \
            self.build_indexed_signed_guesses_block()
        conclusion_block = self.build_conclusion_block()
        res = [title_block, question_block, truth_block,
               indexed_signed_guesses_block]
        if len(self.frozen_guessers) > 1 and len(self.frozen_voters) > 0:
            graph_block = self.build_graph_block()
            res.append(graph_block)
        res.append(conclusion_block)
        res = blocks.u(res)
        return res

    @staticmethod
    def build_result_stage_lower_blocks():
        return blocks.d([])


class Views(Blocks):

    @staticmethod
    def build_exception_view(msg):
        return views.build_exception_view(msg)

    @staticmethod
    def build_exception_view_response(msg):
        return views.build_exception_view_response(msg)

    def build_setup_view(self):
        id_ = self.build_setup_view_id()
        return views.build_game_setup_view(id_)

    def build_guess_view(self):
        id_ = self.build_guess_view_id()
        return views.build_guess_view(id_, self.question)

    def build_vote_view(self, voter):
        res = deepcopy(views.vote_view_template)
        res['callback_id'] = self.build_vote_view_id()
        input_block_template = res['blocks'][0]
        votable_proposals_msg = ['Voting options:']
        option_template = input_block_template['element']['options'][0]
        vote_options = []
        for iap in self.build_votable_indexed_anonymous_proposals(voter):
            index = iap['index']
            proposal = iap['proposal']
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


class Slack(Views):

    slack_token = None
    slack_client = None

    def build_slack_client(self):
        return SlackClient(token=self.slack_token)

    def get_potential_guessers(self):
        return slack.get_potential_guessers(
            self.slack_client, self.channel_id, self.organizer_id)

    def get_app_conversations(self):
        return slack.get_app_conversations(self.slack_client)

    def post_message(self, blocks_):
        return slack.post_message(self.slack_client, self.channel_id, blocks_)

    def post_ephemeral(self, user_id, msg):
        slack.post_ephemeral(self.slack_client, self.channel_id, user_id, msg)

    def update_message(self, blocks_, ts):
        slack.update_message(self.slack_client, self.channel_id, blocks_, ts)

    def open_view(self, trigger_id, view):
        slack.open_view(self.slack_client, trigger_id, view)

    def open_exception_view(self, trigger_id, msg):
        slack.open_exception_view(self.slack_client, trigger_id, msg)

    def update_upper(self, blocks_):
        self.update_message(blocks_, self.upper_ts)

    def update_lower(self, blocks_):
        self.update_message(blocks_, self.lower_ts)

    def send_vote_reminders(self):
        time_left_to_vote = self.compute_time_left_to_vote()
        for u in self.potential_voters:
            msg_template = (
                'Hey {}, you can now vote in the bluffer game ' 
                'organized by {}!')
            msg = msg_template.format(
                ids.user_display(u),
                ids.user_display(self.organizer_id),
                time_left_to_vote)
            self.post_ephemeral(u, msg)

    def send_is_over_notifications(self):
        for u in self.frozen_guessers:
            msg = ("The bluffer game organized by {} is over!"
                   .format(ids.user_display(self.organizer_id)))
            self.post_ephemeral(u, msg)

    def post_pre_guess_stage_upper(self):
        return self.post_message(self.build_pre_guess_stage_upper_blocks())

    def post_pre_guess_stage_lower(self):
        return self.post_message(self.build_pre_guess_stage_lower_blocks())

    def update_pre_vote_stage_upper(self):
        self.update_upper(self.build_pre_vote_stage_upper_blocks())

    def update_pre_vote_stage_lower(self):
        self.update_lower(self.build_pre_vote_stage_lower_blocks())

    def update_pre_result_stage_upper(self):
        self.update_upper(self.build_pre_result_stage_upper_blocks())

    def update_pre_result_stage_lower(self):
        self.update_lower(self.build_pre_result_stage_lower_blocks())

    def update_guess_stage_upper(self):
        self.update_upper(self.build_guess_stage_upper_blocks())

    def update_guess_stage_lower(self):
        self.update_lower(self.build_guess_stage_lower_blocks())

    def update_vote_stage_upper(self):
        self.update_upper(self.build_vote_stage_upper_blocks())

    def update_vote_stage_lower(self):
        self.update_lower(self.build_vote_stage_lower_blocks())

    def update_result_stage_upper(self):
        self.update_upper(self.build_result_stage_upper_blocks())

    def update_result_stage_lower(self):
        self.update_lower(self.build_result_stage_lower_blocks())

    def post_pre_guess_stage(self):
        return self.post_pre_guess_stage_upper(), \
               self.post_pre_guess_stage_lower()

    def update_pre_vote_stage(self):
        self.update_pre_vote_stage_upper()
        self.update_pre_vote_stage_lower()

    def update_pre_result_stage(self):
        self.update_pre_result_stage_upper()
        self.update_pre_result_stage_lower()

    def update_guess_stage(self):
        self.update_guess_stage_upper()
        self.update_guess_stage_lower()

    def update_vote_stage(self):
        self.update_vote_stage_upper()
        self.update_vote_stage_lower()

    def update_result_stage(self):
        self.update_result_stage_upper()
        self.update_result_stage_lower()

    def open_setup_view(self, trigger_id):
        self.open_view(trigger_id, self.build_setup_view())

    def open_guess_view(self, trigger_id):
        self.open_view(trigger_id, self.build_guess_view())

    def open_vote_view(self, trigger_id, voter):
        view = self.build_vote_view(voter)
        self.open_view(trigger_id, view)


class Exceptions(Version, Question, Time, Truth, Guessers, Voters):

    max_running_games = None
    max_guessers = None
    exists = None

    @staticmethod
    def count_running_games(game_dicts):
        return len([g for g in game_dicts if 'result_stage_over' not in g])

    @staticmethod
    def get_running_organizer_ids(game_dicts):
        return [ids.game_id_to_organizer_id(gid) for gid in game_dicts
                if 'result_stage_over' not in game_dicts[gid]]

    def max_nb_of_running_games_reached(self, game_dicts):
        nb_of_running_games = self.count_running_games(game_dicts)
        return nb_of_running_games >= self.max_running_games

    def organizer_has_another_game_running(self, game_dicts):
        running_organizer_ids = self.get_running_organizer_ids(game_dicts)
        return self.organizer_id in running_organizer_ids

    def app_is_in_conversation(self, app_conversations):
        return self.channel_id in [c['id'] for c in app_conversations]

    def no_time_left_to_guess(self):
        return self.compute_time_left_to_guess() >= 0

    def max_nb_of_guessers_reached(self):
        return len(self.guessers) >= self.max_guessers

    def no_time_left_to_vote(self):
        return self.compute_time_left_to_vote() >= 0

    def is_too_old(self):
        now = time.get_now()
        delta = time.datetime1_minus_datetime2(now, self.setup_submission)
        print(delta)
        return delta >= self.max_life_span

    def version_is_bad(self):
        return self.version != self.version_latest

    def is_dead(self):
        if not self.exists:
            return True
        if self.setup_submission is None:
            return True
        if self.is_too_old():
            return True
        if self.version is None:
            return True
        if self.version_is_bad():
            return True
        return False

    @staticmethod
    def build_organizer_has_another_game_running_msg():
        return ('You are the organizer of a game which is sill running. '
                'You can only have one game running at a time.')

    def build_is_dead_msg(self):
        if self.is_dead():
            return 'This game is dead!'

    def build_slash_command_exception_msg(self, game_dicts, app_conversations):
        if self.max_nb_of_running_games_reached(game_dicts):
            msg_template = ('There are already {} games running! '
                            'This is the maximal number allowed.')
            msg = msg_template.format(self.max_running_games)
            return msg
        if self.organizer_has_another_game_running(game_dicts):
            return self.build_organizer_has_another_game_running_msg()
        if not self.app_is_in_conversation(app_conversations):
            return 'Please invite me first to this conversation!'

    def build_setup_view_exception_msg(self, game_dicts):
        if self.max_nb_of_running_games_reached(game_dicts):
            msg = ('Question: {}\n\n'
                   'Answer: {}\n\n'
                   'Time to guess: {}s\n\n'
                   'There are already {} games running! '
                   'This is the maximal number allowed.'.format(
                    self.question, self.truth, self.time_to_guess,
                    self.max_running_games))
            return msg
        if self.organizer_has_another_game_running(game_dicts):
            return self.build_organizer_has_another_game_running_msg()

    def build_guess_view_exception_msg(self, guess):
        if not self.no_time_left_to_guess():
            msg = ('Your guess: {}\n\n'
                   'It will not be taken into account '
                   'because the guessing deadline '
                   'has passed!'.format(guess))
            return msg
        if self.max_nb_of_guessers_reached():
            msg_template = ('Your guess: {}\n\n'
                            'It will not be taken into account '
                            'because there are already {} guessers. '
                            'This is the maximal number allowed.')
            msg = msg_template.format(guess, self.max_guessers)
            return msg

    def build_vote_view_exception_msg(self, vote):
        if not self.no_time_left_to_vote():
            msg = ('Your vote: proposal {}.\n\n'
                   'It will not be taken into account '
                   'because the voting deadline has passed!'.format(vote))
            return msg

    def build_guess_button_exception_msg(self, user_id):
        if user_id == self.organizer_id:
            return 'As the organizer of this game, you cannot guess!'
        if user_id in self.guessers:
            return 'You have already guessed!'
        if user_id not in self.potential_guessers:
            msg = ('You cannot guess because when the set up of this '
                   'game started, you were not a member of this channel.')
            return msg
        if self.max_nb_of_guessers_reached():
            msg_template = ('You cannot guess because there are already {} '
                            'guessers. This is the maximal number allowed.')
            msg = msg_template.format(self.max_guessers)
            return msg
        if user_id == 'Truth':
            msg = ("You cannot play bluffer because your slack user_id is "
                   "'Truth', which is a reserved word for the game.")
            return msg

    def build_vote_button_exception_msg(self, user_id):
        if user_id not in self.potential_voters:
            return 'Only guessers can vote!'
        if user_id in self.voters:
            return 'You have already voted!'


class Game(PubSub, Firestore, Slack, Exceptions):

    def __init__(
            self,
            game_id,
            secret_prefix,
            project_id,
            publisher,
            db,
            bucket,
            local_dir_path,
            logger,
    ):
        self.id = game_id
        self.secret_prefix = secret_prefix
        self.project_id = project_id
        self.publisher = publisher
        self.db = db
        self.bucket = bucket
        self.local_dir_path = local_dir_path
        self.logger = logger

        self.code = self.build_code()

        self.slash_command_compact = self.get_slash_command_compact()
        self.team_id = self.get_team_id()
        self.channel_id = self.get_channel_id()
        self.organizer_id = self.get_organizer_id()

        self.ref = self.build_ref()

        self.bucket_dir_name = self.team_id

        self.team_dict = self.get_team_dict()
        self.diffuse_team_dict()

        self.slack_client = self.build_slack_client()

        self.dict = self.get_dict()
        if self.dict:
            self.exists = True
            self.diffuse_dict()
        else:
            self.exists = False

    def diffuse(self, d):
        for key in d:
            self.__dict__[key] = d[key]

    def diffuse_team_dict(self):
        self.diffuse(self.team_dict)

    def diffuse_dict(self):
        self.diffuse(self.dict)
