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