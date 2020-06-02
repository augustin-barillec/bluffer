#!/bin/bash

source ports.sh
source clean_utils.sh

clean_functions

$(gcloud beta emulators pubsub env-init)

export GOOGLE_APPLICATION_CREDENTIALS=credentials.json

SOURCE=../main.py

for port in {5000..5006}
do
n=$(port_to_function_name $port)
s=$(port_to_signature_type $port)
file=function_$port.log
functions-framework --source $SOURCE --target=$n --port $port --signature-type $s &> $file &
done