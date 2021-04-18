from flask_restful import abort, Resource
from flask import jsonify

from data import db_session
from data.books import Books
from data.reqparse_books import parser


def abort_if_news_not_found(books_id):
    # обработка ошибки
    session = db_session.create_session()
    books = session.query(Books).get(books_id)
    if not books:
        abort(404, message=f"Book {books_id} not found")


class BooksResource(Resource):
    # ресурс для одной книги
    def get(self, books_id):
        # получение данных о книге
        abort_if_news_not_found(books_id)
        session = db_session.create_session()
        books = session.query(Books).get(books_id)
        return jsonify({'books': books.to_dict(
            only=('id', 'title', 'author', 'genre', 'img_url',
                  'year_of_publishing', 'description', 'preview_url'))})

    def delete(self, books_id):
        # удаление данных о книге
        abort_if_news_not_found(books_id)
        session = db_session.create_session()
        books = session.query(Books).get(books_id)
        session.delete(books)
        session.commit()
        return jsonify({'success': 'OK'})


class BooksListResource(Resource):
    # ресурс для списка книг
    def get(self):
        # получение данных о книгах
        session = db_session.create_session()
        books = session.query(Books).all()
        return jsonify({'books': [item.to_dict(
            only=('id', 'title', 'author', 'genre', 'img_url',
                  'year_of_publishing', 'description', 'preview_url'))
            for item in books]})

    def post(self):
        # Добавление данных о новой книге
        args = parser.parse_args()
        session = db_session.create_session()
        books = Books(
            title=args['title'],
            author=args['author'],
            genre=args['genre'],
            img_url=args['img_url'],
            year_of_publishing=args['year_of_publishing'],
            description=args['description'],
            preview_url=args['preview_url']
        )
        session.add(books)
        session.commit()
        return jsonify({'success': 'OK'})

