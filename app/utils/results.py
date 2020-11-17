class ResultsBuilder:
    def __init__(
            self,
            frozen_voters,
            truth_index,
            potential_guessers,
            proposals_browser):
        self.frozen_voters = frozen_voters
        self.truth_index = truth_index
        self.potential_guessers = potential_guessers
        self.proposals_browser = proposals_browser

    def get_guesser_name(self, guesser):
        return self.potential_guessers[guesser]

    def compute_truth_score(self, voter):
        return int(self.frozen_voters[voter][1] == self.truth_index)

    def compute_bluff_score(self, voter):
        res = 0
        for voter_ in self.frozen_voters:
            voter_index = self.proposals_browser.author_to_index(voter)
            if self.frozen_voters[voter_][1] == voter_index:
                res += 2
        return res

    def build_results(self):
        results = []
        for isp in self.proposals_browser.indexed_signed_proposals:
            index = isp['index']
            author = isp['author']
            proposal = isp['proposal']
            r = dict()
            if author == 'Truth':
                continue
            r['index'] = index
            r['guesser'] = author
            r['guesser_name'] = self.get_guesser_name(author)
            r['guess'] = proposal
            if author not in self.frozen_voters:
                r['score'] = 0
                results.append(r)
                continue
            vote_index = self.frozen_voters[author][1]
            r['vote_index'] = vote_index
            r['chosen_author'] = self.proposals_browser.index_to_author(
                vote_index)
            r['truth_score'] = self.compute_truth_score(author)
            r['bluff_score'] = self.compute_bluff_score(author)
            r['score'] = r['truth_score'] + r['bluff_score']
            results.append(r)

        def sort_key(r_):
            return 'vote_index' not in r_, -r_['score'], r_['guesser']

        results.sort(key=lambda r_: sort_key(r_))

        return results


def compute_max_score(results):
    scores = [r['score'] for r in results if 'score' in r]
    return scores[0]


def compute_winners(results, max_score):
    res = []
    for r in results:
        if r['score'] == max_score:
            res.append(r['guesser'])
    return res
