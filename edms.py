from datetime import date, datetime
import dateutil.parser
from sqlalchemy.exc import IntegrityError
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

Index(
    "device_logs_device_id_date_type",
    DeviceLog.device_id,
    DeviceLog.date,
    DeviceLog.type,
    unique=True)


class DeviceProperty(Base):
    __tablename__ = "device_properties"
    device_id = Column(Integer, primary_key=True)
    name = Column(String, primary_key=True)
    value = Column(String)

# We want to be able to search a device by one of its property
# like "ether_macaddress" = "010203040506"
Index("device_properties_name_value", DeviceProperty.name, DeviceProperty.value)


class DevicePropertyHistory(Base):
    __tablename__ = "device_properties_history"
#    __table_args__ = ( # This is ugly
#            UniqueConstraint(
#                "device_id",
#                "name",
#                "date"
#            ),
#        )
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer)
    name = Column(String)
    date = Column(DateTime)
    value = Column(String)

Index(
    "device_properties_history_id_name_date",
    DevicePropertyHistory.device_id,
    DevicePropertyHistory.name,
    DevicePropertyHistory.date,
    unique=True)


Base.metadata.create_all(engine)


def conf_get(name, default=None):
        conf = session.query(Config).filter(Config.name == name).first()
        if conf:
            return conf.value
        else:
            if default:  # We can easily see the default values in the GUI this way
                conf_set(name, default)
            return default


def conf_set(name, value):
        conf = session.query(Config).filter(Config.name == name).first()
        if not conf:
            conf = Config(name=name)
            session.add(conf)
        conf.value = value
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
    return device


class DeviceById(tornado.web.RequestHandler):
    def get(self, id):
        device = session.query(Device).filter(Device.ident == id).first()
        if not device:
            device = session.query(Device).filter(Device.id == int(id)).first()
        if device:
            properties = session.query(DeviceProperty).filter(DeviceProperty.device_id == device.id).order_by(DeviceProperty.name).all()
            logs = session.query(DeviceLog).filter(DeviceLog.device_id==device.id).order_by(DeviceLog.date.desc()).all()
            self.render("device.html", title=_("Device"), device=device, properties=properties, logs=logs)
        else:
            self.render("error.html", title=_("Device not found"), error=_("Device was not found"))


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
            for name, value in data.iteritems():
                session.merge(DeviceProperty(device_id=device.id, name=name, value=value))

        session.commit()
        self.write({"status": "ok"})


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


class DeviceReport(tornado.web.RequestHandler):
    def post(self):
        conf_possible_ident = conf_get("report_possible_ident_fields", "ident,hostname").split(',')
        data = tornado.escape.json_decode(self.request.body)

        ident = None

        for name in conf_possible_ident:
            value = data.get(name)
            if value:
                ident = name+":"+value
                break

        date = data.get('date')
        if not date:
            self.set_status(400)
            self.write(
                {
                    "status": "error",
                    "message": "No date specified"
                }
            )
            return

        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
        if not date:
            self.set_status(400)
            self.write(
                {
                    "status": "error",
                    "message": "Incorrect date format"
                }
            )
            return

        if not ident:
            self.set_status(400)
            self.write(
                {
                    "status": "error",
                    "message": "No identifier could be found",
                    "possible identifiers": conf_possible_ident
                }
            )
            return

        device = get_or_create_device(ident)
        if not device.date_seen or date > device.date_seen:
            device.date_seen = date

        session.commit()

        changes = False

        try:
            for name, value in data.iteritems():
                value = tornado.escape.json_encode(value)
                # We check if the value isn't already stored (not doing so
                previous = session.query(DevicePropertyHistory).filter(
                    DevicePropertyHistory.device_id == device.id,
                    DevicePropertyHistory.name == name,
                    DevicePropertyHistory.date == date).first()
                if not previous: # If not, we store it
                    changes = True
                    session.merge(DevicePropertyHistory(device_id=device.id, name=name, date=date, value=value))

                # We only take the last value as the current one
                last = session.query(DevicePropertyHistory).filter(
                    DevicePropertyHistory.device_id == device.id,
                    DevicePropertyHistory.name == name,
                    DevicePropertyHistory.date == date).order_by(DevicePropertyHistory.date.desc()).first()
                session.merge(DeviceProperty(device_id=last.device_id, name=last.name, value=last.value))
        except IntegrityError:
            session.rollback()

        if changes and date > device.date_updated:
            device.date_updated = date

        session.commit()

        type = data['type']

        if type:
            log = DeviceLog()
            log.device_id = device.id
            log.date = date
            log.type = type

            previous = session.query(DeviceLog).filter(
                DeviceLog.device_id == log.device_id,
                DeviceLog.type == log.type,
                DeviceLog.date == log.date
            ).first()

            if not previous:
                changes = True
                del data['date']
                del data['type']
                log.content = tornado.escape.json_encode(data)
                session.add(log)
                session.commit()

        if changes:
            self.write({"status": "ok"})
        else:
            self.write({"status": "ok", "already_sent": True})

    def get(self):
        self.render("error.html", title=_("Error"), error=_("This page can only be used in POST mode"))


class ConfigPage(tornado.web.RequestHandler):
    def get(self, name=None):
        if name == u"new":
            conf = Config()
            conf.name = ""
            conf.value = ""
        elif name:
            conf = session.query(Config).filter(Config.name == name).first()
        else:
            conf = None
        parameters = session.query(Config).all()
        self.render("config.html", title=_("Config"), parameters=parameters, param=conf)

    def post(self, name=None):
        name = self.get_argument("name", name)
        value = self.get_argument("value")
        conf_set(name, value)
        parameters = session.query(Config).all()
        self.render("config.html", title=_("Config"), parameters=parameters, param=None)

application = tornado.web.Application(
# Paths
    [
       (r"/device/(.+)", DeviceById),
       (r"/device/event", DeviceEvent),
       (r"/devices", Devices),
       (r"/device/properties", DeviceProperties),
       (r"/", Index),
       (r"/device/register", DeviceRegister),
       (r"/about", About),
       (r"/report", DeviceReport),
       (r"/config", ConfigPage),
       (r"/config/(.+)", ConfigPage)
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

