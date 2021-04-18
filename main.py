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
APIKEY = 'AIzaSyDhh89odNoM6HWTlJQzfQ-_tbYHf-jncdQ'


# главная страница
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return redirect(f"/search/{request.form['q']}")
    return render_template('index.html', saying=choice(SAYINGS),
                           title='Книгапоиск')


def get_books_table(response):
    # Собираю данные из запроса и формурую таблицу с 3 столбцами
    # В ячейке - миниатюра, название книги и автор
    books = []
    # Если количество найденных книг будет рано 0,
    # то books будет пустой, и будет выведено соответствующее сообщение пользователю
    if response['totalItems']:
        for row_index in range(len(response['items']) // 3 + 1):
            row = []
            if (row_index + 1) * 3 <= len(response['items']):
                # делаем срез трёх книг
                slice = response['items'][row_index * 3:(row_index + 1) * 3]
            else:
                # делаем срез оставшихся двух книг или одной книги
                slice = response['items'][row_index * 3:]
            for book in slice:
                info = book['volumeInfo']
                # Проверка на существование автора
                if 'authors' in info:
                    # Авторов может быть несколько
                    authors = ', '.join(info['authors'])
                else:
                    authors = 'Автор не известен'
                # Проверка на существование картинки
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
        z = f"{request.form['q']}"
        if request.form['author']:
            z += f"+inauthor:{request.form['author']}"
        if request.form['subject']:
            z += f"+subject:{request.form['subject']}"
        return redirect(f"/search/{z}")
    # q - книга, langRestrict - язык
    params = {
        "q": f'"{q}"',
        "maxResults": 20,
        "langRestrict": 'ru',
        "key": 'AIzaSyDhh89odNoM6HWTlJQzfQ-_tbYHf-jncdQ'
    }
    response = requests.get(API_SERVER, params=params).json()
    books = get_books_table(response)
    return render_template('search.html', books=books, search_flag=True, title='Поиск')

@app.route('/user_recommendations')
@login_required
def user_recommendations():
    # Формируем рекомендации для пользователя
    # пока заглушка
    books = []
    return render_template('search.html', books=books, search_flag=False,
                           title='Рекомендации')


@app.route('/book_information/<google_book_id>')
def book_information(google_book_id):
    # Выводим информацию о книге
    response = get(API_SERVER + '/' + google_book_id,
                   params={"langRestrict": 'ru', "key": APIKEY}).json()

    book = {}
    img = None
    buylink = None
    isreadable = False
    # Проверка на существование книги
    if 'volumeInfo' in response:
        data = response['volumeInfo']
        # обложка
        if 'imageLinks' in data:
            img = data['imageLinks']['thumbnail']
        else:
            img = '/static/img/default_img_book.png'
        # название
        book['Название'] = data['title']
        # авторы
        if 'authors' in data:
            book['Авторы'] = ', '.join(data['authors'])
        else:
            book['Авторы'] = 'Отсутствуют'
        # дата публикации
        if 'publishedDate' in data:
            book['Дата публикации'] = data['publishedDate']
        else:
            book['Дата публикации'] = 'Отсутствует'
        # описание
        if 'description' in data:
            book['Описание'] = data['description'].replace(
                '<br>', '').replace('<p>', '').replace('</br>', '').replace(
                '</p>', '')
        else:
            book['Описание'] = 'Отсутствует'
        # категории
        if 'categories' in data:
            book['Категории'] = ', '.join(data['categories'])
        else:
            book['Категории'] = 'Отсутствуют'
        # ссылка на покупку книги
        if 'buyLink' in response['saleInfo']:
            buylink = response["saleInfo"]["buyLink"]
        # флаг на публикацию ссылки на предварительное ознакомление с книгой
        if data['readingModes']['text'] or data['readingModes']['image']:
            isreadable = True
    return render_template('book.html', book=book, img=img, buylink=buylink,
                           google_book_id=google_book_id, isreadable=isreadable,
                           title='Информация о книге')


@app.route('/view_book/<google_book_id>')
def view_book(google_book_id):
    # Просмотр книги
    return render_template('book_viewer.html', google_book_id=google_book_id,
                           title='Просмотр книги')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # профиль пользователя
    if request.method == 'POST':
        # Загрузка аватара
        request.files['file'].save(
            f'static/img/profile_img/{current_user.id}.png')

    # headers нужен для правильного порядка следования заголовков
    headers = {'surname': 'Фамилия', 'name': 'Имя', 'email': 'Почта',
               'age': 'Возраст', 'about': 'О себе'}
    # получаем двнные о пользователе
    user = get(f'http://localhost:5000/api/users/{current_user.id}').json()[
        'users']
    return render_template('profile.html', user=user, headers=headers,
                           title='Профиль')


def check_email(db_sess, email, user_id=None):
    # Проверка email пользователя
    # В зависимости от операции (регистрация или редактирование профиля ползователя)
    # определяется область проверки корректности email пользователя
    if user_id:
        other = db_sess.query(User).filter(User.id != user_id)
    else:
        other = db_sess.query(User).all()
    # получаем email пользователей
    emails = [i.email for i in other]
    # осуществляем проверку
    if email in emails:
        return True
    return False


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_user():
    # редактирование профиля пользователя
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == current_user.id).first()
    form = EditForm()

    if request.method == "GET":
        # Заполняем поля уже существующими данными
        form.surname.data = user.surname
        form.name.data = user.name
        form.email.data = user.email
        form.age.data = user.age
        form.about.data = user.about
        # меняем надпись кнопки
        form.submit.label.text = 'Редактировать'

    elif request.method == "POST" and form.validate_on_submit():
        if check_email(db_sess, form.email.data, user_id=current_user.id):
            # Если такой email уже есть, то выводим сообщение для пользователя
            form.submit.label.text = 'Редактировать'
            return render_template('register.html',
                                   message="Пользователь с таким почтовым адресом уже зарегистрирован",
                                   registerform=form,
                                   title='Редактирование профиля')

        # иначе записываем новые данные
        user.surname = form.surname.data
        user.name = form.name.data
        user.email = form.email.data
        user.age = form.age.data
        user.about = form.about.data

        db_sess.commit()
        return redirect('/profile')

    return render_template('register.html', title='Редактирование профиля',
                           registerform=form)


@login_manager.user_loader
def load_user(user_id):
    # загрузка пользователя
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    # выход из профиля
    logout_user()
    return redirect("/")


@app.route('/login', methods=['GET', 'POST'])
def login():
    # авторизация
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        # Проверка почты
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        # и пароля
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        # в случае неверности одного из пунктов, уведомляем об этом
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               loginform=form, title='Авторизация')
    return render_template('login.html', loginform=form, title='Авторизация')


@app.route('/register', methods=['GET', 'POST'])
def register():
    # регистрация
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        # проверка почты на уникальность
        if check_email(db_sess, form.email.data):
            return render_template('register.html', registerform=form,
                                   message="Пользователь с таким почтовым адресом уже зарегистрирован",
                                   title='Регистрация')

        # Создание нового пользователя в базе данный
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

        # сохраняем дефолтную картинку как аватар пользователя
        default_path = 'static/img/default_person_img.png'
        copy(default_path, f'static/img/profile_img/{current_user.id}.png')
        return redirect("/")
    return render_template('register.html', registerform=form,
                           title='Регистрация')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404_Not_Found.html'), 404

def main():
    # иницилизация базы данных
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
