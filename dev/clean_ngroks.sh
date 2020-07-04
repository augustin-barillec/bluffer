#!/bin/bash

rm -f ngrok_*.out
kill -9 $(ps -ef | grep 'ngrok http' | grep -v 'grep' | awk '{print $2}')