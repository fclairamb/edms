from datetime import datetime
from sqlalchemy.exc import IntegrityError
import tornado.escape
import tornado.ioloop
import tornado.web
import os
import re
import gettext
import sqlalchemy
import hashlib
import base64
import uuid
import argparse
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
_ = gettext.gettext

# Deb packages:
# *
# * python-sqlalchemy
# * python-tornado

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='EDMS')
    parser.add_argument('--port', metavar='PORT', type=int, help='Server port', default=8888)
    parser.add_argument('--sql', action='store_true', help='Show SQL requests')
    parser.add_argument('--db', metavar="DB_FILE", help='Database file to use', default='main.db')
    args = parser.parse_args()

engine = sqlalchemy.create_engine('sqlite:///'+args.db, echo=args.sql)

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


class Config(Base):
    """General configuration"""
    __tablename__ = "config"
    name = Column(String, primary_key=True)
    value = Column(String)

    def __repr__(self):
        return "Config<name={name},value={value}>".format(id=self.id, name=self.name)


class DeviceGroup(Base):
    """Device group"""
    __tablename__ = "device_group"
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("device_group.id"))
    name = Column(String)
    ident = Column(String, unique=True)
    depth = Column(Integer)

    parent = relationship("DeviceGroup", remote_side=[id])
    children = relationship("DeviceGroup", remote_side=parent_id)


class Device(Base):
    """Device table"""
    __tablename__ = "device"
    id = Column(Integer, primary_key=True)
    ident = Column(String)
    type = Column(String)
    date_created = Column(DateTime)
    date_updated = Column(DateTime)
    date_seen = Column(DateTime)
    group_id = Column(Integer, ForeignKey('device_group.id'))

    group = relationship("DeviceGroup", order_by=DeviceGroup.id)

    def __repr__(self):
        return "Device<ident={ident},type={type}>".format(id=self.id, name=self.name)


class DeviceLog(Base):
    """Device log"""
    __tablename__ = "device_log"
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('device.id'))
    date = Column(DateTime)
    type = Column(String)
    # We dont need to save the raw content of the report
    # content = Column(String)

    device = relationship("Device", order_by=Device.id)

    def __repr__(self):
        return "DeviceLog<id={id},device_id={device_id},date={date},type={type},content={content}>".format(
            id=self.id,
            device_id=self.device_id,
            date=self.date,
            type=self.type,
            content=self.content
        )

Index(
    "device_log_device_id_date_type",
    DeviceLog.device_id,
    DeviceLog.date,
    DeviceLog.type,
    unique=True)


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    password = Column(String)
    right = Column(Integer)

    RIGHT_ACCESS = 1
    RIGHT_ADMIN = 10
    RIGHTS = {RIGHT_ACCESS: "Access", RIGHT_ADMIN: "Admin"}


class DeviceConfig(Base):
    __tablename__ = "device_config"
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('device.id'))
    name = Column(String)
    value_set = Column(String)
    date_set = Column(DateTime)
    value_ack = Column(String)
    date_ack = Column(DateTime)

    device = relationship("Device", order_by=Device.id)


class DeviceProperty(Base):
    """Last property for all devices."""
    __tablename__ = "device_property"
    device_id = Column(Integer, primary_key=True)
    name = Column(String, primary_key=True)
    value = Column(String)

# We want to be able to search a device by one of its property
# like "ether_macaddress" = "010203040506"
Index("device_properties_name_value", DeviceProperty.name, DeviceProperty.value)


class DevicePropertyHistory(Base):
    """Properties history for all devices."""
    __tablename__ = "device_property_history"
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer)
    name = Column(String)
    date = Column(DateTime)
    value = Column(String)

Index(
    "device_property_history_id_name_date",
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


class SecureHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        userId = self.get_secure_cookie("user_id")
        return session.query(User).filter(User.id == userId).first()

    def has_right(self, right):
        user = self.get_current_user()
        if not user or user.right < right:
            self.redirect('/login')
            self.finish()  # We don't want anyone to continue writing the response
            return False
        else:
            return True

    def check_access_right(self):
        return self.has_right(User.RIGHT_ACCESS)

    def check_admin_right(self):
        return self.has_right(User.RIGHT_ADMIN)


class DeviceById(SecureHandler):
    def get(self, id):
        self.check_access_right()
        device = session.query(Device).filter(Device.ident == id).first()
        if not device:
            device = session.query(Device).filter(Device.id == int(id)).first()
        if device:
            properties = session.query(DeviceProperty)\
                .filter(DeviceProperty.device_id == device.id)\
                .order_by(DeviceProperty.name)\
                .all()
            logs = session.query(DeviceLog).filter(DeviceLog.device_id == device.id)\
                .order_by(DeviceLog.date.desc())\
                .all()
            self.render("device.html", title=_("Device ")+device.ident, device=device, properties=properties, logs=logs)
        else:
            self.render("error.html", title=_("Device not found"), error=_("Device was not found"))


class Devices(SecureHandler):
    def get(self):
        self.check_access_right()
        devices = session.query(Device).all()
        self.render("devices.html", title=_("Devices"), devices=devices)


class Index(tornado.web.RequestHandler):
    def get(self):
        self.render("home.html", title=_(""))


class About(tornado.web.RequestHandler):
    def get(self):
        self.render("about.html", title=_("About"))


def json_flatten(data):
    if not isinstance(data, dict):
        return data
    sub = {}
    for name, value in data.iteritems():
        if isinstance(value, dict):
            for vn, vv in value.iteritems():
                sub[name+"."+vn] = json_flatten(vv)
        else:
            sub[name] = value
    return sub


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
        type = data.get('type')
        if not date:
            self.set_status(400)
            self.write(
                {
                    "status": "error",
                    "message": "No date specified"
                }
            )
            return

        del data['date']

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

        if type:
            del data['type']

        device = get_or_create_device(ident)
        if not device.date_seen or date > device.date_seen:
            device.date_seen = date

        # We will try to attach this device to a group of devices
        conf_possible_group = conf_get("report_possible_device_group_field", "device_group")
        group_ident = data.get(conf_possible_group)
        if group_ident:
            group = session.query(DeviceGroup).filter(DeviceGroup.ident == group_ident).first()

            if not group and bool(conf_get("device_group_auto_create", "false")):
                group = DeviceGroup(name=group_ident, ident=group_ident)
                session.add(group)

            if group:
                device.group_id = group.id

        session.commit()

        changes = False

        if bool(conf_get("report_json_flatten", "true")):
            data = json_flatten(data)

        # We update these report properties in the device properties
        try:
            for name, value in data.iteritems():
                value = tornado.escape.json_encode(value)
                # We check if the value isn't already stored (not doing so
                previous = session.query(DevicePropertyHistory).filter(
                    DevicePropertyHistory.device_id == device.id,
                    DevicePropertyHistory.name == name,
                    DevicePropertyHistory.date == date).first()
                if not previous:  # If not, we store it
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
                log.content = tornado.escape.json_encode(data)
                session.add(log)
                session.commit()

        if changes:
            self.write({"status": "ok"})
        else:
            self.write({"status": "ok", "already_sent": True})

    def get(self):
        self.render("error.html", title=_("Error"), error=_("This page can only be used in POST mode"))


class ConfigPage(SecureHandler):
    def get(self, name=None):
        self.check_access_right()
        if name == u"new":
            conf = Config()
            conf.name = ""
            conf.value = ""
        elif name:
            conf = session.query(Config).filter(Config.name == name, ~Config.name.startswith('.')).first()
        else:
            conf = None
        parameters = session.query(Config).filter(~Config.name.startswith('.')).all()
        self.render("config.html", title=_("Config"), parameters=parameters, param=conf)

    def post(self, name=None):
        if not self.check_admin_right():
            return
        name = self.get_argument("name", name)
        value = self.get_argument("value")
        conf_set(name, value)
        parameters = session.query(Config).filter(~Config.name.startswith('.')).all()
        self.render("config.html", title=_("Config"), parameters=parameters, param=None)


class LastReports(SecureHandler):

    def pagination(self, query, nb=40):
        """Basic pagination"""
        paging_from = self.get_argument("paging_to", None)
        if paging_from:
            query = query.filter(DeviceLog.id <= int(paging_from))

        query = query.limit(nb+1).all()

        link_previous = None
        link_next = None
        if len(query) > 1:
            first = query[0]
            last = query[len(query)-1]

            link_previous = "?paging_to={id}".format(id=first.id+20)

            if len(query) > nb:
                query.pop()
                link_next = "?paging_to={id}".format(id=last.id)
            else:
                link_next = None

        return query, link_previous, link_next

    def get(self, type=None):
        self.check_access_right()
        reports = session.query(DeviceLog).order_by(DeviceLog.date.desc())
        if type:
            reports = reports.filter(DeviceLog.type == type)

        reports, link_previous, link_next = self.pagination(reports)

        self.render(
            "last_reports.html",
            title=_("Last reports"),
            reports=reports,
            paging_previous=link_previous, paging_next=link_next
        )


class ShowReport(SecureHandler):
    def get(self, reportId):
        self.check_access_right()
        report = session.query(DeviceLog).filter(DeviceLog.id == reportId).first()
        if report:
            properties = session.query(DevicePropertyHistory).filter(
                DevicePropertyHistory.device_id == report.device_id,
                DevicePropertyHistory.date == report.date
            ).all()
            self.render("report.html", title=_("Report"), report=report, properties=properties)
        else:
            self.render("error.html", title=_("Error"), error=_("Report could not be found"))


class GroupsPage(SecureHandler):
    def get(self):
        self.check_access_right()
        action = self.get_argument("action", None)

        group = None
        error = None

        if action == "add" or action == 'mod':
            if not self.check_admin_right():
                return
            name = self.get_argument("name", "")
            if action == 'add':
                group = DeviceGroup()
                group.name = ""
                group.ident = ""
            else:
                group = session.query(DeviceGroup).filter(DeviceGroup.id==int(self.get_argument("group_id"))).first()
            if name:
                group.name = name
                group.parent_id = self.get_argument("parent_id", "")
                group.ident = re.sub(r'\W+', '', self.get_argument("ident", ""))
                if group.parent:
                    group.depth = group.parent.depth + 1
                else:
                    group.depth = 0

                try:
                    session.merge(group)
                    session.commit()
                except IntegrityError as e:
                    error = str(e)
                    session.rollback()
                group = None

        groups = session.query(DeviceGroup).order_by(DeviceGroup.depth.desc(), DeviceGroup.name).all()

        self.render("groups.html", title=_("Groups"), groups=groups, current_group=group, error=error)

    def post(self):
        self.get()


class UsersPage(SecureHandler):
    def get(self):
        self.check_access_right()
        action = self.get_argument("action", None)

        user = None
        error = None

        if action == "add" or action == 'mod':
            if not self.check_admin_right():
                return
            id = self.get_argument("id", "")
            username = self.get_argument("username", "")
            password = self.get_argument("password", "")
            right = int(self.get_argument("right", str(User.RIGHT_ACCESS)))
            if action == 'add':
                user = User()
            else:
                user = session.query(User).filter(User.id == int(id)).first()
            if username:
                user.name = username
                user.right = right
                if password or user.password:
                    if password:
                        user.password = hashlib.sha1(password).hexdigest()
                    try:
                        session.merge(user)
                        session.commit()
                        user = None
                    except IntegrityError as e:
                        error = str(e)
                        session.rollback()
                else:
                    error = "You have to specify a password."

        users = session.query(User).order_by(User.name).all()

        self.render("users.html", title=_("Users"), current_user=user, users=users, error=error)

    def post(self):
        self.get()


class Login(tornado.web.RequestHandler):
    def get(self):
        error = None
        if bool(self.get_argument("logout", "false")):
            self.set_secure_cookie("user_id", str(0))
            user = None
        else:
            user = session.query(User).filter(
                User.id == self.get_secure_cookie("user_id")
            ).first()
        self.render('auth.html', title=_("Authentication"), user=user, error=None)

    def post(self):
        error = None
        user = session.query(User).filter(
            User.name == self.get_argument("username", ""),
            User.password == hashlib.sha1(self.get_argument("password", "")).hexdigest()
        ).first()
        if user:
            self.set_secure_cookie("user_id", str(user.id))
        else:
            error = "Could not authenticate you"
        self.render('auth.html', title=_("Authentication"), user=user, error=error)


application = tornado.web.Application(
    # Paths
    [
        (r"/device/(.+)", DeviceById),
        (r"/devices", Devices),
        (r"/", Index),
        (r"/about", About),
        (r"/report", DeviceReport),
        (r"/report/([0-9]+)", ShowReport),
        (r"/last-reports", LastReports),
        (r"/last-reports/(.+)", LastReports),
        (r"/config", ConfigPage),
        (r"/config/(.+)", ConfigPage),
        (r"/groups", GroupsPage),
        (r"/users", UsersPage),
        (r"/login", Login)
    ],
    # Config
    debug=True,
    cookie_secret=conf_get('.cookie_secret', base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)),
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    template_path=os.path.join(os.path.dirname(__file__), "templates")
)


def launch_setup():
    # We define the default options
    conf_get("report_possible_ident_fields", "ident,hostname")
    conf_get("report_possible_device_group_field", "device_group")
    conf_get("report_json_flatten", "true")
    conf_get("device_group_auto_create", "false")

    # We update the number of launches
    nbLaunches = conf_get("nb_launches")
    if not nbLaunches:
        nbLaunches = 1
    else:
        nbLaunches = str(int(nbLaunches) + 1)
    conf_set("nb_launches", nbLaunches)

    # We check if we have a user "admin" and if not we create it:
    user = session.query(User).filter(User.name == "admin").first()
    if not user:
        user = User(name="admin", password=hashlib.sha1("admin").hexdigest(), right=User.RIGHT_ADMIN)
        session.add(user)
        session.commit()
        print("Created user \"admin\" with pass \"admin\".")

if __name__ == "__main__":
    application.listen(args.port)
    launch_setup()
    print("Listening on {port}".format(port=args.port))
    tornado.ioloop.IOLoop.instance().start()

