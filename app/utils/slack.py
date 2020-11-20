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
    if dn is not None and dn != '':
        return dn
    if fn is not None and fn != '':
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


def open_exception_view(slack_client, trigger_id, msg):
    exception_view = utils.views.build_exception_view(msg)
    open_view(slack_client, trigger_id, exception_view)


def get_app_conversations(slack_client):
    return slack_client.api_call(
        'users.conversations',
        types='public_channel, private_channel, mpim, im')['channels']


class SlackOperator:
    def __init__(
            self,
            slack_client,
            channel_id,
            organizer_id,
            upper_ts,
            lower_ts,
            view_builder):
        self.slack_client = slack_client
        self.channel_id = channel_id
        self.organizer_id = organizer_id
        self.upper_ts = upper_ts
        self.lower_ts = lower_ts
        self.view_builder = view_builder

    def get_potential_guessers(self):
        return get_potential_guessers(
            self.slack_client, self.channel_id, self.organizer_id)

    def get_app_conversations(self):
        return get_app_conversations(self.slack_client)

    def post_message(self, blocks_):
        return post_message(self.slack_client, self.channel_id, blocks_)

    def post_ephemeral(self, user_id, msg):
        post_ephemeral(self.slack_client, self.channel_id, user_id, msg)

    def update_message(self, blocks_, ts):
        update_message(self.slack_client, self.channel_id, blocks_, ts)

    def open_view(self, trigger_id, view):
        open_view(self.slack_client, trigger_id, view)

    def open_exception_view(self, trigger_id, msg):
        open_exception_view(self.slack_client, trigger_id, msg)

    def update_upper(self, blocks_):
        self.update_message(blocks_, self.upper_ts)

    def update_lower(self, blocks_):
        self.update_message(blocks_, self.lower_ts)

    def open_setup_view(self, trigger_id):
        self.open_view(trigger_id, self.view_builder.build_setup_view())

    def open_guess_view(self, trigger_id):
        self.open_view(trigger_id, self.view_builder.build_guess_view())

    def open_vote_view(self, trigger_id, voter):
        view = self.view_builder.build_vote_view(voter)
        self.open_view(trigger_id, view)


def send_vote_reminders(game):
    for u in game.potential_voters:
        msg_template = (
            'Hey {}, you can now vote in the bluffer game '
            'organized by {}!')
        msg = msg_template.format(
            utils.users.user_display(u),
            utils.users.user_display(game.organizer_id),
            game.time_left_to_vote)
        game.slack_operator.post_ephemeral(u, msg)


def send_is_over_notifications(game):
    for u in game.frozen_guessers:
        msg = ("The bluffer game organized by {} is over!"
               .format(utils.users.user_display(game.organizer_id)))
        game.slack_operator.post_ephemeral(u, msg)


def post_pre_guess_stage_upper(organizer_id, slack_operator):
    return slack_operator.post_message(
        utils.blocks.build_pre_guess_stage_upper_blocks(organizer_id))


def post_pre_guess_stage_lower(slack_operator):
    return slack_operator.post_message(
        utils.blocks.build_pre_guess_stage_lower_blocks())


def update_pre_vote_stage_upper(organizer_id, question, slack_operator):
    slack_operator.update_upper(
        utils.blocks.build_pre_vote_stage_upper_blocks(
            organizer_id, question))


def update_pre_vote_stage_lower(slack_operator):
    slack_operator.update_lower(
        utils.blocks.build_pre_vote_stage_lower_blocks())


def update_pre_result_stage_upper(organizer_id, question, slack_operator):
    slack_operator.update_upper(
        utils.blocks.build_pre_result_stage_upper_blocks(
            organizer_id, question))


def update_pre_result_stage_lower(slack_operator):
    slack_operator.update_lower(
        utils.blocks.build_pre_result_stage_lower_blocks())


def update_guess_stage_upper(
        organizer_id, question, id_builder, slack_operator):
    slack_operator.update_upper(
        utils.blocks.build_guess_stage_upper_blocks(
            organizer_id, question, id_builder))


def update_guess_stage_lower(game):
    game.slack_operator.update_lower(
        utils.blocks.build_guess_stage_lower_blocks(
            game.time_left_to_guess, game.guessers))


def update_vote_stage_upper(
        organizer_id, question, id_builder, proposals_browser, slack_operator):
    slack_operator.update_upper(
        utils.blocks.build_vote_stage_upper_blocks(
            organizer_id, question, id_builder, proposals_browser))


def update_vote_stage_lower(game):
    game.slack_operator.update_lower(
        utils.blocks.build_vote_stage_lower_blocks(
            game.potential_voters, game.voters, game.time_left_to_vote))


def update_result_stage_upper(
        organizer_id, question, truth, truth_index, results, frozen_guessers,
        frozen_voters, max_score, winners, graph_url, slack_operator):
    slack_operator.update_upper(
        utils.blocks.build_result_stage_upper_blocks(
            organizer_id, question, truth, truth_index, results,
            frozen_guessers, frozen_voters, max_score, winners, graph_url))


def update_result_stage_lower(slack_operator):
    slack_operator.update_lower(utils.blocks.build_result_stage_lower_blocks())


def post_pre_guess_stage(game):
    return post_pre_guess_stage_upper(
        game.organizer_id, game.slack_operator), \
           post_pre_guess_stage_lower(game.slack_operator)


def update_pre_vote_stage(game):
    update_pre_vote_stage_upper(
        game.organizer_id, game.question, game.slack_operator)
    update_pre_vote_stage_lower(game.slack_operator)


def update_pre_result_stage(game):
    update_pre_result_stage_upper(
        game.organizer_id, game.question, game.slack_operator)
    update_pre_result_stage_lower(game.slack_operator)


def update_guess_stage(game):
    update_guess_stage_upper(
        game.organizer_id, game.question, game.id_builder, game.slack_operator)
    update_guess_stage_lower(game)


def update_vote_stage(game):
    update_vote_stage_upper(
        game.organizer_id, game.question, game.id_builder,
        game.proposals_browser, game.slack_operator)
    update_vote_stage_lower(game)


def update_result_stage(game):
    update_result_stage_upper(
        game.organizer_id, game.question, game.truth, game.truth_index,
        game.results, game.frozen_guessers, game.frozen_voters, game.max_score,
        game.winners, game.graph_url, game.slack_operator)
    update_result_stage_lower(game.slack_operator)
