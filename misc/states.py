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
    'potential_guessers': {'u1': 'n1', 'u2': 'n2', 'u3': 'n3'}
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
    'potential_guessers': {'u1': 'n1', 'u2': 'n2', 'u3': 'n3'},
    'guessers': {'u1': 'guess1', 'u2': 'guess2'}
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
    'potential_guessers': {'u1': 'n1', 'u2': 'n2', 'u3': 'n3'},
    'guessers': {'u1': 'guess1', 'u2': 'guess2'},
    'order': ['u2', 'Truth', 'u1']
}

# vote stage

game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
    'upper_ts': '1487598622',
    'lower_ts': '1477889966',
    'start_guess_datetime': '2020-03-05 19:50:01',
    'start_vote_datetime': '2020-03-05 19:57:01',
    'potential_guessers': {'u1': 'n1', 'u2': 'n2', 'u3': 'n3'},
    'guessers': {'u1': 'guess1', 'u2': 'guess2'},
    'order': ['u2', 'Truth', 'u1'],
    'voters': {'u2': 1}
}

# results stage

game = {
    'question': '?',
    'truth': '!',
    'time_to_guess': 60,
    'time_to_vote': 40,
    'upper_ts': '1487598622',
    'lower_ts': '1477889966',
    'start_guess_datetime': '2020-03-05 19:50:01',
    'start_vote_datetime': '2020-03-05 19:57:01',
    'potential_guessers': {'u1': 'n1', 'u2': 'n2', 'u3': 'n3'},
    'guessers': {'u1': 'guess1', 'u2': 'guess2'},
    'order': ['u2', 'Truth', 'u1'],
    'voters': {'u2': 1}
}

