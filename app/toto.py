class Slack:

    def __init__(self, game):
        self.game = game

    def post_message(self):
        pass

    def update_message(self):
        pass


class Graph:

    def __init__(self, game):
        self.game = game

    def draw_graph(self):
        pass


class Game:

    def __init__(self, toto, tutu, titi, tata):
        self.toto = toto
        self.tutu = tutu
        self.titi = titi
        self.tata = tata


g = Game(toto=1, tutu=2, titi=3, tata=5)

slack = Slack(g)
graph = Graph(g)

slack.post_message()
slack.update_message()
graph.draw_graph()