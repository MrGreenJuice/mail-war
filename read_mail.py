import json
import sys
from email.parser import Parser

from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

email_input = sys.stdin.readlines()

engine = create_engine(
    'mysql+pymysql://user:password@host:3306/custom_email')
DBSession = sessionmaker(bind=engine)
Base = declarative_base()


class MailList(Base):
    __tablename__ = 'mail_list'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String)


class MailListParse(Base):
    __tablename__ = 'mail_list_parse'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String)
    sender = Column(String)
    to = Column(String)
    subject = Column(String)


def record_original(data):
    session = DBSession()
    session.add(MailList(content=data))
    session.commit()

    session.close()


def record_parse(sender, to, subject, content):
    session = DBSession()
    session.add(MailListParse(content=content, sender=sender, to=to, subject=subject))
    session.commit()
    session.close()


data = ""
for line in email_input:
    data = data + line
record_original(data)

email = Parser().parsestr(data)
body = []
for payload in email.get_payload():
    body.append(str(payload))
to = str(email['to'])
if to.index("<") > 0:
    to = to[to.index("<") + 1: to.index(">")]
sender = email['from']
if sender.index("<") > 0:
    sender = sender[sender.index("<") + 1: sender.index(">")]
record_parse(sender, to, email['subject'], json.dumps(body))
