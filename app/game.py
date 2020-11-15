from slackclient import SlackClient
from copy import deepcopy
from app.utils import ids, proposals, time, pubsub, firestore, blocks, views, \
    slack

VERSION = 1


class IdBuilder:
    def __init__(self, secret_prefix, game_id):
        self.secret_prefix = secret_prefix
        self.game_id = game_id

    def get_team_id(self):
        return ids.game_id_to_team_id(self.game_id)

    def get_organizer_id(self):
        return ids.game_id_to_organizer_id(self.game_id)

    def get_channel_id(self):
        return ids.game_id_to_channel_id(self.game_id)

    def build_code(self):
        return self.game_id.encode("utf-8")

    def build_slack_object_id(self, object_name):
        return ids.build_slack_object_id(self.secret_prefix,
                                         object_name, self.game_id)

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


class Enumerator:

    def __init__(self, guessers, voters, potential_guessers, potential_voters):
        self.guessers = guessers
        self.voters = voters
        self.potential_guessers = potential_guessers
        self.potential_voters = potential_voters

    def compute_remaining_potential_guessers(self):
        return {pv: self.potential_guessers[pv]
                for pv in self.potential_guessers
                if pv not in self.guessers}

    def compute_remaining_potential_voters(self):
        return {pv: self.potential_voters[pv]
                for pv in self.potential_voters
                if pv not in self.voters}


class ProposalsBuilder:

    def __init__(self, game_id, frozen_guessers, truth):
        self.game_id = game_id
        self.frozen_guessers = frozen_guessers
        self.truth = truth

    def build_indexed_signed_proposals(self):
        return proposals.build_indexed_signed_proposals(
            self.frozen_guessers, self.truth, self.game_id)


class ProposalsBrowser:
    def __init__(self, indexed_signed_proposals):
        self.indexed_signed_proposals = indexed_signed_proposals

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


class ResultsBuilder:
    def __init__(
            self,
            frozen_voters,
            truth_index,
            potential_guessers,
            proposals_browser):
        self.frozen_voters = frozen_voters
        self.truth_index = truth_index
        self.potential_guessers = potential_guessers
        self.proposals_browser = proposals_browser

    def get_guesser_name(self, guesser):
        return self.potential_guessers[guesser]

    def compute_truth_score(self, voter):
        return int(self.frozen_voters[voter][1] == self.truth_index)

    def compute_bluff_score(self, voter):
        res = 0
        for voter_ in self.frozen_voters:
            voter_index = self.proposals_browser.author_to_index(voter)
            if self.frozen_voters[voter_][1] == voter_index:
                res += 2
        return res

    def build_results(self):
        results = []
        for isp in self.proposals_browser.indexed_signed_proposals:
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
            r['chosen_author'] = self.proposals_browser.index_to_author(
                vote_index)
            r['truth_score'] = self.compute_truth_score(author)
            r['bluff_score'] = self.compute_bluff_score(author)
            r['score'] = r['truth_score'] + r['bluff_score']
            results.append(r)

        def sort_key(r_):
            return 'vote_index' not in r_, -r_['score'], r_['guesser']

        results.sort(key=lambda r_: sort_key(r_))

        return results


class DeadlineBuilder:
    def __init__(self, time_to_guess, time_to_vote, guess_start, vote_start):
        self.time_to_guess = time_to_guess
        self.time_to_vote = time_to_vote
        self.guess_start = guess_start
        self.vote_start = vote_start

    def build_max_life_span(self):
        return self.time_to_guess + self.time_to_vote + 300

    def compute_guess_deadline(self):
        return time.compute_deadline(self.guess_start, self.time_to_guess)

    def compute_vote_deadline(self):
        return time.compute_deadline(self.vote_start, self.time_to_vote)


class TimeLeftBuilder:
    def __init__(self, guess_deadline, vote_deadline):
        self.guess_deadline = guess_deadline
        self.vote_deadline = vote_deadline

    def compute_time_left_to_guess(self):
        return time.compute_time_left(self.guess_deadline)

    def compute_time_left_to_vote(self):
        return time.compute_time_left(self.vote_deadline)


class StageTriggerer:
    def __init__(self, publisher, project_id, game_code):
        self.publisher = publisher
        self.project_id = project_id
        self.game_code = game_code

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

    def trigger_pre_result_stage(self):
        self.publish('topic_pre_result_stage')

    def trigger_result_stage(self):
        self.publish('topic_result_stage')


class DataBaseReader:
    def __init__(self, db, team_id, game_id):
        self.db = db
        self.team_id = team_id
        self.game_id = game_id

    def get_team_dict(self):
        return firestore.get_team_dict(self.db, self.team_id)

    def get_game_dict(self):
        return firestore.get_game_dict(self.db, self.team_id, self.game_id)

    def get_game_dicts(self):
        return firestore.get_game_dicts(self.db, self.team_id)

    def build_game_ref(self):
        return firestore.get_game_ref(self.db, self.team_id, self.game_id)


class DataBaseEditor:
    def __init__(self, game_ref, game_dict):
        self.game_ref = game_ref
        self.game_dict = game_dict

    def set_game_dict(self, merge=False):
        self.game_ref.set(self.game_dict, merge=merge)

    def delete_game(self):
        self.game_ref.delete()


class LocalPathBuilder:
    def __init__(self, local_dir_path, game_id):
        self.local_dir_path = local_dir_path
        self.game_id = game_id

    def build_basename(self, kind, ext):
        return '{}_{}.{}'.format(kind, self.game_id, ext)

    def build_local_file_path(self, basename):
        return self.local_dir_path + '/' + basename


class BlockBuilder:
    def __init__(
            self,
            organizer_id,
            question,
            truth,
            truth_index,
            guessers,
            voters,
            frozen_guessers,
            frozen_voters,
            potential_voters,
            results,
            max_score,
            winners,
            graph_url,
            id_builder,
            time_left_builder,
            proposals_browser):
        self.organizer_id = organizer_id
        self.question = question
        self.truth = truth
        self.truth_index = truth_index
        self.guessers = guessers
        self.voters = voters
        self.frozen_guessers = frozen_guessers
        self.frozen_voters = frozen_voters
        self.potential_voters = potential_voters
        self.max_score = max_score
        self.winners = winners
        self.results = results
        self.graph_url = graph_url
        self.id_builder = id_builder
        self.time_left_builder = time_left_builder
        self.proposals_browser = proposals_browser

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
        id_ = self.id_builder.build_guess_button_block_id()
        return blocks.build_button_block('Your guess', id_)

    def build_vote_button_block(self):
        id_ = self.id_builder.build_vote_button_block_id()
        return blocks.build_button_block('Your vote', id_)

    def build_guess_timer_block(self):
        time_left = self.time_left_builder.compute_time_left_to_guess()
        return blocks.build_guess_timer_block(time_left)

    def build_vote_timer_block(self):
        time_left = self.time_left_builder.compute_time_left_to_vote()
        return blocks.build_vote_timer_block(time_left)

    @staticmethod
    def build_users_blocks(users, kind, no_users_msg):
        msg = ids.build_users_msg(users, kind, no_users_msg)
        return blocks.build_text_block(msg)

    def compute_remaining_potential_voters(self):
        return {pv: self.potential_voters[pv]
                for pv in self.potential_voters
                if pv not in self.voters}

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
        indexed_anonymous_proposals = \
            self.proposals_browser.build_indexed_anonymous_proposals()
        for iap in indexed_anonymous_proposals:
            index = iap['index']
            proposal = iap['proposal']
            msg.append('{}) {}'.format(index, proposal))
        msg = '\n'.join(msg)
        return blocks.build_text_block(msg)

    def build_own_guess_block(self, voter):
        index, guess = self.proposals_browser.build_own_indexed_guess(voter)
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


class ViewBuilder:
    def __init__(self, question, id_builder, proposals_browser, block_builder):
        self.question = question
        self.id_builder = id_builder
        self.proposals_browser = proposals_browser
        self.block_builder = block_builder

    @staticmethod
    def build_exception_view(msg):
        return views.build_exception_view(msg)

    @staticmethod
    def build_exception_view_response(msg):
        return views.build_exception_view_response(msg)

    def build_setup_view(self):
        id_ = self.id_builder.build_setup_view_id()
        return views.build_game_setup_view(id_)

    def build_guess_view(self):
        id_ = self.id_builder.build_guess_view_id()
        return views.build_guess_view(id_, self.question)

    def build_vote_view(self, voter):
        res = deepcopy(views.vote_view_template)
        res['callback_id'] = self.id_builder.build_vote_view_id()
        input_block_template = res['blocks'][0]
        votable_proposals_msg = ['Voting options:']
        option_template = input_block_template['element']['options'][0]
        vote_options = []
        for viap in self.proposals_browser.\
                build_votable_indexed_anonymous_proposals(voter):
            index = viap['index']
            proposal = viap['proposal']
            votable_proposals_msg.append('{}) {}'.format(index, proposal))
            vote_option = deepcopy(option_template)
            vote_option['text']['text'] = '{}'.format(index)
            vote_option['value'] = '{}'.format(index)
            vote_options.append(vote_option)
        votable_proposals_msg = '\n'.join(votable_proposals_msg)
        input_block = input_block_template
        input_block['element']['options'] = vote_options
        res['blocks'] = [self.block_builder.build_own_guess_block(voter),
                         blocks.build_text_block(votable_proposals_msg),
                         input_block]
        return res


class SlackOperator:
    def __init__(
            self,
            slack_client,
            channel_id,
            organizer_id,
            upper_ts,
            lower_ts,
            frozen_guessers,
            potential_voters,
            time_left_builder,
            block_builder,
            view_builder):
        self.slack_client = slack_client
        self.channel_id = channel_id
        self.organizer_id = organizer_id
        self.upper_ts = upper_ts
        self.lower_ts = lower_ts
        self.frozen_guessers = frozen_guessers
        self.potential_voters = potential_voters
        self.time_left_builder = time_left_builder
        self.block_builder = block_builder
        self.view_builder = view_builder

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
        time_left_to_vote = self.time_left_builder.compute_time_left_to_vote()
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
        return self.post_message(
            self.block_builder.build_pre_guess_stage_upper_blocks())

    def post_pre_guess_stage_lower(self):
        return self.post_message(
            self.block_builder.build_pre_guess_stage_lower_blocks())

    def update_pre_vote_stage_upper(self):
        self.update_upper(
            self.block_builder.build_pre_vote_stage_upper_blocks())

    def update_pre_vote_stage_lower(self):
        self.update_lower(
            self.block_builder.build_pre_vote_stage_lower_blocks())

    def update_pre_result_stage_upper(self):
        self.update_upper(
            self.block_builder.build_pre_result_stage_upper_blocks())

    def update_pre_result_stage_lower(self):
        self.update_lower(
            self.block_builder.build_pre_result_stage_lower_blocks())

    def update_guess_stage_upper(self):
        self.update_upper(
            self.block_builder.build_guess_stage_upper_blocks())

    def update_guess_stage_lower(self):
        self.update_lower(
            self.block_builder.build_guess_stage_lower_blocks())

    def update_vote_stage_upper(self):
        self.update_upper(
            self.block_builder.build_vote_stage_upper_blocks())

    def update_vote_stage_lower(self):
        self.update_lower(
            self.block_builder.build_vote_stage_lower_blocks())

    def update_result_stage_upper(self):
        self.update_upper(
            self.block_builder.build_result_stage_upper_blocks())

    def update_result_stage_lower(self):
        self.update_lower(
            self.block_builder.build_result_stage_lower_blocks())

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
        self.open_view(trigger_id, self.view_builder.build_setup_view())

    def open_guess_view(self, trigger_id):
        self.open_view(trigger_id, self.view_builder.build_guess_view())

    def open_vote_view(self, trigger_id, voter):
        view = self.view_builder.build_vote_view(voter)
        self.open_view(trigger_id, view)


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
        self.upper_ts = self.dict.get('upper_ts')
        self.version = self.dict.get('version')
        self.vote_deadline = self.dict.get('vote_deadline')
        self.vote_stage_last_trigger = self.dict.get('vote_stage_last_trigger')
        self.vote_stage_over = self.dict.get('vote_stage_over')
        self.vote_start = self.dict.get('vote_start')
        self.voters = self.dict.get('voters')
        self.winners = self.dict.get('winners')

        self.truth_index = None
        self.graph_url = None

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
