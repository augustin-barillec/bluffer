from slackclient import SlackClient
from copy import deepcopy
from app.utils import ids, proposals, time, pubsub, firestore, blocks, views, \
    slack, graph, storage

VERSION = 1


















class Exceptions:
    def __init__(
            self,
            version,
            game_exists,
            channel_id,
            organizer_id,
            question,
            truth,
            time_to_guess,
            guessers,
            voters,
            potential_guessers,
            potential_voters,
            setup_submission,
            guess_stage_last_trigger,
            vote_stage_last_trigger,
            max_running_games,
            max_guessers,
            max_life_span,
            time_left_builder):

        self.version = version
        self.game_exists = game_exists
        self.channel_id = channel_id
        self.organizer_id = organizer_id
        self.question = question
        self.truth = truth
        self.time_to_guess = time_to_guess
        self.guessers = guessers
        self.voters = voters
        self.potential_guessers = potential_guessers
        self.potential_voters = potential_voters
        self.setup_submission = setup_submission
        self.guess_stage_last_trigger = guess_stage_last_trigger
        self.vote_stage_last_trigger = vote_stage_last_trigger
        self.max_running_games = max_running_games
        self.max_guessers = max_guessers
        self.max_life_span = max_life_span
        self.time_left_builder = time_left_builder

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
        return self.time_left_builder.compute_time_left_to_guess() >= 0

    def max_nb_of_guessers_reached(self):
        return len(self.guessers) >= self.max_guessers

    def no_time_left_to_vote(self):
        return self.time_left_builder.compute_time_left_to_vote() >= 0

    def is_too_old(self):
        now = time.get_now()
        delta = time.datetime1_minus_datetime2(now, self.setup_submission)
        return delta >= self.max_life_span

    def version_is_bad(self):
        return self.version != VERSION

    def is_dead(self):
        if not self.game_exists:
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
    def stage_was_recently_trigger(last_trigger):
        if last_trigger is None:
            return False
        delta = time.datetime1_minus_datetime2(
            time.get_now(), last_trigger)
        return delta < 30

    def guess_stage_was_recently_trigger(self):
        return self.stage_was_recently_trigger(self.guess_stage_last_trigger)

    def vote_stage_was_recently_trigger(self):
        return self.stage_was_recently_trigger(self.vote_stage_last_trigger)

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


class Game:

    def __init__(
            self,
            game_id,
            secret_prefix,
            project_id,
            publisher,
            db,
            bucket,
            local_dir_path,
            logger):
        self.version = VERSION

        self.id = game_id
        self.secret_prefix = secret_prefix
        self.project_id = project_id
        self.publisher = publisher
        self.db = db
        self.bucket = bucket
        self.local_dir_path = local_dir_path
        self.logger = logger

        self.id_builder = IdBuilder(self.secret_prefix, self.id)
        self.code = self.id_builder.build_code()
        self.team_id = self.id_builder.get_team_id()
        self.channel_id = self.id_builder.get_channel_id()
        self.organizer_id = self.id_builder.get_organizer_id()

        self.bucket_dir_name = self.team_id
        self.graph_basename = '{}_graph.png'.format(self.id)
        self.graph_local_path = self.local_dir_path + '/' + self.graph_basename

        self.db_reader = DataBaseReader(self.db, self.team_id, self.id)
        self.ref = self.db_reader.build_game_ref()
        self.team_dict = self.db_reader.get_team_dict()

        self.max_guessers = self.team_dict['max_guessers']
        self.max_running_games = self.team_dict['max_running_games']
        self.post_clean = self.team_dict['post_clean']
        self.slack_token = self.team_dict['slack_token']
        self.time_to_vote = self.team_dict['time_to_vote']

        self.slack_client = SlackClient(self.slack_token)

        self.exists = True
        self.dict = self.db_reader.get_game_dict()
        if not self.dict:
            self.exists = False
            return
        self.frozen_guessers = self.dict.get('frozen_guessers')
        self.frozen_voters = self.dict.get('frozen_voters')
        self.guess_deadline = self.dict.get('guess_deadline')
        self.guess_stage_last_trigger = self.dict.get(
            'guess_stage_last_trigger')
        self.guess_stage_over = self.dict.get('guess_stage_over')
        self.guess_start = self.dict.get('guess_start')
        self.guessers = self.dict.get('guessers')
        self.indexed_signed_proposals = self.dict.get(
            'indexed_signed_proposals')
        self.lower_ts = self.dict.get('lower_ts')
        self.max_life_span = self.dict.get('max_life_span')
        self.max_score = self.dict.get('max_score')
        self.potential_guessers = self.dict.get('potential_guessers')
        self.potential_voters = self.dict.get('potential_voters')
        self.pre_guess_stage_already_triggered = self.dict.get(
            'pre_guess_stage_already_triggered')
        self.pre_result_stage_already_triggered = self.dict.get(
            'pre_result_stage_already_triggered')
        self.pre_vote_stage_already_triggered = self.dict.get(
            'pre_vote_stage_already_triggered')
        self.question = self.dict.get('question')
        self.result_stage_over = self.dict.get('result_stage_over')
        self.results = self.dict.get('results')
        self.setup_submission = self.dict.get('setup_submission')
        self.time_to_guess = self.dict.get('time_to_guess')
        self.truth = self.dict.get('truth')
        self.truth_index = self.dict.get('truth_index')
        self.upper_ts = self.dict.get('upper_ts')
        self.version = self.dict.get('version')
        self.vote_deadline = self.dict.get('vote_deadline')
        self.vote_stage_last_trigger = self.dict.get('vote_stage_last_trigger')
        self.vote_stage_over = self.dict.get('vote_stage_over')
        self.vote_start = self.dict.get('vote_start')
        self.voters = self.dict.get('voters')
        self.winners = self.dict.get('winners')

        self.enumerator = Enumerator(
            self.guessers,
            self.voters,
            self.potential_guessers,
            self.potential_voters)
        self.proposals_builder = ProposalsBuilder(
            self.id,
            self.frozen_guessers,
            self.truth)
        self.proposals_browser = ProposalsBrowser(
            self.indexed_signed_proposals)
        self.results_builder = ResultsBuilder(
            self.frozen_voters,
            self.truth_index,
            self.potential_guessers,
            self.proposals_browser)
        self.deadline_builder = DeadlineBuilder(
            self.time_to_guess,
            self.time_to_vote,
            self.guess_start,
            self.vote_start)
        self.time_left_builder = TimeLeftBuilder(
            self.guess_deadline,
            self.vote_deadline)
        self.stage_triggerer = StageTriggerer(
            self.publisher,
            self.project_id,
            self.code)
        self.db_editor = DataBaseEditor(
            self.ref,
            self.dict)
        self.local_path_builder = LocalPathBuilder(
            self.local_dir_path,
            self.id)
        self.block_builder = BlockBuilder(
            self.organizer_id,
            self.question,
            self.truth,
            self.truth_index,
            self.guessers,
            self.voters,
            self.frozen_guessers,
            self.frozen_voters,
            self.potential_voters,
            self.results,
            self.max_score,
            self.winners,
            self.graph_url,
            self.id_builder,
            self.time_left_builder,
            self.time_left_builder)
        self.view_builder = ViewBuilder(
            self.question,
            self.id_builder,
            self.proposals_browser,
            self.block_builder)
        self.slack_operator = SlackOperator(
            self.slack_client,
            self.channel_id,
            self.organizer_id,
            self.upper_ts,
            self.lower_ts,
            self.frozen_guessers,
            self.potential_voters,
            self.time_left_builder,
            self.block_builder,
            self.view_builder)
        self.exceptions = Exceptions(
            self.version,
            self.exists,
            self.channel_id,
            self.organizer_id,
            self.question,
            self.truth,
            self.time_to_guess,
            self.guessers,
            self.voters,
            self.potential_guessers,
            self.potential_voters,
            self.setup_submission,
            self.guess_stage_last_trigger,
            self.vote_stage_last_trigger,
            self.max_running_games,
            self.max_guessers,
            self.max_life_span,
            self.time_left_builder)
