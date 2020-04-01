# => slack command

game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40
}

# => pre_guess stage

game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
    'upper_ts': '1487598622',
    'lower_ts': '1477889966',
    'start_guess_datetime': '2020-03-05 19:50:01',
    'potential_players': ['u1', 'u2', 'u3', 'u4', 'u5']
}

# => guess stage

game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
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

# pre_vote stage

game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
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

# vote stage

pre_results_stage_game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
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

# results stage

results_stage_game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
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

