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


def build_guess_timer_block(time_left_to_guess):
    return build_timer_block(time_left_to_guess, 'guess')


def build_vote_timer_block(time_left_to_vote):
    return build_timer_block(time_left_to_vote, 'vote')


def build_title_block(organizer_id):
    msg = 'Game set up by {}!'.format(utils.users.user_display(organizer_id))
    return build_text_block(msg)


def build_question_block(question):
    return build_text_block(question)


def build_preparing_guess_stage_block():
    return build_text_block('Preparing guess stage...')


def build_preparing_vote_stage_block():
    return build_text_block('Preparing vote stage...')


def build_computing_results_stage_block():
    return build_text_block('Computing results :drum_with_drumsticks:')


def build_guess_button_block(id_builder):
    id_ = id_builder.build_guess_button_block_id()
    return build_button_block('Your guess', id_)


def build_vote_button_block(id_builder):
    id_ = id_builder.build_vote_button_block_id()
    return build_button_block('Your vote', id_)


def build_users_blocks(users, kind, no_users_msg):
    msg = utils.users.build_users_msg(users, kind, no_users_msg)
    return build_text_block(msg)


def build_remaining_potential_voters_block(potential_voters, voters):
    users = utils.users.compute_remaining_potential_voters(
        potential_voters, voters)
    kind = 'Potential voters'
    no_users_msg = 'Everyone has voted!'
    return build_users_blocks(users, kind, no_users_msg)


def build_guessers_block(guessers):
    users = guessers
    kind = 'Guessers'
    no_users_msg = 'No one has guessed yet.'
    return build_users_blocks(users, kind, no_users_msg)


def build_voters_block(voters):
    users = voters
    kind = 'Voters'
    no_users_msg = 'No one has voted yet.'
    return build_users_blocks(users, kind, no_users_msg)


def build_indexed_anonymous_proposals_block(proposals_browser):
    msg = ['Proposals:']
    indexed_anonymous_proposals = \
        proposals_browser.build_indexed_anonymous_proposals()
    for iap in indexed_anonymous_proposals:
        index = iap['index']
        proposal = iap['proposal']
        msg.append('{}) {}'.format(index, proposal))
    msg = '\n'.join(msg)
    return build_text_block(msg)


def build_own_guess_block(proposals_browser, voter):
    index, guess = proposals_browser.build_own_indexed_guess(voter)
    msg = 'Your guess: {}) {}'.format(index, guess)
    return build_text_block(msg)


def build_indexed_signed_guesses_msg(results):
    msg = []
    for r in deepcopy(results):
        player = utils.users.user_display(r['guesser'])
        index = r['index']
        guess = r['guess']
        r_msg = '• {}: {}) {}'.format(player, index, guess)
        msg.append(r_msg)
    msg = '\n'.join(msg)
    return msg


def build_conclusion_msg(
        frozen_guessers,
        frozen_voters,
        results,
        max_score,
        winners):
    lg = len(frozen_guessers)
    lv = len(frozen_voters)
    if lg == 0:
        return 'No one played this game :sob:.'
    if lg == 1:
        g = utils.users.user_display(list(frozen_guessers)[0])
        return 'Thanks for your guess, {}!'.format(g)
    if lv == 0:
        return 'No one voted :sob:.'
    if lv == 1:
        r = results[0]
        g = utils.users.user_display(r['guesser'])
        ca = r['chosen_author']
        if ca == 'Truth':
            return 'Bravo {}! You found the truth! :v:'.format(g)
        else:
            return 'Hey {}, at least you voted! :grimacing:'.format(g)
    if max_score == 0:
        return 'Zero points scored!'
    lw = len(winners)
    if lw == lv:
        return "Well, it's a draw! :scales:"
    if lw == 1:
        w = utils.users.user_display(winners[0])
        return 'And the winner is {}! :first_place_medal:'.format(w)
    if lw > 1:
        ws = [utils.users.user_display(w) for w in winners]
        msg_aux = ','.join(ws[:-1])
        msg_aux += ' and {}'.format(ws[-1])
        return 'And the winners are {}! :clap:'.format(msg_aux)


def build_truth_block(truth_index, truth, frozen_guessers):
    msg = '• Truth: '
    if len(frozen_guessers) == 0:
        msg += '{}'.format(truth)
    else:
        index = truth_index
        msg += '{}) {}'.format(index, truth)
    return build_text_block(msg)


def build_indexed_signed_guesses_block(results):
    msg = build_indexed_signed_guesses_msg(results)
    return build_text_block(msg)


def build_graph_block(graph_url):
    return build_image_block(url=graph_url, alt_text='Voting graph')


def build_conclusion_block(
        frozen_guessers, frozen_voters, results, max_score, winners):
    msg = build_conclusion_msg(
        frozen_guessers, frozen_voters, results, max_score, winners)
    return build_text_block(msg)


def build_pre_guess_stage_upper_blocks(organizer_id):
    title_block = build_title_block(organizer_id)
    preparing_guess_stage_block = build_preparing_guess_stage_block()
    return u([title_block, preparing_guess_stage_block])


def build_pre_guess_stage_lower_blocks():
    return d([])


def build_pre_vote_stage_upper_blocks(organizer_id, question):
    title_block = build_title_block(organizer_id)
    question_block = build_question_block(question)
    preparing_vote_stage_block = build_preparing_vote_stage_block()
    return u([title_block, question_block, preparing_vote_stage_block])


def build_pre_vote_stage_lower_blocks():
    return d([])


def build_pre_result_stage_upper_blocks(organizer_id, question):
    title_block = build_title_block(organizer_id)
    question_block = build_question_block(question)
    computing_results_stage_block = build_computing_results_stage_block()
    return u([title_block, question_block, computing_results_stage_block])


def build_pre_result_stage_lower_blocks():
    return d([])


def build_guess_stage_upper_blocks(organizer_id, question, id_builder):
    title_block = build_title_block(organizer_id)
    question_block = build_question_block(question)
    guess_button_block = build_guess_button_block(id_builder)
    return u([title_block, question_block, guess_button_block])


def build_guess_stage_lower_blocks(time_left_to_guess, guessers):
    guess_timer_block = build_guess_timer_block(time_left_to_guess)
    guessers_block = build_guessers_block(guessers)
    return d([guess_timer_block, guessers_block])


def build_vote_stage_upper_blocks(
        organizer_id, question, id_builder, proposals_browser):
    title_block = build_title_block(organizer_id)
    question_block = build_question_block(question)
    anonymous_proposals_block = build_indexed_anonymous_proposals_block(
        proposals_browser)
    vote_button_block = build_vote_button_block(id_builder)
    return u([title_block, question_block,
              anonymous_proposals_block, vote_button_block])


def build_vote_stage_lower_blocks(potential_voters, voters, time_left_to_vote):
    vote_timer_block = build_vote_timer_block(time_left_to_vote)
    remaining_potential_voters_block = build_remaining_potential_voters_block(
        potential_voters, voters)
    voters_block = build_voters_block(voters)
    return d([vote_timer_block, remaining_potential_voters_block,
              voters_block])


def build_result_stage_upper_blocks(
        title, question, truth, truth_index, results, frozen_guessers,
        frozen_voters, max_score, winners, graph_url):
    title_block = build_title_block(title)
    question_block = build_question_block(question)
    truth_block = build_truth_block(truth, truth_index, frozen_guessers)
    indexed_signed_guesses_block = build_indexed_signed_guesses_block(results)
    conclusion_block = build_conclusion_block(
        frozen_guessers, frozen_voters, results, max_score, winners)
    res = [title_block, question_block, truth_block,
           indexed_signed_guesses_block]
    if len(frozen_guessers) > 1 and len(frozen_voters) > 0:
        graph_block = build_graph_block(graph_url)
        res.append(graph_block)
    res.append(conclusion_block)
    res = u(res)
    return res


def build_result_stage_lower_blocks():
    return d([])
