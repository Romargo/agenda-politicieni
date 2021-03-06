# encoding: utf-8
import os.path
from datetime import datetime
from collections import defaultdict
from flask import json
from flask.ext.sqlalchemy import SQLAlchemy
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

prop_defs = {
  'phone': u"Telefon",
  'email': u"Email",
  'website': u"Website",
  'facebook': u"Facebook",
  'twitter': u"Twitter",
  'address': u"Adresa poștală",
}


meta_defs = ['office', 'college', 'hpol_id']


db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    openid_url = db.Column(db.Text())
    name = db.Column(db.Text())
    email = db.Column(db.Text())
    time_create = db.Column(db.DateTime)


class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())

    def get_content(self):
        if self.versions:
            version = sorted(self.versions, key=lambda v: v.time)[-1]
            return version.get_content()
        else:
            return {}

    def save_content_version(self, new_content, user):
        utcnow = datetime.utcnow()
        version = ContentVersion(person=self, user=user, time=utcnow)
        version.content = json.dumps(new_content)
        db.session.add(version)
        log.info("Content update for person id=%r version_id=%r",
                 self.id, version.id)

    def get_meta(self, key):
        for meta in self.meta:
            if meta.key == key:
                return meta.value
        else:
            return None

    @classmethod
    def objects_current(cls):
        return cls.query.filter(
            db.not_(
                cls.meta.any(
                    PersonMeta.key == 'removed' and
                    PersonMeta.value == 'true'
                )
            )
        )


class ContentVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'))
    person = db.relationship('Person', backref=db.backref('versions'))
    content = db.Column(db.LargeBinary)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')
    time = db.Column(db.DateTime)

    def get_content(self):
        return json.loads(self.content)


class PersonMeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'))
    person = db.relationship('Person', backref=db.backref('meta'))
    key = db.Column(db.Text)
    value = db.Column(db.Text)


def get_user(openid_url):
    return User.query.filter_by(openid_url=openid_url).first()


def get_update_user(openid_url, name, email):
    user = get_user(openid_url)
    if user is None:
        utcnow = datetime.utcnow()
        user = User(openid_url=openid_url, time_create=utcnow)
        log.info("New user, openid_url=%r", openid_url)

    if (name, email) != (user.name, user.email):
        user.name = name
        user.email = email
        db.session.add(user)
        db.session.commit()
        log.info("User data modified for openid_url=%r: name=%r, email=%r",
                 openid_url, name, email)

    return user
