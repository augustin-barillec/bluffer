import random
from slackclient import SlackClient
from bluffer.utils import *


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

    def build_game_setup_view(self):
        id_ = self.build_game_setup_view_id()
        return views.build_game_setup_view(id_)

    def build_guess_view(self):
        id_ = self.build_guess_view_id()
        return views.build_guess_view(id_, self.game_dict['question'])

    def open_view(self, trigger_id, view):
        views.open_view(self.slack_client, trigger_id, view)

    def open_game_setup_view(self, trigger_id):
        self.open_view(trigger_id, self.build_game_setup_view())

    def open_guess_view(self, trigger_id):
        self.open_view(trigger_id, self.build_guess_view())

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
    def build_pre_guess_stage_block():
        return blocks.build_text_block('Preparing guess stage...')

    @staticmethod
    def build_pre_vote_stage_block():
        return blocks.build_text_block('Preparing vote stage...')

    @staticmethod
    def build_pre_results_stage_block():
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

    def compute_time_left_to_guess(self):
        return timer.compute_time_left(self.game_dict['guess_deadline'])

    def compute_time_left_to_vote(self):
        return timer.compute_time_left(self.game_dict['vote_deadline'])

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

    def build_proposals_for_python(self):
        guessers = self.game_dict['frozen_guessers']
        truth = self.game_dict['truth']
        res = [(k, guessers[k][1]) for k in guessers] + [('Truth', truth)]
        random.shuffle(res)
        res = [(index, author, proposal)
               for index, (author, proposal) in enumerate(res, 1)]
        return res

    @staticmethod
    def to_firestore_proposals(python_proposals):
        return {str(index): [author, proposal]
                for index, author, proposal in python_proposals}

    @staticmethod
    def to_python_proposals(firestore_proposals):
        return [
            (int(index), firestore_proposals[0], firestore_proposals[1])
            for index in firestore_proposals]

    def build_proposals_for_firestore(self):
        return self.to_firestore_proposals(self.build_proposals_for_python())













