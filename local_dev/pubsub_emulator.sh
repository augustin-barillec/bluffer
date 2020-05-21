#!/bin/bash

export PROJECT_ID=project-20190222-269014

export PORT=8085
kill -9 $(lsof -t -i tcp:$PORT)
gcloud beta emulators pubsub start --project=$PROJECT_ID --host-port=0.0.0.0:$PORT &

$(gcloud beta emulators pubsub env-init)

python publisher.py $PROJECT_ID create pre_guess_stage_topic
python publisher.py $PROJECT_ID create guess_stage_topic
python publisher.py $PROJECT_ID create pre_vote_stage_topic
python publisher.py $PROJECT_ID create vote_stage_topic
python publisher.py $PROJECT_ID create result_stage_topic

python subscriber.py $PROJECT_ID create-push pre_guess_stage_topic sub2 http://0.0.0.0:5002/
python subscriber.py $PROJECT_ID create-push guess_stage_topic sub3 http://0.0.0.0:5003/
python subscriber.py $PROJECT_ID create-push pre_vote_stage_topic sub4 http://0.0.0.0:5004/
python subscriber.py $PROJECT_ID create-push vote_stage_topic sub5 http://0.0.0.0:5005/
python subscriber.py $PROJECT_ID create-push result_stage_topic sub6 http://0.0.0.0:5006/