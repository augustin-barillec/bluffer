#!/bin/bash

source ports.sh
source project_id.sh
source credentials.sh

export GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS

for port in {5002..5008}
do
function_name=$(port_to_function_name $port)
topic=topic_$function_name
python publisher.py $PROJECT_ID create $topic
done
