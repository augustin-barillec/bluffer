rm -rf stdouts
mkdir stdouts

for port in 5000 5001 5002 5003 5004 5005
do
    kill -9 $(lsof -t -i tcp:$port)
done

$(gcloud beta emulators pubsub env-init)

export s=../main.py

nohup functions-framework --source $s --target=slack_command --port 5000 > stdouts/5000.out &

nohup functions-framework --source $s --target=message_actions --port 5001 > stdouts/5001.out &

nohup functions-framework --source $s --target=pre_guess_stage --port 5002 --signature-type event > stdouts/5002.out &

nohup functions-framework --source $s --target=guess_stage --port 5003 --signature-type event > stdouts/5003.out &

nohup functions-framework --source $s --target=pre_vote_stage --port 5004 --signature-type event > stdouts/5004.out &

nohup functions-framework --source $s --target=vote_stage --port 5005 --signature-type event > stdouts/5005.out &
