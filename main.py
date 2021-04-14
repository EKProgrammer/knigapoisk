from flask import Flask, render_template, redirect, request
from flask_restful import Api
from flask_login import LoginManager, login_user, login_required
from flask_login import logout_user, current_user

import requests
from requests import get, post

from random import choice
from PIL import Image
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
api = Api(app)
login_manager = LoginManager()
login_manager.init_app(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    # Главная страница
    if request.method == 'POST':
        return redirect(f"/search/{request.form['q']}")
    return render_template('index.html', saying=choice(SAYINGS), title='Книгапоиск')


@app.route('/search/<q>', methods=['GET', 'POST'])
def search(q):
    api_server = "https://www.googleapis.com/books/v1/volumes"
    # q - книга, langRestrict - язык
    params = {
        "q": f'"{q}"',
        "langRestrict": 'ru',
        "maxResults": 40,
        "key": 'AIzaSyDhh89odNoM6HWTlJQzfQ-_tbYHf-jncdQ'
    }
    response = requests.get(api_server, params=params).json()
    print(response)
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
                row.append([info['title'], authors, img])
            books.append(row)

    if request.method == 'POST' and request.form['q']:
        return redirect(f"/search/{request.form['q']}")
    return render_template('search.html', saying=choice(SAYINGS),
                           books=books, title='Поиск')


@app.route('/book_information/<google_book_id>')
def book_information(google_book_id):
    return '123456789'


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        paths = [[f'static/img/profile_img/{current_user.id}.png', (500, 500)],
                 [f'static/img/profile_img/{current_user.id}_mini.png', (100, 100)]]
        file = request.files['file'].read()
        for path, sizes in paths:
            with open(path, 'wb') as f:
                f.write(file)
            img = Image.open(path)
            resize_img = img.resize(sizes)
            resize_img.save(path)

    headers = {'surname': 'Фамилия', 'name': 'Имя', 'email': 'Почта',
               'age': 'Возраст', 'about': 'О себе'}
    user = get(f'http://localhost:5000/api/users/{current_user.id}').json()['users']
    return render_template('profile.html', user=user, headers=headers,
                           title='Профиль', saying=choice(SAYINGS))


# не работает
@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_user():
    user = get(f'http://localhost:5000/api/users/{current_user.id}').json()['users']
    form = EditForm()

    if request.method == "GET":
        form.surname.data = user['surname']
        form.name.data = user['name']
        form.email.data = user['email']
        form.age.data = user['age']
        form.about.data = user['about']
        form.submit.label.text = 'Редактировать'

    elif request.method == "POST":

        if form.validate_on_submit():
            post(f'http://localhost:5000/api/users/{current_user.id}', json={
                    'surname': form.surname.data,
                    'name': form.name.data,
                    'email': form.email.data,
                    'age': form.age.data,
                    'about': form.about.data})
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
        mini_path = f'static/img/profile_img/{current_user.id}_mini.png'
        copy(default_path, mini_path)
        img = Image.open(mini_path)
        resize_img = img.resize((100, 100))
        resize_img.save(mini_path)
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
