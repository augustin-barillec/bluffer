# => game_set_up_view_submission

pre_guess_stage_game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40
}

# => pre_guess_stage_to_guess_stage

guess_stage_game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
    'stage': 'guess_stage',
    'upper_ts': '1487598622',
    'lower_ts': '1477889966',
    'start_guess_datetime': '2020-03-05 19:50:01',
    'potential_players': ['u1', 'u2', 'u3', 'u4', 'u5']
}


# => guess_stage_to_pre_vote_stage

pre_vote_stage_game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
    'stage': 'pre_vote_stage',
    'upper_ts': '1487598622',
    'lower_ts': '1477889966',
    'start_guess_datetime': '2020-03-05 19:50:01',
    'potential_players': ['u1', 'u2', 'u3', 'u4', 'u5'],
    'players': {
        'u1': {'name': 'n1', 'guess': 'guess1'},
        'u2': {'name': 'n2', 'guess': 'guess2'},
        'u3': {'name': 'n3', 'guess': 'guess3'}
    }
}

# => pre_vote_stage_to_vote_stage

vote_stage_game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
    'stage': 'pre_vote_stage',
    'upper_ts': '1487598622',
    'lower_ts': '1477889966',
    'start_guess_datetime': '2020-03-05 19:50:01',
    'start_vote_datetime': '2020-03-05 19:57:01',
    'potential_players': ['u1', 'u2', 'u3', 'u4', 'u5'],
    'players': {
        'u1': {'name': 'n1', 'guess': 'guess1'},
        'u2': {'name': 'n2', 'guess': 'guess2'},
        'u3': {'name': 'n3', 'guess': 'guess3'}
    }
}

# => vote_stage_to_pre_results_stage

pre_results_stage_game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
    'stage': 'vote_stage',
    'upper_ts': '1487598622',
    'lower_ts': '1477889966',
    'start_guess_datetime': '2020-03-05 19:50:01',
    'start_vote_datetime': '2020-03-05 19:57:01',
    'potential_players': ['u1', 'u2', 'u3', 'u4', 'u5'],
    'players': {
        'u1': {'name': 'n1', 'guess': 'guess1', 'vote': 2},
        'u2': {'name': 'n2', 'guess': 'guess2', 'vote': 3},
        'u3': {'name': 'n3', 'guess': 'guess3', 'vote': 4}
    }
}

# => pre_results_stage_to_results_stage

results_stage_game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
    'stage': 'results_stage',
    'upper_ts': '1487598622',
    'lower_ts': '1477889966',
    'start_guess_datetime': '2020-03-05 19:50:01',
    'start_vote_datetime': '2020-03-05 19:57:01',
    'potential_players': ['u1', 'u2', 'u3', 'u4', 'u5'],
    'players': {
        'u1': {'name': 'n1', 'guess': 'guess1', 'vote': 2},
        'u2': {'name': 'n2', 'guess': 'guess2', 'vote': 3},
        'u3': {'name': 'n3', 'guess': 'guess3', 'vote': 4}
    }
}

# => results_stage_to_over_stage

over_stage_game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
    'stage': 'results_stage',
    'upper_ts': '1487598622',
    'lower_ts': '1477889966',
    'start_guess_datetime': '2020-03-05 19:50:01',
    'start_vote_datetime': '2020-03-05 19:57:01',
    'potential_players': ['u1', 'u2', 'u3', 'u4', 'u5'],
    'players': {
        'u1': {'name': 'n1', 'guess': 'guess1', 'vote': 2},
        'u2': {'name': 'n2', 'guess': 'guess2', 'vote': 3},
        'u3': {'name': 'n3', 'guess': 'guess3', 'vote': 4}
    }
}