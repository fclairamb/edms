from datetime import date, datetime
import tornado.escape
import tornado.ioloop
import tornado.web
import os
import gettext
import sqlalchemy
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
_ = gettext.gettext

EDMS_VERSION = '0.1'

# The idea of this management interface is simply to follow some devices. It's pretty much empty
# but it can be easily extended.

engine = sqlalchemy.create_engine('sqlite:///main.db', echo=True)

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

class Config(Base):
    __tablename__ = "config"
    name = Column(String, primary_key=True)
    value = Column(String)

    def __repr__(self):
        return "Config<name={name},value={value}>".format(id=self.id, name=self.name)

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True)
    ident = Column(String)
    type = Column(String)
    date_created = Column(DateTime)
    date_updated = Column(DateTime)
    date_seen = Column(DateTime)

    def __repr__(self):
        return "User<id={id},name={name}>".format(id=self.id, name=self.name)

Base.metadata.create_all(engine)

#conf = session.query(Config).filter(Config.name == "nb_launches").first()
#if not conf:
#    conf = Config(name="nb_launches", value="1")
#    session.add( conf )
#conf.value = str(int(conf.value) + 1)
#session.commit()

def conf_get(name):
        conf = session.query(Config).filter(Config.name == name).first()
        if conf:
            return conf.value
        else:
            return None

def conf_set(name, value):
        conf = session.query(Config).filter(Config.name == name).first()
        if not conf:
            conf = Config(name=name)
            session.add(conf)
        conf.value=value
        session.commit()

nbLaunches = conf_get("nb_launches")
if not nbLaunches:
    nbLaunches = 1
else:
    nbLaunches = str( int(nbLaunches) + 1 )
conf_set("nb_launches", nbLaunches)

class VersionHandler(tornado.web.RequestHandler):
    def get(self):
        response = { 'version': EDMS_VERSION,
                     'last_build':  date.today().isoformat() }
        self.write(response)


class DeviceById(tornado.web.RequestHandler):
    def get(self, id):
        device = session.query(Device).filter(Device.id == int(id)).first()
        if device:
            self.render("device.html", title=_("Device"), device=device)
        else:
            self.render("404.html", title=_("Device not found"))

class Devices(tornado.web.RequestHandler):
    def get(self):
        devices = session.query(Device).all()
        self.render("devices.html", title=_("Devices"), devices=devices)

class Index(tornado.web.RequestHandler):
    def get(self):
        self.render("home.html", title=_("Welcome"))


class About(tornado.web.RequestHandler):
    def get(self):
        self.render("about.html", title=_("About"))


class DeviceRegister(tornado.web.RequestHandler):
    def post(self):
        # It must be something like that:
        # {"ident":"imei:2492492", "type":"TC65i"
        data = tornado.escape.json_decode(self.request.body)
        device = session.query(Device).filter(Device.ident == data['ident']).first()
        if not device:
            device = Device(ident=data['ident'], type=data.get('type'), date_created=datetime.utcnow())
            session.add(device)
        device.date_seen = datetime.utcnow()
        session.commit()

application = tornado.web.Application(
# Paths
   [   
       (r"/device/([0-9]+)", DeviceById),
       (r"/devices", Devices),
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

