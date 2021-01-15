import main
from unittest.mock import Mock


def test():
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    form = {
        'team_id': 'tid',
        'channel_id': 'cid',
        'user_id': 'uid',
        'trigger_id': 'tid'
    }
    req = Mock(headers=headers, form=form)
    main.slash_command(req)
