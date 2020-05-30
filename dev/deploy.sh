#!/bin/bash

source ./ports.sh
source clean_utils.sh

clean_functions

$(gcloud beta emulators pubsub env-init)

export GOOGLE_APPLICATION_CREDENTIALS=credentials.json

export s=../main.py

for port in {5000..5006}
do
function_name=$(port_to_function_name $port)
function_log_file=function_$port.log
functions-framework --source $s --target=$function_name --port $port &> $function_log_file &
done
