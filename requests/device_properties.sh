#!/bin/sh

curl http://localhost:8888/device/properties -X POST -d '
{
  "ident":"imei:357973040149194",
  "battery_size":"2500mAh",
  "screen_size":"640x480",
  "gps_included":"1"
}'