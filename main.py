from flask import Flask, render_template, redirect, request
from flask_restful import Api
from flask_login import LoginManager, login_user, login_required
from flask_login import logout_user, current_user

import requests
from requests import get

from random import choice
from shutil import copy


# поговорки
from data.sayings import SAYINGS

from data import db_session, users_resource, books_resource
from forms.registerform import RegisterForm
from forms.loginform import LoginForm
from forms.editform import EditForm
from data.users import User

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

api = Api(app)
login_manager = LoginManager()
login_manager.init_app(app)

API_SERVER = "https://www.googleapis.com/books/v1/volumes"


@app.route('/', methods=['GET', 'POST'])
def index():
    # Главная страница
    if request.method == 'POST':
        return redirect(f"/search/{request.form['q']}")
    return render_template('index.html', saying=choice(SAYINGS), title='Книгапоиск')


def get_books_table(response):
    # Собираю данные из запроса и формурую таблицу с 3 столбцами
    # В ячейке - миниатюра, название книги и автор
    books = []
    # Если количество найденных книг будет рано 0,
    # то books будет пустой, в шаблоне на основе этого делается анализ
    if response['totalItems']:
        for row_index in range(len(response['items']) // 3 + 1):
            row = []
            if (row_index + 1) * 3 <= len(response['items']):
                slice = response['items'][row_index * 3:(row_index + 1) * 3]
            else:
                # делаем срез оставшиеся 2 книгу или 1 книгу
                slice = response['items'][row_index * 3:]
            for book in slice:
                info = book['volumeInfo']
                # Проверка на существование автора
                if 'authors' in info:
                    # Авторов может быть несколько
                    authors = ', '.join(info['authors'])
                else:
                    authors = 'Автор не известен'
                if 'imageLinks' in info:
                    img = info['imageLinks']['thumbnail']
                else:
                    img = '/static/img/default_img_book.png'
                row.append([info['title'], authors, img, book['id']])
            books.append(row)
    return books


@app.route('/search/<q>', methods=['GET', 'POST'])
def search(q):
    if request.method == 'POST' and request.form['q']:
         return redirect(f"/search/{request.form['q']}")
    # q - книга, langRestrict - язык
    params = {
        "q": f'"{q}"',
        "langRestrict": 'ru',
        "maxResults": 40,
        "key": 'AIzaSyDhh89odNoM6HWTlJQzfQ-_tbYHf-jncdQ'
    }
    response = requests.get(API_SERVER, params=params).json()
    books = get_books_table(response)
    return render_template('search.html', saying=choice(SAYINGS),
                           books=books, search_flag=True, title='Поиск')


@app.route('/user_recommendations', methods=['GET', 'POST'])
@login_required
def user_recommendations():
    # пока заглушка
    books = []
    return render_template('search.html', saying=choice(SAYINGS),
                           books=books, search_flag=False, title='Рекомендации')


@app.route('/book_information/<google_book_id>', methods=['GET', 'POST'])
def book_information(google_book_id):
    if request.method == 'POST' and request.form['q']:
         return redirect(f"/search/{request.form['q']}")
    response = requests.get(API_SERVER + '/' + google_book_id,
                            params={"langRestrict": 'ru'}).json()
    book = {}
    img = None
    link = None
    search_history = []
    if 'volumeInfo' in response:
        data = response['volumeInfo']
        if 'imageLinks' in data:
            img = data['imageLinks']['thumbnail']
        else:
            img = '/static/img/default_img_book.png'
        book['Название'] = data['title']
        search_history.extend(data['title'])
        if 'authors' in data:
            book['Авторы'] = ', '.join(data['authors'])
            search_history.extend(data['authors'])
        else:
            book['Авторы'] = 'Отсутствуют'
        if 'publishedDate' in data:
            book['Дата публикации'] = data['publishedDate']
        else:
            book['Дата публикации'] = 'Отсутствует'
        if 'description' in data:
            book['Описание'] = data['description']
        else:
            book['Описание'] = 'Отсутствует'
        if 'categories' in data:
            book['Категории'] = ', '.join(data['categories'])
            search_history.extend(data['categories'])
        else:
            book['Категории'] = 'Отсутствуют'
        link = data['previewLink']
    return render_template('book.html', saying=choice(SAYINGS),
                           book=book, img=img, link=link,
                           title='Информация о книге')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        request.files['file'].save(f'static/img/profile_img/{current_user.id}.png')

    headers = {'surname': 'Фамилия', 'name': 'Имя', 'email': 'Почта',
               'age': 'Возраст', 'about': 'О себе'}
    user = get(f'http://localhost:5000/api/users/{current_user.id}').json()['users']
    return render_template('profile.html', user=user, headers=headers,
                           title='Профиль', saying=choice(SAYINGS))


def check_email(db_sess, email, user_id=None):
    if user_id:
        other = db_sess.query(User).filter(User.id != user_id)
    else:
        other = db_sess.query(User).all()
    emails = [i.email for i in other]
    if email in emails:
        return True
    return False


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_user():
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == current_user.id).first()
    form = EditForm()

    if request.method == "GET":
        form.surname.data = user.surname
        form.name.data = user.name
        form.email.data = user.email
        form.age.data = user.age
        form.about.data = user.about
        form.submit.label.text = 'Редактировать'

    elif request.method == "POST" and form.validate_on_submit():
        if check_email(db_sess, form.email.data, user_id=current_user.id):
            form.submit.label.text = 'Редактировать'
            return render_template('register.html',
                                   message="Пользователь с таким почтовым адресом уже зарегистрирован",
                                   registerform=form, title='Редактирование профиля',
                                   saying=choice(SAYINGS))

        user.surname = form.surname.data
        user.name = form.name.data
        user.email = form.email.data
        user.age = form.age.data
        user.about = form.about.data

        db_sess.commit()
        return redirect('/profile')

    return render_template('register.html', title='Редактирование профиля',
                           registerform=form, saying=choice(SAYINGS))


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               loginform=form, title='Авторизация',
                               saying=choice(SAYINGS))
    return render_template('login.html', loginform=form,
                           title='Авторизация', saying=choice(SAYINGS))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        if check_email(db_sess, form.email.data):
            return render_template('register.html', registerform=form,
                                   message="Пользователь с таким почтовым адресом уже зарегистрирован",
                                   title='Регистрация', saying=choice(SAYINGS))
        user = User()
        user.surname = form.surname.data
        user.name = form.name.data
        user.email = form.email.data
        user.set_password(form.password.data)
        user.age = form.age.data
        user.about = form.about.data
        db_sess.add(user)
        db_sess.commit()
        login_user(user, remember=form.remember_me.data)

        default_path = 'static/img/default_person_img.png'
        copy(default_path, f'static/img/profile_img/{current_user.id}.png')
        return redirect("/")
    return render_template('register.html', registerform=form,
                           title='Регистрация', saying=choice(SAYINGS))


def main():
    db_session.global_init("db/knigapoisk_db.db")

    # для списка объектов
    api.add_resource(users_resource.UsersListResource, '/api/users')
    api.add_resource(books_resource.BooksListResource, '/api/books')

    # для одного объекта
    api.add_resource(users_resource.UsersResource, '/api/users/<int:users_id>')
    api.add_resource(books_resource.BooksResource, '/api/books/<int:books_id>')

    app.run()


if __name__ == '__main__':
    main()
