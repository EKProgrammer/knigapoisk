import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class Favorite(SqlAlchemyBase, SerializerMixin):
    # таблица книг
    __tablename__ = 'favorite'

    fav_id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    google_id = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=True)

    def __repr__(self):
        return f'{self.fav_id} {self.user_id} {self.google_id}'

