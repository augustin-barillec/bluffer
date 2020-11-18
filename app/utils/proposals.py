import random
from app import utils


def build_indexed_signed_proposals(frozen_guessers, truth, random_seed):
    sorted_frozen_guessers = utils.users.sort_users(frozen_guessers)
    res = [(k, frozen_guessers[k][1]) for k in sorted_frozen_guessers]
    res.append(('Truth', truth))
    random.seed(random_seed)
    random.shuffle(res)
    res = [(index, author, proposal)
           for index, (author, proposal) in enumerate(res, 1)]
    res = [{'index': index, 'author': author, 'proposal': proposal}
           for index, author, proposal in res]
    return res


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