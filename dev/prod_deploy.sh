#!/bin/bash

rm -f prod_deploy_*.txt

source ports.sh
source project_id.sh
source credentials.sh

gcloud auth activate-service-account \
--project=$PROJECT_ID \
--key-file=$GOOGLE_APPLICATION_CREDENTIALS

for port in {5000..5001}
do
function_name=$(port_to_function_name $port)
file=prod_deploy_$port.txt
gcloud functions deploy $function_name \
--source .. \
--runtime python38 \
--trigger-http &> $file &
done

for port in {5002..5008}
do
function_name=$(port_to_function_name $port)
topic=topic_$function_name
file=prod_deploy_$port.txt
gcloud functions deploy $function_name \
--source .. \
--runtime python38 \
--trigger-topic $topic &> $file &
done
