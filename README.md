EDMS
====
Experimental Device Management System.

The idea of this interface is to centralize some basic reports in order to follow parameters around devices (date of production, first usage, first malfunction, versions of softwares components, battery status, location).

The main goal is to have a zero cost integration. Making a report is a simple as that:

    import json, urllib2, datetime, os, socket
    report = {
        "hostname": socket.gethostname(),
        "type": "hello_from_python",
        "date": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
        "loadavg": os.getloadavg(),
        "device_group": "g1"
    }
    urllib2.urlopen('http://localhost:8888/report', json.dumps(report))

Installation
------------
On debian 7 (wheezy), it will something like that:

    apt-get install python-dateutil python-sqlalchemy python-tornado supervisor -y

    mkdir -p /usr/local/share/edms/ /var/lib/edms/

    git clone https://github.com/fclairamb/edms.git /usr/local/share/edms/

    echo "
    [program:edms-8501]
    command=python /usr/local/share/edms/edms.py --port=8501 --db /var/lib/edms/main.db
    stderr_logfile=/var/log/supervisor/edms-stderr.log
    stdout_logfile=/var/log/supervisor/edms-stdout.log" >/etc/supervisor/conf.d/edms.conf




Screenshots
-----------
To get an idea of how it looks like...

**Devices list**<br />
All the identified devices.
![Devices](https://github.com/fclairamb/edms/blob/master/quick-look/Devices.png?raw=true)

**Device report**<br />
View of a single report.
![Device report](https://github.com/fclairamb/edms/blob/master/quick-look/Report.png?raw=true)

**Device properties**<br />
Device properties are the result of many device reports.
![Device properties](https://github.com/fclairamb/edms/blob/master/quick-look/Device%20hostname%20xps.png?raw=true)

**Users**<br />
Users can have access or admin rights. Access right allow to see everything but don't allow to modify anything.
![Users](https://github.com/fclairamb/edms/blob/master/quick-look/Users.png?raw=true)

**Device groups**<br />
Device groups are not (really) used yet.
![Groups](https://github.com/fclairamb/edms/blob/master/quick-look/Groups.png?raw=true)
