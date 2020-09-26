from copy import deepcopy
from bluffer.utils import jsons, ids, blocks


def get_view(basename):
    return jsons.get_json('views', basename)


exception_view_template = get_view('exception.json')
game_setup_view_template = get_view('game_setup.json')
guess_view_template = get_view('guess.json')
vote_view_template = get_view('vote.json')


def build_exception_view(msg):
    res = deepcopy(exception_view_template)
    res['blocks'][0]['text']['text'] = msg
    return res


def build_game_setup_view(id_):
    res = deepcopy(game_setup_view_template)
    res['callback_id'] = id_
    return res


def build_guess_view(id_, question):
    res = deepcopy(guess_view_template)
    res['callback_id'] = id_
    input_block = deepcopy(res['blocks'][0])
    question_block = blocks.build_text_block(question)
    res['blocks'] = [question_block, input_block]
    return res


def build_vote_view(secret_prefix, game_id, voter, guessers, truth):
    res = deepcopy(vote_view_template)
    id_ = ids.build_slack_object_id(secret_prefix, 'vote_view', game_id)
    res['callback_id'] = id_
    input_block_template = res['blocks'][0]
    votable_proposals_msg = ['Voting options:']
    option_template = input_block_template['element']['options'][0]
    vote_options = []

    def build_votable_proposals(voter):
        res = []
        for index, author, proposal in signed_proposals:
            if author != voter:
                res.append((index, proposal))
        return res

    for index, proposal in build_votable_proposals(voter):
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


    id_ = ids.build_slack_object_id(secret_prefix, 'vote_view', game_id)
    signed_proposals = build_signed_proposals(guessers, truth)
    anonymous_proposals_block = build_anonymous_proposals_block(signed_proposals)


def build_exception_view_response(msg):
    exception_view = build_exception_view(msg)
    return {'response_action': 'update', 'view': exception_view}


def open_view(slack_client, trigger_id, view):
    slack_client.api_call(
        'views.open',
        trigger_id=trigger_id,
        view=view)


def open_exception_view(slack_client, trigger_id, msg):
    exception_view = build_exception_view(msg)
    open_view(slack_client, trigger_id, exception_view)


def open_game_setup_view(slack_client, trigger_id, secret_prefix, game_id):
    game_setup_view = build_game_setup_view(secret_prefix, game_id)
    open_view(slack_client, trigger_id, game_setup_view)


def open_guess_view(slack_client, trigger_id,
                    secret_prefix, game_id, question):
    guess_view = build_guess_view(secret_prefix, game_id, question)
    open_view(slack_client, trigger_id, guess_view)


def open_vote_view(slack_client, trigger_id, secret_prefix, game_id, question,
                   voter):
    vote_view = build_vote_view(secret_prefix, game_id, voter)
    open_view(slack_client, trigger_id, vote_view)


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
