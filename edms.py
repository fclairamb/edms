from datetime import date
import tornado.escape
import tornado.ioloop
import tornado.web
import os
import gettext
import sqlite3
_ = gettext.gettext

EDMS_VERSION = '0.1'

# The idea of this management interface is simply to follow some devices. It's pretty much empty
# but it can be easily extended.

# DB Preparation
#if not os.path.isdir(os.environ['HOME']+"/.emds"):
#    os.mkdir(os.environ['HOME']+"/.emds")
#db = sqlite3.connect(os.environ['HOME']+"/.emds/main.db")
db = sqlite3.connect("main.db")

# This is obviously NOT 3NF, but who cares ???
stmts = ["""
CREATE TABLE IF NOT EXISTS devices (
  ident VARCHAR UNIQUE,
  type VARCHAR,
  date_created DATETIME,
  date_updated DATETIME
);""",
"""
CREATE TABLE IF NOT EXISTS device_properties (
  device_id INT,
  name VARCHAR,
  value VARCHAR
);
""",
"""
CREATE UNIQUE INDEX IF NOT EXISTS device_properties_id_name ON device_properties (device_id, name);
""",
"""
CREATE INDEX IF NOT EXISTS device_properties_name_value ON device_properties(name, value);
""",
"""
CREATE TABLE IF NOT EXISTS device_logs (
  device_id INT,
  date DATETIME,
  source VARCHAR,
  type VARCHAR,
  content TEXT
);
"""]

for st in stmts:
    db.execute(st)
 
class VersionHandler(tornado.web.RequestHandler):
    def get(self):
        response = { 'version': EDMS_VERSION,
                     'last_build':  date.today().isoformat() }
        self.write(response)


class DeviceById(tornado.web.RequestHandler):
    def get(self, id):
        response = { 'id': int(id),
                     'name': 'My device'}
        self.write(response)


class Index(tornado.web.RequestHandler):
    def get(self):
       self.render("home.html", title=_("Welcome"))


class About(tornado.web.RequestHandler):
    def get(self):
        self.render("about.html", title=_("About"))


class DeviceRegister(tornado.web.RequestHandler):
    def get(self):
        data = tornado.escape.json_decode(self.request.body)
        print "ID: "+str(data)

    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        print "ID: "+str(data)

application = tornado.web.Application(
# Paths
   [   
       (r"/device/([0-9]+)", DeviceById),
       (r"/version", VersionHandler),
       (r"/", Index),
       (r"/device/register", DeviceRegister),
       (r"/about", About)
   ],
# Config
    debug=True,
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    template_path=os.path.join(os.path.dirname(__file__), "templates")
)
 
if __name__ == "__main__":
    application.listen(8888)
    print "Ready !"
    tornado.ioloop.IOLoop.instance().start()

