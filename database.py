import os.path
from datetime import datetime
from flask import json
from flaskext.sqlalchemy import SQLAlchemy
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    openid_url = db.Column(db.Text())
    name = db.Column(db.Text())
    email = db.Column(db.Text())


class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())

    def get_content(self):
        version = self.versions.order_by(ContentVersion.time.desc()).first()
        return {} if version is None else json.loads(version.content)

    def save_content_version(self, new_content, user):
        now = datetime.now()
        version = ContentVersion(person=self, user=user, time=now)
        version.content = json.dumps(new_content)
        db.session.add(version)
        db.session.commit()


class ContentVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'))
    person = db.relationship('Person',
        backref=db.backref('versions', lazy='dynamic'))
    content = db.Column(db.LargeBinary)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')
    time = db.Column(db.DateTime)


def get_persons():
    results = {}

    for person in Person.query.all():
        results[person.id] = dict(person.get_content(), name=person.name)

    return results


def migrate_properties_to_content():
    now = datetime.now()

    for person in Person.query.all():
        content = {}

        for prop in person.properties.all():
            content.setdefault(prop.name, []).append(prop.value)
            db.session.delete(prop)

        version = ContentVersion(person=person, time=now)
        version.content = json.dumps(content)
        db.session.add(version)

    db.session.commit()


def import_fixture(flush=True):
    data_path = os.path.join(os.path.dirname(__file__), 'data')
    fixture_path = os.path.join(data_path, 'fixture.json')
    now = datetime.now()

    if flush:
        db.drop_all()
        db.create_all()

    with open(fixture_path, 'rb') as f:
        fixture = json.load(f)

    for person_data in fixture:

        person = Person(id=person_data.pop('id'), name=person_data.pop('name'))
        db.session.add(person)

        content = {}
        for key in person_data:
            content.setdefault(key, []).append(person_data[key])

        version = ContentVersion(person=person, time=now)
        version.content = json.dumps(content)
        db.session.add(version)

    db.session.commit()


def import_senators():
    data_path = os.path.join(os.path.dirname(__file__), 'data')
    senators_path = os.path.join(data_path, 'senatori_email.json')
    now = datetime.now()

    with open(senators_path, 'rb') as f:
        senatori = json.load(f)

    for person_data in senatori:
        found_persons = Person.query.filter_by(name=person_data['name']).all()
        if found_persons:
            assert len(found_persons) == 1
            person = found_persons[0]

        else:
            person = Person(name=person_data['name'])
            db.session.add(person)

        emails = person_data['emails']
        if emails:
            content = {'email': emails}
            version = ContentVersion(person=person, time=now)
            version.content = json.dumps(content)
            db.session.add(version)

    db.session.commit()


def get_user(openid_url):
    return User.query.filter_by(openid_url=openid_url).first()


def get_update_user(openid_url, name, email):
    user = get_user(openid_url)
    if user is None:
        user = User(openid_url=openid_url)

    if (name, email) != (user.name, user.email):
        user.name = name
        user.email = email
        db.session.add(user)
        db.session.commit()

    return user
