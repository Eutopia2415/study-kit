#!/bin/zsh
# Restart the Study Hall server (to load edited server.py / roomstate.py) at a moment that costs the learner nothing:
# when no card is up, or the card up has just been handed in (the tutor is then writing its reply, and the server is
# back before it posts). Gives up after 3 hours. --now skips the wait.
cd "$(dirname "$0")/.." || exit 1
PORT=4417
python3 -m py_compile server.py roomstate.py room.py || { echo "not restarting: the code does not compile"; exit 1; }
[[ $(grep -c "api/room/" server.py) -ge 3 ]] || { echo "not restarting: the room routes are missing from server.py"; exit 1; }
if [[ "$1" != "--now" ]]; then
  for i in {1..10800}; do
    curl -s -m 2 "http://127.0.0.1:$PORT/api/room/state" | python3 -c 'import json,sys; s=json.load(sys.stdin); sys.exit(0 if (not s.get("card")) or s.get("submitted") else 1)' && break
    sleep 1
  done
fi
PID=$(lsof -tiTCP:$PORT -sTCP:LISTEN)
[[ -n "$PID" ]] && kill $PID && sleep 0.5
nohup python3 server.py $PORT > /tmp/study-hall.log 2>&1 &
sleep 1
echo "restarted at $(date '+%H:%M:%S'): state $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$PORT/api/room/state), page $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$PORT/room)"
