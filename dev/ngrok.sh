#!/bin/bash

source clean_utils.sh

clean_ngroks

for port in 5000 5001
do
    ./ngrok http $port --log=stdout > ngrok_$port.out &
done
