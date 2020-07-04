#!/bin/bash

./clean_ngroks.sh

for port in 5000 5001
do
    ./ngrok http $port --log=stdout > ngrok_$port.out &
done
