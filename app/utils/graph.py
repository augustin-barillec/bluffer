import networkx as nx
import matplotlib.pyplot as plt


def build_graph(results, truth_index):
    res = nx.DiGraph()
    res.add_node(truth_index)
    for r in results:
        res.add_node(r['index'])
        if 'vote_index' in r:
            res.add_edge(r['index'], r['vote_index'])
    return res


def draw_graph(
        graph,
        truth_index,
        results,
        winners,
        graph_local_path):
    g = graph

    side_length = int(len(results) / 2) + 7

    plt.figure(figsize=(side_length, side_length))

    plt.title('Voting graph')
    pos = nx.circular_layout(g)

    nx.draw_networkx_nodes(g, pos, node_color='#cc66ff', alpha=0.3,
                           node_size=1000)

    nx.draw_networkx_edges(g, pos, alpha=1.0, arrows=True, width=1.0)

    truth_label = {truth_index: 'Truth'}
    nx.draw_networkx_labels(g, pos, labels=truth_label, font_color='r')

    guesser_labels = {r['index']: '{}\n{}'.format(r['guesser_name'],
                                                  r['score'])
                      for r in results}

    indexes_of_winners = set(r['index'] for r in results
                             if r['guesser'] in winners)
    indexes_of_losers = set(r['index'] for r in results
                            if r['guesser'] not in winners)

    winner_labels = {k: guesser_labels[k] for k in indexes_of_winners}
    loser_labels = {k: guesser_labels[k] for k in indexes_of_losers}

    nx.draw_networkx_labels(g, pos, labels=loser_labels, font_color='b')
    nx.draw_networkx_labels(g, pos, labels=winner_labels, font_color='g')

    plt.savefig(graph_local_path)
