import main
from unittest.mock import Mock, patch


@patch('main.db')
@patch('app.game.SlackClient')
@patch('app.utils.exceptions.ExceptionsHandler')
def test(db, slack_client, exceptions_handler):
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    form = {
        'team_id': 'tid',
        'channel_id': 'cid',
        'user_id': 'uid',
        'trigger_id': 'tid'
    }
    req = Mock(headers=headers, form=form)
    main.slash_command(req)
    assert db.is_called
    assert slack_client.is_called
    assert exceptions_handler.is_called
