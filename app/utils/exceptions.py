from app import utils
from flask import make_response
from app.version import VERSION


class ExceptionsHandler:

    def __init__(self, game):
        self.game = game

    @property
    def slack_operator(self):
        return utils.slack.SlackOperator(self.game)

    @staticmethod
    def count_running_games(game_dicts):
        return len([g for g in game_dicts if 'result_stage_over' not in g])

    @staticmethod
    def get_running_organizer_ids(game_dicts):
        return [utils.ids.game_id_to_organizer_id(gid) for gid in game_dicts
                if 'result_stage_over' not in game_dicts[gid]]

    def max_nb_of_running_games_reached(self, game_dicts):
        nb_of_running_games = self.count_running_games(game_dicts)
        return nb_of_running_games >= self.game.max_running_games

    def organizer_has_another_game_running(self, game_dicts):
        running_organizer_ids = self.get_running_organizer_ids(game_dicts)
        return self.game.organizer_id in running_organizer_ids

    def app_is_in_conversation(self, app_conversations):
        return self.game.channel_id in [c['id'] for c in app_conversations]

    def no_time_left_to_guess(self):
        return self.game.time_left_to_guess <= 0

    def max_nb_of_guessers_reached(self):
        return len(self.game.guessers) >= self.game.max_guessers

    def no_time_left_to_vote(self):
        return self.game.time_left_to_vote <= 0

    def game_is_too_old(self):
        now = utils.time.get_now()
        delta = utils.time.datetime1_minus_datetime2(
            now, self.game.setup_submission)
        return delta >= self.game.max_life_span

    def version_is_bad(self):
        return self.game.version != VERSION

    def game_is_dead(self):
        if not self.game.exists:
            return True
        if self.game.setup_submission is None:
            return True
        if self.game.max_life_span is None:
            return True
        if self.game_is_too_old():
            return True
        if self.game.version is None:
            return True
        if self.version_is_bad():
            return True
        return False

    @staticmethod
    def stage_was_recently_trigger(last_trigger):
        if last_trigger is None:
            return False
        now = utils.time.get_now()
        delta = utils.time.datetime1_minus_datetime2(now, last_trigger)
        return delta < 30

    def guess_stage_was_recently_trigger(self):
        return self.stage_was_recently_trigger(
            self.game.guess_stage_last_trigger)

    def vote_stage_was_recently_trigger(self):
        return self.stage_was_recently_trigger(
            self.game.vote_stage_last_trigger)

    @staticmethod
    def build_organizer_has_another_game_running_msg():
        return ('You are the organizer of a game which is sill running. '
                'You can only have one game running at a time.')

    def build_game_is_dead_msg(self):
        if self.game_is_dead():
            return 'This game is dead!'

    def build_aborted_cause_recently_triggered_msg(self):
        return 'aborted cause recently triggered, game_id={}'.format(
            self.game.id)

    def build_aborted_cause_already_triggered_msg(self):
        return 'aborted cause already triggered, game_id={}'.format(
            self.game.id)

    def build_slash_command_exception_msg(self, game_dicts, app_conversations):
        if self.max_nb_of_running_games_reached(game_dicts):
            msg_template = ('There are already {} games running! '
                            'This is the maximal number allowed.')
            msg = msg_template.format(self.game.max_running_games)
            return msg
        if self.organizer_has_another_game_running(game_dicts):
            return self.build_organizer_has_another_game_running_msg()
        if not self.app_is_in_conversation(app_conversations):
            return 'Please invite me first to this conversation!'

    def build_setup_submission_exception_msg(self, game_dicts):
        if self.max_nb_of_running_games_reached(game_dicts):
            msg = ('Question: {}\n\n'
                   'Answer: {}\n\n'
                   'There are already {} games running! '
                   'This is the maximal number allowed.'.format(
                    self.game.question, self.game.truth,
                    self.game.max_running_games))
            return msg
        if self.organizer_has_another_game_running(game_dicts):
            return self.build_organizer_has_another_game_running_msg()

    def build_guess_submission_exception_msg(self, guess):
        if self.no_time_left_to_guess():
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
            msg = msg_template.format(guess, self.game.max_guessers)
            return msg

    def build_vote_submission_exception_msg(self, vote):
        if self.no_time_left_to_vote():
            msg = ('Your vote: proposal {}.\n\n'
                   'It will not be taken into account '
                   'because the voting deadline has passed!'.format(vote))
            return msg

    def build_guess_click_exception_msg(self, user_id):
        if user_id == self.game.organizer_id:
            return 'As the organizer of this game, you cannot guess!'
        if user_id in self.game.guessers:
            return 'You have already guessed!'
        if user_id not in self.game.potential_guessers:
            msg = ('You cannot guess because when the set up of this '
                   'game started, you were not a member of this channel.')
            return msg
        if self.max_nb_of_guessers_reached():
            msg_template = ('You cannot guess because there are already {} '
                            'guessers. This is the maximal number allowed.')
            msg = msg_template.format(self.game.max_guessers)
            return msg
        if user_id == 'Truth':
            msg = ("You cannot play bluffer because your slack user_id is "
                   "'Truth', which is a reserved word for the game.")
            return msg

    def build_vote_click_exception_msg(self, user_id):
        if user_id not in self.game.potential_voters:
            return 'Only guessers can vote!'
        if user_id in self.game.voters:
            return 'You have already voted!'

    def handle_is_dead_exception(self, user_id):
        exception_msg = self.build_game_is_dead_msg()
        if exception_msg:
            self.slack_operator.post_ephemeral(user_id, exception_msg)
            return make_response('', 200)

    def handle_slash_command_exceptions(self, organizer_id):
        game_dicts = self.game.firestore_reader.get_game_dicts()
        app_conversations = self.slack_operator.get_app_conversations()
        exception_msg = self.build_slash_command_exception_msg(
            game_dicts, app_conversations)
        if exception_msg:
            self.slack_operator.post_ephemeral(organizer_id, exception_msg)
            return make_response('', 200)

    def handle_setup_submission_exceptions(self, organizer_id):
        game_dicts = self.game.firestore_reader.get_game_dicts()
        exception_msg = self.build_setup_submission_exception_msg(game_dicts)
        if exception_msg:
            self.slack_operator.post_ephemeral(organizer_id, exception_msg)
            return make_response('', 200)

    def handle_guess_submission_exceptions(self, guesser_id, guess):
        exception_msg = self.build_guess_submission_exception_msg(guess)
        if exception_msg:
            self.slack_operator.post_ephemeral(guesser_id, exception_msg)
            return make_response('', 200)

    def handle_vote_submission_exceptions(self, voter_id, vote):
        exception_msg = self.build_vote_submission_exception_msg(vote)
        if exception_msg:
            self.slack_operator.post_ephemeral(voter_id, exception_msg)
            return make_response('', 200)

    def handle_guess_click_exceptions(self, guesser_id):
        exception_msg = self.build_guess_click_exception_msg(guesser_id)
        if exception_msg:
            self.slack_operator.post_ephemeral(guesser_id, exception_msg)
            return make_response('', 200)

    def handle_vote_click_exceptions(self, voter_id):
        exception_msg = self.build_vote_click_exception_msg(voter_id)
        if exception_msg:
            self.slack_operator.post_ephemeral(voter_id, exception_msg)
            return make_response('', 200)

    def handle_pre_guess_stage_exceptions(self):
        if self.game_is_dead():
            return make_response('', 200)
        if self.game.pre_guess_stage_already_triggered:
            self.game.logger.info(
                self.build_aborted_cause_already_triggered_msg())
            return make_response('', 200)

    def handle_guess_stage_exceptions(self):
        if self.game_is_dead():
            return make_response('', 200)
        if self.game.guess_stage_over:
            return make_response('', 200)
        if self.guess_stage_was_recently_trigger():
            self.game.logger.info(
                self.build_aborted_cause_recently_triggered_msg())
            return make_response('', 200)

    def handle_pre_vote_stage_exceptions(self):
        if self.game_is_dead():
            return make_response('', 200)
        if self.game.pre_vote_stage_already_triggered:
            self.game.logger.info(
                self.build_aborted_cause_already_triggered_msg())
            return make_response('', 200)

    def handle_vote_stage_exceptions(self):
        if self.game_is_dead():
            return make_response('', 200)
        if self.game.vote_stage_over:
            return make_response('', 200)
        if self.vote_stage_was_recently_trigger():
            self.game.logger.info(
                self.build_aborted_cause_recently_triggered_msg())
            return make_response('', 200)

    def handle_pre_results_stage_exceptions(self):
        if self.game_is_dead():
            return make_response('', 200)
        if self.game.pre_result_stage_already_triggered:
            self.game.logger.info(
                self.build_aborted_cause_already_triggered_msg())
            return make_response('', 200)

    def handle_results_stage_exceptions(self):
        if self.game_is_dead():
            return make_response('', 200)
        if self.game.result_stage_over:
            return make_response('', 200)
