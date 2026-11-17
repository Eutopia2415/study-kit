#!/bin/zsh
# Double-click to open Study Hall. Starts the local server if it isn't running.
cd "$(dirname "$0")"
PORT=4417
if ! curl -s -o /dev/null "http://127.0.0.1:$PORT/api/state"; then
  nohup python3 server.py $PORT > /tmp/study-hall.log 2>&1 &
  sleep 0.6
fi
open "http://127.0.0.1:$PORT"
