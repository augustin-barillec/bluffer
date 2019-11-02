from bluffer.utils import get_modal, get_message

game_setup = get_modal(__file__, 'game_setup.json')
board_blocks = get_message(__file__, 'board.json')['blocks']


class Game:
    def __init__(self, trigger_id, channel_id, organizer_id, slack_client):
        self.trigger_id = trigger_id
        self.channel_id = channel_id
        self.organizer_id = organizer_id
        self.slack_client = slack_client

        self.is_launched = False
        self.question = None
        self.answer = None
        self.time_to_guess = None
        self.time_to_vote = None
        self.results = None

        self.divider_block = board_blocks[0]
        self.question_block = board_blocks[1]
        self.time_to_guess_block = board_blocks[2]
        self.your_guess_block = board_blocks[3]
        self.players_block = board_blocks[4]
        self.time_to_vote_block = board_blocks[5]
        self.your_vote_block = board_blocks[6]
        self.voters_block = board_blocks[7]
        self.truth_block = board_blocks[8]
        self.results_block = board_blocks[9]
        self.graph_block = board_blocks[10]

    @staticmethod
    def format_block(block, message):
        return block.format(message)

    def launch_setup(self):
        self.slack_client.api_call(
            "views.open",
            trigger_id=self.trigger_id,
            view=game_setup)

    def collect_setup(self, view):
        values = view['state']['values']
        self.question = values['question']['question']['value']
        self.answer = values['answer']['answer']['value']
        self.time_to_guess = (values['time_to_guess']['time_to_guess']
                              ['selected_option']['value'])
        self.time_to_vote = (values['time_to_vote']['time_to_vote']
                             ['selected_option']['value'])

    def format_guess_board(self):
        self.question_block = self.format_block(
            self.question_block, self.question)
        self.time_to_guess_block = self.format_block(
            self.time_to_guess_block, self.time_to_guess_block)
        self.players_block = self.format_block(
            self.players_block, '')

    def show_guess_board(self):
        guess_board_blocks = [
            self.divider_block,
            self.question_block,
            self.time_to_guess_block,
            self.players_block
        ]

        self.slack_client.api_call(
            "chat.postMessage",
            channel=self.channel_id,
            text="",
            blocks=guess_board_blocks)
