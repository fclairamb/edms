#!/bin/sh

# Events have no particular meaning, they are just events
# we need to save for future diagnostics

# The easiest way to handle even is simply to save them as JSON file and to send them with a JSON request

curl http://localhost:8888/device/event -X POST -d '
{
  "ident":"imei:357973040149194",
  "event_type":"battery-low", 
  "date":"2013-11-26 02:38:11",
  "battery-level":"30%"
}'

curl http://localhost:8888/device/event -X POST -d '
{
  "ident":"imei:357973040149194",
  "event_type":"high-speed", 
  "date":"2013-11-26 02:40:22",
  "speed":"400kmh"
}'


