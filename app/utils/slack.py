from app.utils import views


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
    exception_view = views.build_exception_view(msg)
    open_view(slack_client, trigger_id, exception_view)


def get_app_conversations(slack_client):
    return slack_client.api_call(
        'users.conversations',
        types='public_channel, private_channel, mpim, im')['channels']
