functions-framework --target=slack_command --port 5000

functions-framework --target=message_actions --port 5001

functions-framework --target=pre_guess_stage --port 5002 --signature-type event

functions-framework --target=guess_stage --port 5003 --signature-type event
