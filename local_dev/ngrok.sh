#!/bin/bash

rm -rf ngrok_logs
mkdir ngrok_logs

echo "Stopping background ngrok process"
kill -9 $(ps -ef | grep 'ngrok' | grep -v 'grep' | awk '{print $2}') &
echo "ngrok stopped"

./ngrok http 5000 --log=stdout > ngrok_logs/5000.log &

./ngrok http 5001 --log=stdout > ngrok_logs/5001.log &