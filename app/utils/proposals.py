import random
from app.utils import ids


def build_indexed_signed_proposals(frozen_guessers, truth, random_seed):
    sorted_frozen_guessers = ids.sort_users(frozen_guessers)
    res = [(k, frozen_guessers[k][1]) for k in sorted_frozen_guessers]
    res.append(('Truth', truth))
    random.seed(random_seed)
    random.shuffle(res)
    res = [(index, author, proposal)
           for index, (author, proposal) in enumerate(res, 1)]
    res = [{'index': index, 'author': author, 'proposal': proposal}
           for index, author, proposal in res]
    return res
