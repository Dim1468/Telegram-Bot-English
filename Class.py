import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

MyBase = declarative_base()

class CustomUser(MyBase):
  __tablename__ = 'custom_user'
  user_id = sq.Column(sq.Integer, primary_key=True)
  custom_cid = sq.Column(sq.BigInteger, unique=True)

class CustomUserWord(MyBase):
  __tablename__ = 'custom_user_word'
  word_id = sq.Column(sq.Integer, primary_key=True)
  custom_word = sq.Column(sq.String(length=40), unique=True)
  custom_translate = sq.Column(sq.String(length=40), unique=True)
  user_id = sq.Column(sq.Integer, sq.ForeignKey('custom_user.user_id'), nullable=False)

  custom_user = relationship(CustomUser, backref='custom_word')

class CustomWord(MyBase):
  __tablename__ = 'custom_word'
  word_id = sq.Column(sq.Integer, primary_key=True)
  custom_word = sq.Column(sq.String(length=40), unique=True)
  custom_translate = sq.Column(sq.String(length=40), unique=True)

def initialize_database(engine):
  MyBase.metadata.drop_all(engine)
  MyBase.metadata.create_all(engine)