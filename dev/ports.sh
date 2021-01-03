#!/bin/bash

function port_to_function_name(){
case $1
in
    5000) echo slash_command ;;
    5001) echo message_actions ;;
    5002) echo handle_slash_command ;;
    5003) echo handle_message_actions ;;
    5004) echo pre_guess_stage ;;
    5005) echo guess_stage ;;
    5006) echo pre_vote_stage ;;
    5007) echo vote_stage ;;
    5008) echo pre_result_stage ;;
    5009) echo result_stage ;;
    5010) echo erase
esac
}

function port_to_signature_type(){
case $1
in
    5000) echo http ;;
    5001) echo http ;;
    5002) echo event ;;
    5003) echo event ;;
    5004) echo event ;;
    5005) echo event ;;
    5006) echo event ;;
    5007) echo event ;;
    5008) echo event ;;
    5009) echo event ;;
    5010) echo event ;;
esac
}