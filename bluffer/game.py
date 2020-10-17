import random
from copy import deepcopy
from slackclient import SlackClient
from bluffer.utils import *

from argparse import Namespace


class Game:
    def __init__(
            self,
            game_id,
            secret_prefix,
            project_id,
            publisher,
            db,
            logger
    ):
        self.game_id = game_id
        self.code = self.game_id.encode("utf-8")
        self.secret_prefix = secret_prefix
        self.project_id = project_id
        self.publisher = publisher
        self.db = db
        self.logger = logger

        self.team_id = ids.game_id_to_team_id(self.game_id)
        self.organizer_id = ids.game_id_to_organizer_id(self.game_id)
        self.channel_id = ids.game_id_to_channel_id(self.game_id)

        self.team_dict = None
        self.game_dict = None

        self.slack_client = None

        self.guesses = None
        self.guessers = None
        self.votes = None
        self.voters = None
        self.results = None
        self.winners = None
        self.max_score = None

    def get_team_dict(self):
        self.team_dict = firestore.team_id_to_team_dict(
            self.db, self.team_id)
        token = self.team_dict['token']
        self.slack_client = SlackClient(token=token)
        return self.team_dict

    def get_game_dict(self):
        self.game_dict = firestore.get_game_dict(
            self.db, self.team_id, self.game_id)
        return self.game_dict

    def get_game_ref(self):
        return firestore.get_game_ref(self.db, self.team_id, self.game_id)

    def ids(self):

        res = Namespace()

        def build_slack_object_id(object_name):
            return ids.build_slack_object_id(
                self.secret_prefix, object_name, self.game_id)

        def build_game_setup_view_id():
            return build_slack_object_id('game_setup_view')

        res.build_game_setup_view_id = build_game_setup_view_id()

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

    def views(self):

        def open_view(self, trigger_id, view):
            views.open_view(self.slack_client, trigger_id, view)

        def open_game_setup_view(self, trigger_id):
            self.open_view(trigger_id, self.build_game_setup_view())

        def build_game_setup_view(self):
            id_ = self.build_game_setup_view_id()
            return views.build_game_setup_view(id_)

        def build_guess_view(self):
            id_ = self.build_guess_view_id()
            return views.build_guess_view(id_, self.game_dict['question'])

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

        def open_guess_view(self, trigger_id):
            self.open_view(trigger_id, self.build_guess_view())

    def pubsub(self):

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

        def trigger_result_stage(self):
            self.publish('topic_result_stage')

    def slack(self):

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

        def update_upper(self, blocks_):
            self.update_message(blocks_, self.game_dict['upper_ts'])

        def update_lower(self, blocks_):
            self.update_message(blocks_, self.game_dict['lower_ts'])

        def update_guess_stage_lower(self):
            guess_stage_lower_blocks = self.build_guess_stage_lower_blocks()
            self.update_lower(guess_stage_lower_blocks)

        def update_vote_stage_lower(self):
            vote_stage_lower_blocks = self.build_vote_stage_lower_blocks()
            self.update_lower(vote_stage_lower_blocks)

    def blocks(self):

        def build_title_block(self):
            msg = 'Game set up by {}!'.format(ids.user_display(self.organizer_id))
            return blocks.build_text_block(msg)

        def build_question_block(self):
            return blocks.build_text_block(self.game_dict['question'])

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
            users = self.game_dict[kind]
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
            proposals = self.to_python_proposals(self.game_dict['proposals'])
            for index, author, proposal in proposals:
                msg.append('{}) {}'.format(index, proposal))
            msg = '\n'.join(msg)
            return blocks.build_text_block(msg)

        def build_own_guess_block(self, voter):
            index = self.author_to_index(voter)
            guess = self.author_to_proposal(voter)
            msg = 'Your guess: {}) {}'.format(index, guess)
            return blocks.build_text_block(msg)

        def build_signed_guesses_block(self):
            msg = self.build_signed_guesses_msg('slack')
            return blocks.build_text_block(msg)

        def build_conclusion_block(self):
            msg = self.build_conclusion_msg('slack')
            return blocks.build_text_block(msg)

    def time(self):

        def compute_time_left_to_guess(self):
            return timer.compute_time_left(self.game_dict['guess_deadline'])

        def compute_time_left_to_vote(self):
            return timer.compute_time_left(self.game_dict['vote_deadline'])

    def get_potential_guessers(self):
        return members.get_potential_guessers(
            self.slack_client, self.channel_id, self.organizer_id)

    def compute_remaining_potential_guessers(self):
        potential_guessers = self.game_dict['potential_guessers']
        guessers = self.game_dict['guessers']
        return set(potential_guessers) - set(guessers)

    def compute_remaining_potential_voters(self):
        potential_voters = self.game_dict['potential_voters']
        voters = self.game_dict['voters']
        return set(potential_voters) - set(voters)

    def send_vote_reminders(self):
        time_left_to_vote = self.compute_time_left_to_guess()
        for u in self.game_dict['guessers']:
            msg_template = ('Hey {}, you can now vote in the bluffer game ' 
                            'organized by {}!')
            msg = msg_template.format(
                ids.user_display(u),
                ids.user_display(self.organizer_id),
                time_left_to_vote)
            self.post_ephemeral(u, msg)

    @staticmethod
    def to_firestore_proposals(python_proposals):
        return {str(index): [author, proposal]
                for index, author, proposal in python_proposals}

    @staticmethod
    def to_python_proposals(firestore_proposals):
        return [
            (int(index),
             firestore_proposals[index][0],
             firestore_proposals[index][1])
            for index in firestore_proposals]

    def build_python_proposals(self):
        guessers = self.game_dict['frozen_guessers']
        truth = self.game_dict['truth']
        res = [(k, guessers[k][1]) for k in guessers] + [('Truth', truth)]
        random.shuffle(res)
        res = [(index, author, proposal)
               for index, (author, proposal) in enumerate(res, 1)]
        return res

    def build_firestore_proposals(self):
        return self.to_firestore_proposals(self.build_python_proposals())

    def get_python_proposals(self):
        return self.to_python_proposals(self.game_dict['proposals'])

    def build_votable_proposals(self, voter):
        proposals = self.get_python_proposals()
        res = []
        for index, author, proposal in proposals:
            if author != voter:
                res.append((index, proposal))
        return res

    def index_to_author(self, index):
        for index_, author, proposal in self.get_python_proposals():
            if index_ == index:
                return author

    def author_to_index(self, author):
        for index, author_, proposal in self.get_python_proposals():
            if author == author_:
                return index

    def author_to_proposal(self, author):
        for index_, author_, proposal in self.get_python_proposals():
            if author_ == author:
                return proposal

    def open_vote_view(self, trigger_id, voter):
        view = self.build_vote_view(voter)
        self.open_view(trigger_id, view)

    def build_results(self):
        results = []
        for index, author, proposal in self.get_python_proposals():
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
            r['truth_score'] = self.compute_truth_score(author)
            r['bluff_score'] = self.compute_bluff_score(author)
            r['score'] = r['truth_score'] + r['bluff_score']
            results.append(r)

        def sort_key(r_):
            return 'vote_index' not in r_, -r_['score'], r_['guesser']

        results.sort(key=lambda r_: sort_key(r_))

        self.results = results

    def compute_truth_score(self, voter):
        return int(self.votes[voter] == self.author_to_index('Truth'))

    def compute_bluff_score(self, voter):
        res = 0
        for voter_ in self.votes.keys():
            voter_index = self.author_to_index(voter)
            if self.votes[voter_] == voter_index:
                res += 2
        return res

    def get_guesser_name(self, guesser):
        return self.game_dict['potential_guessers'][guesser]

    def build_guesses(self):
        self.guesses = {
            guesser: self.game_dict['frozen_guessers'][guesser][1]
            for guesser in self.game_dict['frozen_guessers']
        }

    def build_votes(self):
        self.votes = {
            voter: self.game_dict['frozen_voters'][voter][1]
            for voter in self.game_dict['frozen_voters']
        }

    def build_guessers(self):
        self.guessers = list(self.guesses.keys())

    def build_voters(self):
        self.voters = list(self.votes.keys())

    def compute_winners(self):
        res = []
        for r in self.results:
            if r['score'] == self.max_score:
                res.append(r['guesser'])
        self.winners = res

    def compute_max_score(self):
        scores = [r['score'] for r in self.results if 'score' in r]
        self.max_score = scores[0]

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







