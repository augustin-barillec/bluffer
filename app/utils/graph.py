import networkx as nx
import matplotlib.pyplot as plt
import app.utils as utils


def build_graph(game):
    res = nx.DiGraph()
    res.add_node(game.truth_index)
    for r in game.results:
        res.add_node(r['index'])
        if 'vote_index' in r:
            res.add_edge(r['index'], r['vote_index'])
    return res


def draw_graph(game):
    g = game.graph

    side_length = int(len(game.results) / 2) + 7

    plt.figure(figsize=(side_length, side_length))

    plt.title('Voting graph')
    pos = nx.circular_layout(g)

    nx.draw_networkx_nodes(g, pos, node_color='#cc66ff', alpha=0.3,
                           node_size=1000)

    nx.draw_networkx_edges(g, pos, alpha=1.0, arrows=True, width=1.0)

    truth_label = {game.truth_index: 'Truth'}
    nx.draw_networkx_labels(g, pos, labels=truth_label, font_color='r')

    guesser_labels = {r['index']: '{}\n{}'.format(r['guesser_name'],
                                                  r['score'])
                      for r in game.results}

    indexes_of_winners = set(r['index'] for r in game.results
                             if r['guesser'] in game.winners)
    indexes_of_losers = set(r['index'] for r in game.results
                            if r['guesser'] not in game.winners)

    winner_labels = {k: guesser_labels[k] for k in indexes_of_winners}
    loser_labels = {k: guesser_labels[k] for k in indexes_of_losers}

    nx.draw_networkx_labels(g, pos, labels=loser_labels, font_color='b')
    nx.draw_networkx_labels(g, pos, labels=winner_labels, font_color='g')

    plt.savefig(game.graph_local_path)


def upload_graph_to_gs(game):
    return utils.storage.upload_to_gs(
        game.bucket, game.bucket_dir_name, game.graph_local_path)
