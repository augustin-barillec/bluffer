#!/bin/bash

source ports.sh

PROJECT_ID=$(head -n 1 ../conf.yaml)
PROJECT_ID=${PROJECT_ID#"project_id: "}

./clean_functions.sh

$(gcloud beta emulators pubsub env-init)

export credentials_basename=default_compute_service_account.json
export GOOGLE_APPLICATION_CREDENTIALS=/etc/$PROJECT_ID/$credentials_basename

SOURCE=../main.py

for port in {5000..5007}
do
n=$(port_to_function_name $port)
s=$(port_to_signature_type $port)
file=function_$port.txt
functions-framework --source $SOURCE --target=$n --port $port --signature-type $s &> $file &
done
