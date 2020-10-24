import os
import random
import networkx as nx
import matplotlib.pyplot as plt
from copy import deepcopy
from slackclient import SlackClient
from bluffer.utils import *


class Guessers:

    potential_guessers = None
    guessers = None
    frozen_guessers = None

    def get_guesser_name(self, guesser):
        return self.potential_guessers[guesser]

    def compute_remaining_potential_guessers(self):
        return set(self.potential_guessers) - set(self.guessers)


class Voters:

    potential_voters = None
    voters = None
    frozen_voters = None

    def compute_remaining_potential_voters(self):
        return set(self.potential_voters) - set(self.voters)


class Proposals(Guessers):

    truth = None
    indexed_signed_proposals = None
    truth_index = None

    def index_to_author(self, index):
        for index_, author, proposal in self.indexed_signed_proposals:
            if index_ == index:
                return author

    def author_to_index(self, author):
        for index, author_, proposal in self.indexed_signed_proposals:
            if author == author_:
                return index

    def author_to_proposal(self, author):
        for index_, author_, proposal in self.indexed_signed_proposals:
            if author_ == author:
                return proposal

    @staticmethod
    def to_firestore_indexed_signed_proposals(python_isp):
        return {str(index): [author, proposal]
                for index, author, proposal in python_isp}

    @staticmethod
    def to_python_indexed_signed_proposals(firestore_isp):
        return [
            (int(index),
             firestore_isp[index][0],
             firestore_isp[index][1])
            for index in firestore_isp]

    def build_indexed_signed_proposals(self):
        res = [(k, self.frozen_guessers[k][1]) for k in self.frozen_guessers]
        res.append(('Truth', self.truth))
        random.shuffle(res)
        res = [(index, author, proposal)
               for index, (author, proposal) in enumerate(res, 1)]
        return res

    def build_own_guess(self, guesser):
        index = self.author_to_index(guesser)
        guess = self.author_to_proposal(guesser)
        return index, guess

    def build_votable_indexed_anonymous_proposals(self, voter):
        res = []
        for index, author, proposal in self.indexed_signed_proposals:
            if author != voter:
                res.append((index, proposal))
        return res

    def build_indexed_anonymous_proposals(self):
        res = []
        for index, author, proposal in self.indexed_signed_proposals:
            res.append((index, proposal))
        return res

    def compute_truth_index(self):
        return self.author_to_index('Truth')


class Results(Proposals, Voters):

    frozen_voters = None
    results = None
    winners = None
    max_score = None

    def compute_truth_score(self, voter):
        return int(self.frozen_voters[voter] == self.author_to_index('Truth'))

    def compute_bluff_score(self, voter):
        res = 0
        for voter_ in self.frozen_voters:
            voter_index = self.author_to_index(voter)
            if self.frozen_voters[voter_] == voter_index:
                res += 2
        return res

    def compute_winners(self):
        res = []
        for r in self.results:
            if r['score'] == self.max_score:
                res.append(r['guesser'])
        self.winners = res

    def compute_max_score(self):
        scores = [r['score'] for r in self.results if 'score' in r]
        self.max_score = scores[0]

    def build_results(self):
        results = []
        for index, author, proposal in self.indexed_signed_proposals:
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
            vote_index = self.frozen_voters[author]
            r['vote_index'] = vote_index
            r['chosen_author'] = self.index_to_author(vote_index)
            r['truth_score'] = self.compute_truth_score(author)
            r['bluff_score'] = self.compute_bluff_score(author)
            r['score'] = r['truth_score'] + r['bluff_score']
            results.append(r)

        def sort_key(r_):
            return 'vote_index' not in r_, -r_['score'], r_['guesser']

        results.sort(key=lambda r_: sort_key(r_))

        self.results = results


class Time:

    game_creation_ts = None

    time_to_guess = None
    time_to_vote = None

    upper_ts = None
    lower_ts = None

    guess_start = None
    vote_start = None

    guess_deadline = None
    vote_deadline = None

    def compute_guess_deadline(self):
        return timer.compute_deadline(self.guess_start, self.time_to_guess)

    def compute_vote_deadline(self):
        return timer.compute_deadline(self.vote_start, self.time_to_vote)

    def compute_time_left_to_guess(self):
        return timer.compute_time_left(self.guess_deadline)

    def compute_time_left_to_vote(self):
        return timer.compute_time_left(self.vote_deadline)


class Ids:

    secret_prefix = None
    game_id = None
    game_code = None
    team_id = None
    organizer_id = None
    channel_id = None

    def build_game_code(self):
        self.game_code = self.game_id.encode("utf-8")

    def build_team_id(self):
        self.team_id = ids.game_id_to_team_id(self.game_id)

    def build_organizer_id(self):
        self.organizer_id = ids.game_id_to_organizer_id(self.game_id)

    def build_channel_id(self):
        self.channel_id = ids.game_id_to_channel_id(self.game_id)

    def build_slack_object_id(self, object_name):
        return ids.build_slack_object_id(self.secret_prefix,
                                         object_name, self.game_id)

    def build_game_setup_view_id(self):
        return self.build_slack_object_id('game_setup_view')

    def build_guess_view_id(self):
        return self.build_slack_object_id('guess_view')

    def build_vote_view_id(self):
        return self.build_slack_object_id('vote_view')

    def build_guess_button_block_id(self):
        return self.build_slack_object_id('guess_button_block')

    def build_vote_button_block_id(self):
        return self.build_slack_object_id('vote_button_block')


class PubSub(Ids):

    project_id = None
    publisher = None

    def build_topic_path(self, topic_name):
        return pubsub.build_topic_path(
            self.publisher, self.project_id, topic_name)

    def publish(self, topic_name):
        topic_path = self.build_topic_path(topic_name)
        self.publisher.publish(topic_path, data=self.game_code)

    def trigger_pre_guess_stage(self):
        self.publish('topic_pre_guess_stage')

    def trigger_guess_stage(self):
        self.publish('topic_guess_stage')

    def trigger_pre_vote_stage(self):
        self.publish('topic_pre_vote_stage')

    def trigger_vote_stage(self):
        self.publish('topic_vote_stage')

    def trigger_result_stage(self):
        self.publish('topic_result_stage')


class Firestore(Ids):

    db = None

    team_dict = None
    game_dict = None

    def get_team_dict(self):
        self.team_dict = firestore.team_id_to_team_dict(
            self.db, self.team_id)

    def get_game_dict(self):
        self.game_dict = firestore.get_game_dict(
            self.db, self.team_id, self.game_id)

    def get_game_ref(self):
        return firestore.get_game_ref(self.db, self.team_id, self.game_id)


class Local(Ids, Time):

    local_dir_path = None
    graph_basename = None
    graph_local_path = None

    def build_basename(self, core_name, ext):
        return '{}_{}_{}.{}'.format(
                    self.guess_start.strftime('%Y%m%d_%H%M%S'),
                    core_name, self.game_id, ext)

    def build_graph_basename(self):
        return self.build_basename('graph', 'png')

    def build_local_path(self, basename):
        return self.local_dir_path + '/' + basename

    def build_graph_local_path(self):
        return self.build_local_path(self.graph_basename)


class Storage(Local):

    bucket = None
    bucket_dir_name = None

    def upload_to_gs(self, local_file_path, sub_dir_name):
        basename = os.path.basename(local_file_path)

        blob_name = '{}/{}/{}'.format(
            self.bucket_dir_name, sub_dir_name, basename)

        blob = self.bucket.blob(blob_name)

        blob.upload_from_filename(local_file_path)

        return blob.public_url

    def upload_graph_to_gs(self):
        return self.upload_to_gs(self.graph_local_path, 'graphs')


class Graph(Local, Results):

    graph = None
    graph_url = None

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


class Blocks(Ids, Time, Graph):

    question = None

    def build_title_block(self):
        msg = 'Game set up by {}!'.format(ids.user_display(self.organizer_id))
        return blocks.build_text_block(msg)

    def build_question_block(self):
        return blocks.build_text_block(self.question)

    def build_guess_button_block(self):
        id_ = self.build_guess_button_block_id()
        return blocks.build_button_block('Your guess', id_)

    def build_vote_button_block(self):
        id_ = self.build_vote_button_block_id()
        return blocks.build_button_block('Your vote', id_)

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

    def build_guess_timer_block(self):
        time_left = self.compute_time_left_to_guess()
        return blocks.build_guess_timer_block(time_left)

    def build_vote_timer_block(self):
        time_left = self.compute_time_left_to_vote()
        return blocks.build_vote_timer_block(time_left)

    def build_users_blocks(self, kind):
        assert kind in ('guessers', 'voters')
        past_participle = 'guessed' if kind == 'guessers' else 'voted'
        users = self.guessers if kind == 'guessers' else self.voters
        users = sorted(users, key=lambda k: users[k][0])
        if not users:
            msg = 'No one has {} yet.'.format(past_participle)
            return blocks.build_text_block(msg)
        user_displays = ids.user_displays(users)
        msg = '{}: {}'.format(kind.title(), user_displays)
        return blocks.build_text_block(msg)

    def build_guessers_block(self):
        return self.build_users_blocks('guessers')

    def build_voters_block(self):
        return self.build_users_blocks('voters')

    def build_guess_stage_lower_blocks(self):
        guess_timer_block = self.build_guess_timer_block()
        guessers_block = self.build_guessers_block()
        return blocks.d([guess_timer_block, guessers_block])

    def build_vote_stage_lower_blocks(self):
        vote_timer_block = self.build_vote_timer_block()
        voters_block = self.build_voters_block()
        return blocks.d([vote_timer_block, voters_block])

    def build_anonymous_proposals_block(self):
        msg = ['Proposals:']
        anonymous_proposals = self.build_anonymous_proposals()
        for index, proposal in anonymous_proposals:
            msg.append('{}) {}'.format(index, proposal))
        msg = '\n'.join(msg)
        return blocks.build_text_block(msg)

    def build_own_guess_block(self, voter):
        index, guess = self.build_own_guess(voter)
        msg = 'Your guess: {}) {}'.format(index, guess)
        return blocks.build_text_block(msg)

    def build_signed_guesses_block(self):
        msg = self.build_signed_guesses_msg('slack')
        return blocks.build_text_block(msg)

    def build_conclusion_block(self):
        msg = self.build_conclusion_msg('slack')
        return blocks.build_text_block(msg)

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

    def build_signed_guesses_msg(self, fmt):
        assert fmt in ('slack', 'pdf')
        msg = []
        for r in deepcopy(self.results):
            if fmt == 'slack':
                player = ids.user_display(r['guesser'])
            else:
                player = r['guesser_name']
            index = r['index']
            guess = r['guess']
            r_msg = '• {}: {}) {}'.format(player, index, guess)
            msg.append(r_msg)
        msg = '\n'.join(msg)
        return msg


class Views(Blocks):

    def build_game_setup_view(self):
        id_ = self.build_game_setup_view_id()
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


class Slack(Views):

    slack_client = None

    def post_message(self, blocks_):
        return self.slack_client.api_call(
            'chat.postMessage',
            channel=self.channel_id,
            blocks=blocks_)['ts']

    def post_ephemeral(self, user_id, msg):
        self.slack_client.api_call(
            'chat.postEphemeral',
            channel=self.channel_id,
            user=user_id,
            text=msg)

    def update_message(self, blocks_, ts):
        self.slack_client.api_call(
            'chat.update',
            channel=self.channel_id,
            ts=ts,
            blocks=blocks_)

    def open_view(self, trigger_id, view):
        self.slack_client.api_call(
            'views.open',
            trigger_id=trigger_id,
            view=view)

    def update_upper(self, blocks_):
        self.update_message(blocks_, self.upper_ts)

    def update_lower(self, blocks_):
        self.update_message(blocks_, self.lower_ts)

    def update_guess_stage_lower(self):
        guess_stage_lower_blocks = self.build_guess_stage_lower_blocks()
        self.update_lower(guess_stage_lower_blocks)

    def update_vote_stage_lower(self):
        vote_stage_lower_blocks = self.build_vote_stage_lower_blocks()
        self.update_lower(vote_stage_lower_blocks)

    def open_game_setup_view(self, trigger_id):
        self.open_view(trigger_id, self.build_game_setup_view())

    def open_guess_view(self, trigger_id):
        self.open_view(trigger_id, self.build_guess_view())

    def open_vote_view(self, trigger_id, voter):
        view = self.build_vote_view(voter)
        self.open_view(trigger_id, view)

    def get_potential_guessers(self):
        return members.get_potential_guessers(
            self.slack_client, self.channel_id, self.organizer_id)

    def send_vote_reminders(self):
        time_left_to_vote = self.compute_time_left_to_guess()
        for u in self.frozen_guessers:
            msg_template = (
                'Hey {}, you can now vote in the bluffer game ' 
                'organized by {}!'
            )
            msg = msg_template.format(
                ids.user_display(u),
                ids.user_display(self.organizer_id),
                time_left_to_vote)
            self.post_ephemeral(u, msg)


class Game(Slack, Storage, PubSub, Firestore):

    def __init__(
            self,
            game_id,
            secret_prefix,
            project_id,
            publisher,
            db,
            bucket,
            bucket_dir_name,
            local_dir_path,
            logger,
            fetch_game_data=True
    ):
        self.game_id = game_id
        self.secret_prefix = secret_prefix
        self.project_id = project_id
        self.publisher = publisher
        self.db = db
        self.bucket = bucket
        self.bucket_dir_name = bucket_dir_name
        self.local_dir_path = local_dir_path
        self.logger = logger

        self.get_team_dict()
        self.diffuse_team_dict()

        self.slack_client = SlackClient(token=self.slack_token)

        if fetch_game_data:
            self.get_game_dict()
            self.diffuse_game_dict()

        if self.indexed_signed_proposals is not None:
            self.indexed_signed_proposals = \
                self.to_python_indexed_signed_proposals(
                    self.indexed_signed_proposals)

    def diffuse_dict(self, d):
        for key in d:
            d[key] = self.__dict__[key]

    def diffuse_team_dict(self):
        self.diffuse_dict(self.team_dict)

    def diffuse_game_dict(self):
        self.diffuse_dict(self.game_dict)
