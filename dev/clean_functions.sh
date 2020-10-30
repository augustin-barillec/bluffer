#!/bin/bash

rm -f function_*.txt
for port in {5000..5006}
do
    kill -9 $(lsof -t -i tcp:$port)
done
