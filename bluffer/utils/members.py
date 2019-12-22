def get_channel_members(slack_client, channel_id):
    return slack_client.api_call(
        'conversations.members',
        channel=channel_id)['members']


def get_workspace_members(slack_client):
    return slack_client.api_call('users.list')['members']


def get_potential_guessers(slack_client, channel_id, organizer_id):
    res = set()
    channel_members = get_channel_members(slack_client, channel_id)
    workspace_members = get_workspace_members(slack_client)
    for m in workspace_members:
        c1 = m['id'] in channel_members
        c2 = not m['is_bot']
        c3 = not m['deleted']
        c4 = m['id'] != 'Truth'
        c5 = m['id'] != organizer_id
        if c1 and c2 and c3 and c4 and c5:
            res.add(m['id'])
    return res
