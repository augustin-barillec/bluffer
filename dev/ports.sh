#!/bin/bash

function port_to_function_name(){
case $1
in
    5000) echo slack_command ;;
    5001) echo message_actions ;;
    5002) echo pre_guess_stage ;;
    5003) echo guess_stage ;;
    5004) echo pre_vote_stage ;;
    5005) echo vote_stage ;;
    5006) echo result_stage ;;
esac
}
