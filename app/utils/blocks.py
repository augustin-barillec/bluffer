from app import utils
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


def build_guess_timer_block(game):
    return build_timer_block(game.time_left_to_guess, 'guess')


def build_vote_timer_block(game):
    return build_timer_block(game.time_left_to_vote, 'vote')


def build_title_block(game):
    msg = 'Game set up by {}!'.format(
        utils.users.user_display(game.organizer_id))
    return build_text_block(msg)


def build_question_block(game):
    return build_text_block(game.question)


def build_preparing_guess_stage_block():
    return build_text_block('Preparing guess stage...')


def build_preparing_vote_stage_block():
    return build_text_block('Preparing vote stage...')


def build_computing_results_stage_block():
    return build_text_block('Computing results :drum_with_drumsticks:')


def build_guess_button_block(game):
    id_ = game.id_builder.build_guess_button_block_id()
    return build_button_block('Your guess', id_)


def build_vote_button_block(game):
    id_ = game.id_builder.build_vote_button_block_id()
    return build_button_block('Your vote', id_)


def build_users_blocks(users, kind, no_users_msg):
    msg = utils.users.build_users_msg(users, kind, no_users_msg)
    return build_text_block(msg)


def build_remaining_potential_voters_block(game):
    kind = 'Potential voters'
    no_users_msg = 'Everyone has voted!'
    return build_users_blocks(
        game.remaining_potential_voters, kind, no_users_msg)


def build_guessers_block(game):
    users = game.guessers
    kind = 'Guessers'
    no_users_msg = 'No one has guessed yet.'
    return build_users_blocks(users, kind, no_users_msg)


def build_voters_block(game):
    users = game.voters
    kind = 'Voters'
    no_users_msg = 'No one has voted yet.'
    return build_users_blocks(users, kind, no_users_msg)


def build_indexed_anonymous_proposals_block(game):
    msg = ['Proposals:']
    indexed_anonymous_proposals = \
        game.proposals_browser.build_indexed_anonymous_proposals()
    for iap in indexed_anonymous_proposals:
        index = iap['index']
        proposal = iap['proposal']
        msg.append('{}) {}'.format(index, proposal))
    msg = '\n'.join(msg)
    return build_text_block(msg)


def build_own_guess_block(game):
    index, guess = game.proposals_browser.build_own_indexed_guess(game.voter)
    msg = 'Your guess: {}) {}'.format(index, guess)
    return build_text_block(msg)


def build_indexed_signed_guesses_msg(game):
    msg = []
    for r in deepcopy(game.results):
        player = utils.users.user_display(r['guesser'])
        index = r['index']
        guess = r['guess']
        r_msg = '• {}: {}) {}'.format(player, index, guess)
        msg.append(r_msg)
    msg = '\n'.join(msg)
    return msg


def build_conclusion_msg(game):
    lg = len(game.frozen_guessers)
    lv = len(game.frozen_voters)
    if lg == 0:
        return 'No one played this game :sob:.'
    if lg == 1:
        g = utils.users.user_display(list(game.frozen_guessers)[0])
        return 'Thanks for your guess, {}!'.format(g)
    if lv == 0:
        return 'No one voted :sob:.'
    if lv == 1:
        r = game.results[0]
        g = utils.users.user_display(r['guesser'])
        ca = r['chosen_author']
        if ca == 'Truth':
            return 'Bravo {}! You found the truth! :v:'.format(g)
        else:
            return 'Hey {}, at least you voted! :grimacing:'.format(g)
    if game.max_score == 0:
        return 'Zero points scored!'
    lw = len(game.winners)
    if lw == lv:
        return "Well, it's a draw! :scales:"
    if lw == 1:
        w = utils.users.user_display(game.winners[0])
        return 'And the winner is {}! :first_place_medal:'.format(w)
    if lw > 1:
        ws = [utils.users.user_display(w) for w in game.winners]
        msg_aux = ','.join(ws[:-1])
        msg_aux += ' and {}'.format(ws[-1])
        return 'And the winners are {}! :clap:'.format(msg_aux)


def build_truth_block(game):
    msg = '• Truth: '
    if len(game.frozen_guessers) == 0:
        msg += '{}'.format(game.truth)
    else:
        index = game.truth_index
        msg += '{}) {}'.format(index, game.truth)
    return build_text_block(msg)


def build_indexed_signed_guesses_block(game):
    msg = build_indexed_signed_guesses_msg(game)
    return build_text_block(msg)


def build_graph_block(game):
    return build_image_block(url=game.graph_url, alt_text='Voting graph')


def build_conclusion_block(game):
    msg = build_conclusion_msg(game)
    return build_text_block(msg)


def build_pre_guess_stage_upper_blocks(game):
    title_block = build_title_block(game)
    preparing_guess_stage_block = build_preparing_guess_stage_block()
    return u([title_block, preparing_guess_stage_block])


def build_pre_guess_stage_lower_blocks():
    return d([])


def build_pre_vote_stage_upper_blocks(game):
    title_block = build_title_block(game)
    question_block = build_question_block(game)
    preparing_vote_stage_block = build_preparing_vote_stage_block()
    return u([title_block, question_block, preparing_vote_stage_block])


def build_pre_vote_stage_lower_blocks():
    return d([])


def build_pre_result_stage_upper_blocks(game):
    title_block = build_title_block(game)
    question_block = build_question_block(game)
    computing_results_stage_block = build_computing_results_stage_block()
    return u([title_block, question_block, computing_results_stage_block])


def build_pre_result_stage_lower_blocks():
    return d([])


def build_guess_stage_upper_blocks(game):
    title_block = build_title_block(game)
    question_block = build_question_block(game)
    guess_button_block = build_guess_button_block(game)
    return u([title_block, question_block, guess_button_block])


def build_guess_stage_lower_blocks(game):
    guess_timer_block = build_guess_timer_block(game)
    guessers_block = build_guessers_block(game)
    return d([guess_timer_block, guessers_block])


def build_vote_stage_upper_blocks(game):
    title_block = build_title_block(game)
    question_block = build_question_block(game)
    anonymous_proposals_block = build_indexed_anonymous_proposals_block(game)
    vote_button_block = build_vote_button_block(game)
    return u([title_block, question_block,
              anonymous_proposals_block, vote_button_block])


def build_vote_stage_lower_blocks(game):
    vote_timer_block = build_vote_timer_block(game)
    remaining_potential_voters_block = \
        build_remaining_potential_voters_block(game)
    voters_block = build_voters_block(game)
    return d([vote_timer_block, remaining_potential_voters_block,
              voters_block])


def build_result_stage_upper_blocks(game):
    title_block = build_title_block(game)
    question_block = build_question_block(game)
    truth_block = build_truth_block(game)
    indexed_signed_guesses_block = build_indexed_signed_guesses_block(game)
    conclusion_block = build_conclusion_block(game)
    res = [title_block, question_block, truth_block,
           indexed_signed_guesses_block]
    if len(game) > 1 and len(game) > 0:
        graph_block = build_graph_block(game)
        res.append(graph_block)
    res.append(conclusion_block)
    res = u(res)
    return res


def build_result_stage_lower_blocks():
    return d([])
