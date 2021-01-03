from app import utils
from copy import deepcopy


def get_view(basename):
    return utils.jsons.get_json('views', basename)


exception_view_template = get_view('exception.json')
game_setup_view_template = get_view('game_setup.json')
guess_view_template = get_view('guess.json')
vote_view_template = get_view('vote.json')


def build_game_setup_view(id_):
    res = deepcopy(game_setup_view_template)
    res['callback_id'] = id_
    return res


def build_guess_view(id_, question):
    res = deepcopy(guess_view_template)
    res['callback_id'] = id_
    input_block = deepcopy(res['blocks'][0])
    question_block = utils.blocks.build_text_block(question)
    res['blocks'] = [question_block, input_block]
    return res


def collect_game_setup(game_setup_view):
    values = game_setup_view['state']['values']
    question = values['question']['question']['value']
    truth = values['truth']['truth']['value']
    time_to_guess = int((values['time_to_guess']['time_to_guess']
                               ['selected_option']['value']))*60
    return question, truth, time_to_guess


def collect_guess(guess_view):
    values = guess_view['state']['values']
    guess = values['guess']['guess']['value']
    return guess


def collect_vote(vote_view):
    values = vote_view['state']['values']
    vote = int(values['vote']['vote']['selected_option']['value'])
    return vote


class ViewBuilder:
    def __init__(self, game):
        self.game = game
        self.id_builder = utils.ids.IdBuilder(game.secret_prefix, game.id)
        self.proposals_browser = utils.proposals.ProposalsBrowser(game)
        self.block_builder = utils.blocks.BlockBuilder(game)

    def build_setup_view(self):
        id_ = self.id_builder.build_setup_view_id()
        return build_game_setup_view(id_)

    def build_guess_view(self):
        id_ = self.id_builder.build_guess_view_id()
        return build_guess_view(id_, self.game.question)

    def build_vote_view(self, voter):
        res = deepcopy(vote_view_template)
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
        res['blocks'] = [
            self.block_builder.build_own_guess_block(voter),
            utils.blocks.build_text_block(votable_proposals_msg),
            input_block]
        return res
