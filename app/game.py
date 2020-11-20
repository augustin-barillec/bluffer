from slackclient import SlackClient
from app.version import VERSION
from app import utils


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
        self.code = self.id_builder.build_code()
        self.team_id = self.id_builder.get_team_id()
        self.channel_id = self.id_builder.get_channel_id()
        self.organizer_id = self.id_builder.get_organizer_id()

        self.bucket_dir_name = self.team_id
        self.graph_basename = '{}_graph.png'.format(self.id)
        self.graph_local_path = self.local_dir_path + '/' + self.graph_basename

        self.firestore_reader = utils.firestore.FirestoreReader(
            self.db, self.team_id, self.id)
        self.ref = self.firestore_reader.build_game_ref()
        self.team_dict = self.firestore_reader.get_team_dict()

        self.max_guessers = self.team_dict['max_guessers']
        self.max_running_games = self.team_dict['max_running_games']
        self.post_clean = self.team_dict['post_clean']
        self.slack_token = self.team_dict['slack_token']
        self.time_to_vote = self.team_dict['time_to_vote']

        self.slack_client = SlackClient(self.slack_token)

        self.exists = True
        self.dict = self.firestore_reader.get_game_dict()
        if not self.dict:
            self.exists = False
            return

        self.firestore_editor = utils.firestore.FirestoreEditor(
            self.ref, self.dict)

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

        if self.guess_deadline is not None:
            self.time_left_to_guess = utils.time.compute_time_left(
                self.guess_deadline)
        if self.vote_deadline is not None:
            self.time_left_to_vote = utils.time.compute_time_left(
                self.vote_deadline)

        if self.potential_guessers is not None and self.guessers is not None:
            self.remaining_potential_guessers = \
                utils.users.compute_remaining_potential_guessers(
                    self.potential_guessers, self.guessers)
        if self.potential_voters is not None and self.voters is not None:
            self.remaining_potential_voters = \
                utils.users.compute_remaining_potential_voters(
                    self.potential_voters, self.voters)

        self.stage_triggerer = utils.pubsub.StageTriggerer(
            self.publisher,
            self.project_id,
            self.code)
        self.proposals_browser = utils.proposals.ProposalsBrowser(
            self.indexed_signed_proposals)
        self.results_builder = utils.results.ResultsBuilder(
            self.frozen_voters,
            self.truth_index,
            self.potential_guessers,
            self.proposals_browser)
        self.view_builder = utils.views.ViewBuilder(
            self.question,
            self.id_builder,
            self.proposals_browser)
        self.slack_operator = utils.slack.SlackOperator(
            self.slack_client,
            self.channel_id,
            self.organizer_id,
            self.upper_ts,
            self.lower_ts,
            self.view_builder)
