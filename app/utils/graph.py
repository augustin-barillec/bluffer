import networkx as nx
import matplotlib.pyplot as plt
from app.utils import storage


class Graph:

    def __init__(self, game):
        self.game = game

    def build_graph(self):
        res = nx.DiGraph()
        res.add_node(self.game.truth_index)
        for r in self.game.results:
            res.add_node(r['index'])
            if 'vote_index' in r:
                res.add_edge(r['index'], r['vote_index'])
        return res

    def draw_graph(self):
        g = self.game.graph

        side_length = int(len(self.game.results) / 2) + 7

        plt.figure(figsize=(side_length, side_length))

        plt.title('Voting graph')
        pos = nx.circular_layout(g)

        nx.draw_networkx_nodes(g, pos, node_color='#cc66ff', alpha=0.3,
                               node_size=1000)

        nx.draw_networkx_edges(g, pos, alpha=1.0, arrows=True, width=1.0)

        truth_label = {self.game.truth_index: 'Truth'}
        nx.draw_networkx_labels(g, pos, labels=truth_label, font_color='r')

        guesser_labels = {r['index']: '{}\n{}'.format(r['guesser_name'],
                                                      r['score'])
                          for r in self.game.results}

        indexes_of_winners = set(r['index'] for r in self.game.results
                                 if r['guesser'] in self.game.winners)
        indexes_of_losers = set(r['index'] for r in self.game.results
                                if r['guesser'] not in self.game.winners)

        winner_labels = {k: guesser_labels[k] for k in indexes_of_winners}
        loser_labels = {k: guesser_labels[k] for k in indexes_of_losers}

        nx.draw_networkx_labels(g, pos, labels=loser_labels, font_color='b')
        nx.draw_networkx_labels(g, pos, labels=winner_labels, font_color='g')

        plt.savefig(self.game.graph_local_path)

    def upload_graph_to_gs(self):
        return storage.upload_to_gs(
            self.game.bucket, self.game.bucket_dir_name,
            self.game.graph_local_path)
