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
        # c5 = m['id'] != organizer_id
        c5 = True
        if c1 and c2 and c3 and c4 and c5:
            res[m['id']] = user_info_to_user_name(m)
    return res
