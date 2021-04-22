import sqlalchemy
from flask_login import UserMixin
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .db_session import SqlAlchemyBase


class Favorite(SqlAlchemyBase, SerializerMixin):
    # таблица книг
    __tablename__ = 'favorite'

    fav_id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    google_id = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=True)

    user = orm.relation('User')

    def __repr__(self):
        return f'{self.fav_id} {self.user_id} {self.google_id}'

