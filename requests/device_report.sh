#!/bin/sh
curl http://localhost:8888/report -d "{
  \"hostname\":\"`hostname`\",
  \"date\":\"`date +%Y-%m-%d\ %H:%M:%S.%6N`\",
  \"type\":\"hello_from_shell\",
  \"loadavg\":\"`cat /proc/loadavg`\",
  \"uname\":\"`uname -omr`\"
}"
