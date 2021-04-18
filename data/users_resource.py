from flask_restful import abort, Resource
from flask import jsonify

from data import db_session
from data.users import User
from data.reqparse_users import parser


def abort_if_news_not_found(users_id):
    # обработка ошибки
    session = db_session.create_session()
    users = session.query(User).get(users_id)
    if not users:
        abort(404, message=f"User {users_id} not found")


class UsersResource(Resource):
    # ресурс для одного пользователя
    def get(self, users_id):
        # получение данных о пользователе
        abort_if_news_not_found(users_id)
        session = db_session.create_session()
        users = session.query(User).get(users_id)
        return jsonify({'users': users.to_dict(
            only=('id', 'surname', 'name', 'email', 'hashed_password', 'age', 'about'))})

    def delete(self, users_id):
        # удаления данных о пользователе
        abort_if_news_not_found(users_id)
        session = db_session.create_session()
        users = session.query(User).get(users_id)
        session.delete(users)
        session.commit()
        return jsonify({'success': 'OK'})


class UsersListResource(Resource):
    # ресурс для списка пользователей
    def get(self):
        # получение данных о пользователях
        session = db_session.create_session()
        users = session.query(User).all()
        return jsonify({'users': [item.to_dict(
            only=('id', 'surname', 'name', 'email', 'hashed_password', 'age', 'about'))
            for item in users]})

    def post(self):
        # Добавление данных о новом пользователе
        args = parser.parse_args()
        session = db_session.create_session()
        users = User(
            surname=args['surname'],
            name=args['name'],
            email=args['email'],
            hashed_password=args['hashed_password'],
            age=args['age'],
            about=args['about']
        )
        session.add(users)
        session.commit()
        return jsonify({'success': 'OK'})

