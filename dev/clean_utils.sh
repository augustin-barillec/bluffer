function clean_ngroks(){
    rm -rf ngrok_*.out
    kill -9 $(ps -ef | grep 'ngrok http' | grep -v 'grep' | awk '{print $2}')
}

function clean_functions(){
    rm -rf function_*.log
    for port in 5000 5001 5002 5003 5004 5005
    do
        kill -9 $(lsof -t -i tcp:$port)
    done
}
