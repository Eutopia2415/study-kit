#!/bin/zsh
# Put the redesigned room live: room-next.html becomes room.html (the old page is kept as room-old.html) and the
# 4417 server restarts so the new roomstate.py loads. Holds off while a block is running unless called with --now.
cd "$(dirname "$0")/.." || exit 1
PORT=4417
if [[ "$1" != "--now" ]]; then
  while true; do
    B=$(curl -s -m 3 "http://127.0.0.1:$PORT/api/block")
    echo "$B" | python3 -c 'import json,sys; b=json.load(sys.stdin); sys.exit(0 if not b.get("subject") or b.get("paused") else 1)' && break
    sleep 30
  done
fi
[[ -f room-next.html ]] || { echo "room-next.html is missing"; exit 1; }
cp room.html room-old.html && cp room-next.html room.html || exit 1
PID=$(lsof -tiTCP:$PORT -sTCP:LISTEN)
[[ -n "$PID" ]] && kill $PID && sleep 0.6
nohup python3 server.py $PORT > /tmp/study-hall.log 2>&1 &
sleep 1
curl -s -o /dev/null -w "state %{http_code}\n" "http://127.0.0.1:$PORT/api/room/state"
curl -s "http://127.0.0.1:$PORT/room" | grep -c 'class="leaf"' | sed 's/^/new page served: /'
grep -c "api/room/" server.py | sed 's/^/room routes in server.py: /'
