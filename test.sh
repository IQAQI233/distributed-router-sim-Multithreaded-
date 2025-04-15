#!/bin/bash

chmod +x Routing.sh
source "$(dirname "$0")/.venv/bin/activate"
ports=(6000 6001 6002 6003 6004 6005)

for port in "${ports[@]}"; do
  pid=$(lsof -ti :$port)
  if [ -n "$pid" ]; then
    echo "Killing process on port $port (PID: $pid)"
    kill -9 "$pid"
  else
    echo "No process on port $port"
  fi
done
./Routing.sh A 6000 local_test/A.txt 3 0.5 &
./Routing.sh B 6001 local_test/B.txt 3 0.5 &
./Routing.sh C 6002 local_test/C.txt 3 0.5 &
./Routing.sh D 6003 local_test/D.txt 3 0.5 &
./Routing.sh E 6004 local_test/E.txt 3 0.5 &
./Routing.sh F 6005 local_test/F.txt 3 0.5
