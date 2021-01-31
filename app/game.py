from slackclient import SlackClient
from app import utils
from app.version import VERSION


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

        self.id_builder = utils.ids.IdBuilder(self.secret_prefix, self.id)
        self.team_id = self.id_builder.get_team_id()
        self.channel_id = self.id_builder.get_channel_id()
        self.organizer_id = self.id_builder.get_organizer_id()

        self.stage_triggerer = utils.pubsub.StageTriggerer(
            self.publisher, self.project_id, self.id)

        self.bucket_dir_name = self.team_id
        self.graph_basename = '{}_graph.png'.format(self.id)
        self.graph_local_path = self.local_dir_path + '/' + self.graph_basename

        self.firestore_reader = utils.firestore.FirestoreReader(
            self.db, self.team_id, self.channel_id, self.id)
        self.ref = self.firestore_reader.build_game_ref()
        self.team_dict = self.firestore_reader.get_team_dict()

        slack_token = self.team_dict['slack_token']
        self.slack_client = SlackClient(slack_token)

        channel_dicts = self.firestore_reader.get_channel_dicts()
        if self.channel_id in channel_dicts:
            params = self.firestore_reader.get_channel_dict()
        else:
            params = self.team_dict

        self.max_guessers_per_game = params['max_guessers_per_game']
        self.max_running_games_per_organizer = \
            params['max_running_games_per_organizer']
        self.max_total_running_games = params['max_total_running_games']
        self.post_delete = params['post_delete']
        self.time_to_guess_options = params['time_to_guess_options']
        self.time_to_vote = params['time_to_vote']

        self.exists = True
        self.dict = self.firestore_reader.get_game_dict()
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
        self.max_guessers = self.dict.get('max_guessers')
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

        self.now = utils.time.get_now()

        if self.guess_deadline:
            self.time_left_to_guess = utils.time.datetime1_minus_datetime2(
                self.guess_deadline, self.now)

        if self.vote_deadline:
            self.time_left_to_vote = utils.time.datetime1_minus_datetime2(
                self.vote_deadline, self.now)

        if self.potential_guessers is not None and self.guessers is not None:
            self.remaining_potential_guessers = utils.users.\
                compute_remaining_potential_guessers(
                    self.potential_guessers, self.guessers)

        if self.potential_voters is not None and self.voters is not None:
            self.remaining_potential_voters = utils.users.\
                compute_remaining_potential_voters(
                    self.potential_voters, self.voters)
