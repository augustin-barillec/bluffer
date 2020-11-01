#!/bin/bash

source ./ports.sh

PROJECT_ID=$(head -n 1 ../conf.yaml)
PROJECT_ID=${PROJECT_ID#"project_id: "}

PORT=8085
kill -9 $(lsof -t -i tcp:$PORT)
gcloud beta emulators pubsub start --project=$PROJECT_ID --host-port=0.0.0.0:$PORT &

$(gcloud beta emulators pubsub env-init)

for port in {5002..5007}
do
function_name=$(port_to_function_name $port)
topic=topic_$function_name
sub=sub_$function_name
endpoint=http://0.0.0.0:$port/
python publisher.py $PROJECT_ID create $topic
python subscriber.py $PROJECT_ID create-push $topic $sub $endpoint
done
