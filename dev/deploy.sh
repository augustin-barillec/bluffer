#!/bin/bash

source ports.sh
source credentials.sh

./clean_functions.sh

$(gcloud beta emulators pubsub env-init)

export GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS

SOURCE=../main.py

for port in {5000..5008}
do
n=$(port_to_function_name $port)
s=$(port_to_signature_type $port)
file=function_$port.txt
functions-framework --source $SOURCE --target=$n --port $port --signature-type $s &> $file &
done
