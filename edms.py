from datetime import date, datetime
import dateutil.parser
import tornado.escape
import tornado.ioloop
import tornado.web
import os
import gettext
import sqlalchemy
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
_ = gettext.gettext

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
        return "Device<ident={ident},type={type}>".format(id=self.id, name=self.name)


class DeviceLog(Base):
    __tablename__ = "device_logs"
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    date = Column(DateTime)
    type = Column(String)
    content = Column(String)

    def __repr__(self):
        return "DeviceLog<id={id},device_id={device_id},date={date},type={type},content={content}>".format(
            id=self.id,
            device_id=self.device_id,
            date=self.date,
            type=self.type,
            content=self.content
        )


class DeviceProperty(Base):
    __tablename__ = "device_properties"
    device_id = Column(Integer, primary_key=True)
    name = Column(String, primary_key=True)
    value = Column(String)

# We want to be able to search a device by one of its property
# like "ether_macaddress" = "010203040506"
Index("device_properties_name_value", DeviceProperty.name, DeviceProperty.value)


Base.metadata.create_all(engine)


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


def get_or_create_device(ident):
    device = session.query(Device).filter(Device.ident == ident).first()
    if not device:
        device = Device(
            ident=ident,
            date_updated=datetime.utcnow(),
            date_created=datetime.utcnow()
        )
    session.add(device)

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
        data = tornado.escape.json_decode(self.request.body)
        device = get_or_create_device(data['ident'])
        if not device.type and data.get('ident'):
            device.type = data['ident']
            device.date_updated = datetime.utcnow()
        device.date_seen = datetime.utcnow()
        session.commit()
        self.write({"status": "ok", "device_id": device.id})


class DeviceProperties(tornado.web.RequestHandler):
    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        device = get_or_create_device(data['ident'])
        del data['ident']
        if device:
            for name, value in data:
                session.add(DeviceProperty(name, value))

        session.commit()


class DeviceEvent(tornado.web.RequestHandler):
    def post(self):
        data = tornado.escape.json_decode(self.request.body)
        device = session.query(Device).filter(Device.ident == data['ident']).first()
        if not device:
            device = Device(
                ident=data['ident'],
                date_updated=datetime.utcnow(),
                date_created=datetime.utcnow()
            )
            session.add(device)
        date = data.get('date')
        if date:
            date = dateutil.parser.parse(date)
        if not date:
            date = datetime.now()
        device.date_seen = datetime.utcnow()

        if not data.get('event_type'):
            self.write({"status":"error","message":"you need to have an event type"})
            return

        log = DeviceLog(
            device_id=device.id,
            date=date,
            type=data['event_type'])
        del data['ident']
        del data['date']
        del data['event_type']
        log.content=tornado.escape.json_encode(data)
        session.add(log)
        session.commit()
        self.write({"status": "ok"})


application = tornado.web.Application(
# Paths
    [
       (r"/device/([0-9]+)", DeviceById),
       (r"/device/event", DeviceEvent),
       (r"/devices", Devices),
       (r"/device/properties", DeviceProperties),
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
    print ("Ready !")
    tornado.ioloop.IOLoop.instance().start()

