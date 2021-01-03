from app import utils


def get_channel_members(slack_client, channel_id):
    return slack_client.api_call(
        'conversations.members',
        channel=channel_id)['members']


def get_workspace_members(slack_client):
    return slack_client.api_call('users.list')['members']


def user_info_to_user_name(user_info):
    dn = user_info['profile'].get('display_name')
    fn = user_info['profile'].get('first_name')
    n = user_info['name']
    if dn:
        return dn
    if fn:
        return fn
    return n


def user_id_to_user_name(slack_client, user_id):
    workspace_members = get_workspace_members(slack_client)
    for m in workspace_members:
        if m['id'] == user_id:
            return user_info_to_user_name(m)
    return 'unknown'


def get_potential_guessers(slack_client, channel_id, organizer_id):
    res = dict()
    channel_members = get_channel_members(slack_client, channel_id)
    workspace_members = get_workspace_members(slack_client)
    for m in workspace_members:
        c1 = m['id'] in channel_members
        c2 = not m['is_bot']
        c3 = not m['deleted']
        c4 = m['id'] != 'Truth'
        c5 = m['id'] != organizer_id
        if c1 and c2 and c3 and c4 and c5:
            res[m['id']] = user_info_to_user_name(m)
    return res


def post_message(slack_client, channel_id, blocks):
    return slack_client.api_call(
        'chat.postMessage',
        channel=channel_id,
        blocks=blocks)['ts']


def post_ephemeral(slack_client, channel_id, user_id, msg):
    slack_client.api_call(
        'chat.postEphemeral',
        channel=channel_id,
        user=user_id,
        text=msg)


def update_message(slack_client, channel_id, blocks, ts):
    slack_client.api_call(
        'chat.update',
        channel=channel_id,
        ts=ts,
        blocks=blocks)


def open_view(slack_client, trigger_id, view):
    slack_client.api_call(
        'views.open',
        trigger_id=trigger_id,
        view=view)


def get_app_conversations(slack_client):
    return slack_client.api_call(
        'users.conversations',
        types='public_channel, private_channel, mpim, im')['channels']


class SlackOperator:
    def __init__(self, game):
        self.game = game
        self.block_builder = utils.blocks.BlockBuilder(game)
        self.view_builder = utils.views.ViewBuilder(game)

    def get_potential_guessers(self):
        return get_potential_guessers(
            self.game.slack_client, self.game.channel_id,
            self.game.organizer_id)

    def get_app_conversations(self):
        return get_app_conversations(self.game.slack_client)

    def post_message(self, blocks):
        return post_message(
            self.game.slack_client, self.game.channel_id, blocks)

    def post_ephemeral(self, user_id, msg):
        post_ephemeral(
            self.game.slack_client, self.game.channel_id, user_id, msg)

    def update_message(self, blocks, ts):
        update_message(self.game.slack_client, self.game.channel_id,
                       blocks, ts)

    def open_view(self, trigger_id, view):
        open_view(self.game.slack_client, trigger_id, view)

    def update_upper(self, blocks_):
        self.update_message(blocks_, self.game.upper_ts)

    def update_lower(self, blocks_):
        self.update_message(blocks_, self.game.lower_ts)

    def open_setup_view(self, trigger_id):
        self.open_view(trigger_id, self.view_builder.build_setup_view())

    def open_guess_view(self, trigger_id):
        self.open_view(trigger_id, self.view_builder.build_guess_view())

    def open_vote_view(self, trigger_id, voter):
        view = self.view_builder.build_vote_view(voter)
        self.open_view(trigger_id, view)

    def send_vote_reminders(self):
        for u in self.game.potential_voters:
            msg_template = (
                'Hey {}, you can now vote in the bluffer game '
                'organized by {}!')
            msg = msg_template.format(
                utils.users.user_display(u),
                utils.users.user_display(self.game.organizer_id),
                self.game.time_left_to_vote)
            self.post_ephemeral(u, msg)

    def send_is_over_notifications(self):
        for u in self.game.frozen_guessers:
            msg = ("The bluffer game organized by {} is over!"
                   .format(utils.users.user_display(self.game.organizer_id)))
            self.post_ephemeral(u, msg)

    def post_pre_guess_stage_upper(self):
        return self.post_message(
            self.block_builder.build_pre_guess_stage_upper_blocks())

    def post_pre_guess_stage_lower(self):
        return self.post_message(
            self.block_builder.build_pre_guess_stage_lower_blocks())

    def update_pre_vote_stage_upper(self):
        self.update_upper(
            self.block_builder.build_pre_vote_stage_upper_blocks())

    def update_pre_vote_stage_lower(self):
        self.update_lower(
            self.block_builder.build_pre_vote_stage_lower_blocks())

    def update_pre_result_stage_upper(self):
        self.update_upper(
            self.block_builder.build_pre_result_stage_upper_blocks())

    def update_pre_result_stage_lower(self):
        self.update_lower(
            self.block_builder.build_pre_result_stage_lower_blocks())

    def update_guess_stage_upper(self):
        self.update_upper(
            self.block_builder.build_guess_stage_upper_blocks())

    def update_guess_stage_lower(self):
        self.update_lower(
            self.block_builder.build_guess_stage_lower_blocks())

    def update_vote_stage_upper(self):
        self.update_upper(
            self.block_builder.build_vote_stage_upper_blocks())

    def update_vote_stage_lower(self):
        self.update_lower(
            self.block_builder.build_vote_stage_lower_blocks())

    def update_result_stage_upper(self):
        self.update_upper(
            self.block_builder.build_result_stage_upper_blocks())

    def update_result_stage_lower(self):
        self.update_lower(
            self.block_builder.build_result_stage_lower_blocks())

    def post_pre_guess_stage(self):
        return self.post_pre_guess_stage_upper(), \
               self.post_pre_guess_stage_lower()

    def update_pre_vote_stage(self):
        self.update_pre_vote_stage_upper()
        self.update_pre_vote_stage_lower()

    def update_pre_result_stage(self):
        self.update_pre_result_stage_upper()
        self.update_pre_result_stage_lower()

    def update_guess_stage(self):
        self.update_guess_stage_upper()
        self.update_guess_stage_lower()

    def update_vote_stage(self):
        self.update_vote_stage_upper()
        self.update_vote_stage_lower()

    def update_result_stage(self):
        self.update_result_stage_upper()
        self.update_result_stage_lower()
