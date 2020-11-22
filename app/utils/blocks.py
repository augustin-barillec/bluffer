import app.utils as utils
from copy import deepcopy


def get_block(basename):
    return utils.jsons.get_json('blocks', basename)


divider_block = get_block('divider.json')
text_block_template = get_block('text.json')
button_block_template = get_block('button.json')
image_block_template = get_block('image.json')


def u(blocks):
    return [divider_block] + blocks


def d(blocks):
    return blocks + [divider_block]


def build_text_block(msg):
    res = deepcopy(text_block_template)
    res['text']['text'] = msg
    return res


def build_button_block(msg, id_):
    res = deepcopy(button_block_template)
    res['elements'][0]['text']['text'] = msg
    res['block_id'] = id_
    return res


def build_image_block(url, alt_text):
    res = deepcopy(image_block_template)
    res['image_url'] = url
    res['alt_text'] = alt_text
    return res


def build_timer_block(time_left, kind):
    assert kind in ('guess', 'vote')
    time_display = utils.time.build_time_display(time_left)
    msg = 'Time left to {}: {}'.format(kind, time_display)
    return build_text_block(msg)


class BlockBuilder:

    def __init__(self, game):
        self.game = game
        self.id_builder = utils.ids.IdBuilder(game.secret_prefix, game.id)

    def build_guess_timer_block(self):
        return build_timer_block(self.game.time_left_to_guess, 'guess')

    def build_vote_timer_block(self):
        return build_timer_block(self.game.time_left_to_vote, 'vote')

    def build_title_block(self):
        msg = 'Game set up by {}!'.format(
            utils.users.user_display(self.game.organizer_id))
        return build_text_block(msg)

    def build_question_block(self):
        return build_text_block(self.game.question)

    @staticmethod
    def build_preparing_guess_stage_block():
        return build_text_block('Preparing guess stage...')

    @staticmethod
    def build_preparing_vote_stage_block():
        return build_text_block('Preparing vote stage...')

    @staticmethod
    def build_computing_results_stage_block():
        return build_text_block('Computing results :drum_with_drumsticks:')

    def build_guess_button_block(self):
        id_ = self.id_builder.build_guess_button_block_id()
        return build_button_block('Your guess', id_)

    def build_vote_button_block(self):
        id_ = self.id_builder.build_vote_button_block_id()
        return build_button_block('Your vote', id_)

    @staticmethod
    def build_users_blocks(users, kind, no_users_msg):
        msg = utils.users.build_users_msg(users, kind, no_users_msg)
        return build_text_block(msg)

    def build_remaining_potential_voters_block(self):
        kind = 'Potential voters'
        no_users_msg = 'Everyone has voted!'
        return self.build_users_blocks(
            self.game.remaining_potential_voters, kind, no_users_msg)

    def build_guessers_block(self):
        users = self.game.guessers
        kind = 'Guessers'
        no_users_msg = 'No one has guessed yet.'
        return self.build_users_blocks(users, kind, no_users_msg)

    def build_voters_block(self):
        users = self.game.voters
        kind = 'Voters'
        no_users_msg = 'No one has voted yet.'
        return self.build_users_blocks(users, kind, no_users_msg)

    def build_indexed_anonymous_proposals_block(self):
        msg = ['Proposals:']
        indexed_anonymous_proposals = \
            utils.proposals.ProposalsBrowser(
                self.game).build_indexed_anonymous_proposals()
        for iap in indexed_anonymous_proposals:
            index = iap['index']
            proposal = iap['proposal']
            msg.append('{}) {}'.format(index, proposal))
        msg = '\n'.join(msg)
        return build_text_block(msg)

    def build_own_guess_block(self, voter):
        index, guess = utils.proposals.ProposalsBrowser(
            self.game).build_own_indexed_guess(voter)
        msg = 'Your guess: {}) {}'.format(index, guess)
        return build_text_block(msg)

    def build_indexed_signed_guesses_msg(self):
        msg = []
        for r in deepcopy(self.game.results):
            player = utils.users.user_display(r['guesser'])
            index = r['index']
            guess = r['guess']
            r_msg = '• {}: {}) {}'.format(player, index, guess)
            msg.append(r_msg)
        msg = '\n'.join(msg)
        return msg

    def build_conclusion_msg(self):
        lg = len(self.game.frozen_guessers)
        lv = len(self.game.frozen_voters)
        if lg == 0:
            return 'No one played this game :sob:.'
        if lg == 1:
            g = utils.users.user_display(list(self.game.frozen_guessers)[0])
            return 'Thanks for your guess, {}!'.format(g)
        if lv == 0:
            return 'No one voted :sob:.'
        if lv == 1:
            r = self.game.results[0]
            g = utils.users.user_display(r['guesser'])
            ca = r['chosen_author']
            if ca == 'Truth':
                return 'Bravo {}! You found the truth! :v:'.format(g)
            else:
                return 'Hey {}, at least you voted! :grimacing:'.format(g)
        if self.game.max_score == 0:
            return 'Zero points scored!'
        lw = len(self.game.winners)
        if lw == lv:
            return "Well, it's a draw! :scales:"
        if lw == 1:
            w = utils.users.user_display(self.game.winners[0])
            return 'And the winner is {}! :first_place_medal:'.format(w)
        if lw > 1:
            ws = [utils.users.user_display(w) for w in self.game.winners]
            msg_aux = ','.join(ws[:-1])
            msg_aux += ' and {}'.format(ws[-1])
            return 'And the winners are {}! :clap:'.format(msg_aux)

    def build_truth_block(self):
        msg = '• Truth: '
        if len(self.game.frozen_guessers) == 0:
            msg += '{}'.format(self.game.truth)
        else:
            index = self.game.truth_index
            msg += '{}) {}'.format(index, self.game.truth)
        return build_text_block(msg)

    def build_indexed_signed_guesses_block(self):
        msg = self.build_indexed_signed_guesses_msg()
        return build_text_block(msg)

    def build_graph_block(self):
        return build_image_block(
            url=self.game.graph_url, alt_text='Voting graph')

    def build_conclusion_block(self):
        msg = self.build_conclusion_msg()
        return build_text_block(msg)

    def build_pre_guess_stage_upper_blocks(self):
        title_block = self.build_title_block()
        preparing_guess_stage_block = self.build_preparing_guess_stage_block()
        return u([title_block, preparing_guess_stage_block])

    @staticmethod
    def build_pre_guess_stage_lower_blocks():
        return d([])

    def build_pre_vote_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        preparing_vote_stage_block = self.build_preparing_vote_stage_block()
        return u([title_block, question_block, preparing_vote_stage_block])

    @staticmethod
    def build_pre_vote_stage_lower_blocks():
        return d([])

    def build_pre_result_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        computing_results_stage_block = \
            self.build_computing_results_stage_block()
        return u([title_block, question_block, computing_results_stage_block])

    @staticmethod
    def build_pre_result_stage_lower_blocks():
        return d([])

    def build_guess_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        guess_button_block = self.build_guess_button_block()
        return u([title_block, question_block, guess_button_block])

    def build_guess_stage_lower_blocks(self):
        guess_timer_block = self.build_guess_timer_block()
        guessers_block = self.build_guessers_block()
        return d([guess_timer_block, guessers_block])

    def build_vote_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        anonymous_proposals_block = \
            self.build_indexed_anonymous_proposals_block()
        vote_button_block = self.build_vote_button_block()
        return u([title_block, question_block,
                  anonymous_proposals_block, vote_button_block])

    def build_vote_stage_lower_blocks(self):
        vote_timer_block = self.build_vote_timer_block()
        remaining_potential_voters_block = \
            self.build_remaining_potential_voters_block()
        voters_block = self.build_voters_block()
        return d([vote_timer_block, remaining_potential_voters_block,
                  voters_block])

    def build_result_stage_upper_blocks(self):
        title_block = self.build_title_block()
        question_block = self.build_question_block()
        truth_block = self.build_truth_block()
        indexed_signed_guesses_block = \
            self.build_indexed_signed_guesses_block()
        conclusion_block = self.build_conclusion_block()
        res = [title_block, question_block, truth_block,
               indexed_signed_guesses_block]
        if len(self.game.frozen_guessers) > 1 and \
                len(self.game.frozen_voters) > 0:
            graph_block = self.build_graph_block()
            res.append(graph_block)
        res.append(conclusion_block)
        res = u(res)
        return res

    @staticmethod
    def build_result_stage_lower_blocks():
        return d([])
