#!/usr/bin/python
import json, urllib2, datetime, os, socket

report = {
    "hostname": socket.gethostname(),
    "type": "hello_from_python",
    "date": datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
    "loadavg": os.getloadavg(),
    "device_group": "g1",
    "hierarchy": {
        "sub1": "val1",
        "sub2": "val2"
    }
}

urllib2.urlopen('http://localhost:8888/report', json.dumps(report))
