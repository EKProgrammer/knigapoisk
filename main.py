from flask import Flask, render_template, redirect, request
from flask_restful import Api
from flask_login import LoginManager, login_user, login_required
from flask_login import logout_user, current_user

import requests

from random import choice, sample
from shutil import copy
import os

# поговорки
from data.sayings import SAYINGS
# ресурс
from data import db_session, users_resource
# формы
from forms.registerform import RegisterForm
from forms.loginform import LoginForm
from forms.editform import EditForm
# таблицы
from data.users import User
from data.favorite import Favorite

# настройка приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

api = Api(app)
login_manager = LoginManager()
login_manager.init_app(app)

# константы
API_SERVER = "https://www.googleapis.com/books/v1/volumes"
APIKEY = 'AIzaSyDhh89odNoM6HWTlJQzfQ-_tbYHf-jncdQ'


# главная страница
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # обработка ошибки
        if '/' in request.form['q']:
            return render_template('index.html', saying=choice(SAYINGS), title='Книгапоиск',
                                   message='Символ "/" нельзя использовать в поисковом запросе.')
        return redirect(f"/search/{request.form['q'].replace(' ', '+')}")
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
                row.append(book_parse(book))
            books.append(row)
    return books


def book_parse(book):
    # получаем информацию о книге в нужном для нас формате
    info = book['volumeInfo']
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
    return [info['title'], authors, img, book['id']]


@app.route('/search/<q>', methods=['GET', 'POST'])
def search(q):
    # поиск книг

    if request.method == 'POST' and request.form['q']:
        z = f"{request.form['q'].strip()}"
        if request.form['author']:
            z += f'+inauthor:"{request.form["author"].replace(" ", "+")}"'
        if request.form['subject']:
            z += f'+subject:"{request.form["subject"].replace(" ", "+")}"'
        return redirect(f"/search/{z.replace(' ', '+')}")

    # q - запрос, maxResults - максимальное кол-во результатов,
    # langRestrict - язык, key - API ключ
    params = {
        "q": f'"{q}"',
        "maxResults": 20,
        "langRestrict": 'ru',
        "key": APIKEY
    }
    # Получаем ответ API
    response = requests.get(API_SERVER, params=params).json()
    # Формируем таблицу книг
    books = get_books_table(response)
    return render_template('search.html', books=books,
                           search_flag=True, title='Поиск')


@app.route('/user_recommendations')
@login_required
def user_recommendations():
    # Формируем рекомендации для пользователя
    tags = get_tags()
    # Если избранных книг нет значит и рекомендаций нет
    if tags:
        # ключи для того, чтобы не получить ошибку в get_books_table()
        books = {'totalItems': 1,
                 'items': []}
        for param in tags.keys():
            for tag in tags[param]:
                # Формируем запрос по соответствующему параметру
                params = {
                    "q": f'""+{param}:"{tag.replace(" ", "+")}"',
                    "maxResults": 10,
                    "langRestrict": 'ru',
                    "key": APIKEY
                }
                # Получаем ответ API
                response = requests.get(API_SERVER, params=params).json()
                # Добавляем новые книги
                books['items'].extend(response['items'])
        # Формируем таблицу из 3-х столбцов
        table = get_books_table(books)
    else:
        table = []
    return render_template('search.html', books=table,
                           search_flag=False, title='Рекомендации')


def get_tags():
    # Получаем теги для формирования рекомендаций
    db_sess = db_session.create_session()
    # Все избранные ползователем книги
    favorites = db_sess.query(User).filter(
        User.id == current_user.id).first().books
    # Если избранных книг нет значит и рекомендаций нет
    if not favorites:
        return {}

    tags = {'subject': [],
            'inauthor': [],
            'intitle': []}
    # Используем две любые книги
    if len(favorites) == 1:
        random_choice = favorites
    else:
        random_choice = sample(favorites, 2)

    for favorite in random_choice:
        response = requests.get(
            API_SERVER + '/' + favorite.google_id,
            params={"langRestrict": 'ru', "key": APIKEY}).json()
        # Полчаем тег книги либо из категорий (в первую очередь),
        # либо из авторов, либо, крайнем случае, из названия.
        if 'categories' in response['volumeInfo']:
            tags['subject'].append(response['volumeInfo']['categories'][0])
        elif 'authors' in response['volumeInfo']:
            tags['inauthor'].append(response['volumeInfo']['authors'][0])
        else:
            tags['intitle'].append(response['volumeInfo']['title'])

    return tags


@app.route('/book_information/<google_book_id>')
def book_information(google_book_id):
    # Выводим информацию о книге
    response = requests.get(API_SERVER + '/' + google_book_id,
                            params={"langRestrict": 'ru', "key": APIKEY}).json()

    if current_user.is_authenticated:
        db_sess = db_session.create_session()
        check = []
        for favorite_ in db_sess.query(Favorite).all():
            f = str(favorite_)
            f = f.split()
            if int(f[1]) == int(current_user.id):
                check.append(f[2])

        if google_book_id in check:
            fav = True
        else:
            fav = False
    else:
        fav = False

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
                           fav_check=fav, title='Информация о книге')


def book_parse2(book):
    # получаем информацию о книге в нужном для нас формате
    if 'Авторы' in book:
        # Авторов может быть несколько
        authors = ', '.join(book['Авторы'].split())
    else:
        authors = 'Автор не известен'
    # Проверка на существование картинки
    if 'image' in book:
        img = book['image']
    else:
        img = '/static/img/default_img_book.png'

    return [book['Название'], authors, img, book['id']]


def get_books_table2(response):
    # Собираю данные из запроса и формурую таблицу с 3 столбцами
    # В ячейке - миниатюра, название книги и автор
    books = []
    # Если количество найденных книг будет рано 0,
    # то books будет пустой, и будет выведено соответствующее сообщение пользователю
    for row_index in range(len(response) // 3 + 1):
        row = []
        if (row_index + 1) * 3 <= len(response):
            # делаем срез трёх книг
            slice = response[row_index * 3:(row_index + 1) * 3]
        else:
            # делаем срез оставшихся двух книг или одной книги
            slice = response[row_index * 3:]
        for book in slice:
            row.append(book)
        books.append(row)
    return books


@app.route('/favorites/<user_id>')
@login_required
def favorites(user_id):
    if int(current_user.id) == int(user_id):
        # Выводим информацию о книге

        db_sess = db_session.create_session()
        favorite_list = []
        check = []
        for favorite_ in db_sess.query(Favorite).all():
            f = str(favorite_)
            f = f.split()
            if int(f[1]) == int(current_user.id):
                check.append(f[2])

        for favorite in check:
            response = requests.get(API_SERVER + '/' + favorite,
                                    params={"langRestrict": 'ru',
                                            "key": APIKEY}).json()
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
                book['image'] = img
                book['id'] = favorite
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

                pars_book = book_parse2(book)
                favorite_list.append(pars_book)

        table = get_books_table2(favorite_list)

        if table == [[]]:
            there_are_no_favorites_books = True
        else:
            there_are_no_favorites_books = False

        return render_template('search.html', books=table, search_flag=False,
                               there_are_no_favorites_books=there_are_no_favorites_books)

    else:
        return redirect("/error")


@app.route('/view_book/<google_book_id>')
def view_book(google_book_id):
    # Просмотр книги
    return render_template('book_viewer.html', google_book_id=google_book_id,
                           title='Просмотр книги')


# запись в избранное
@app.route('/background_process_test/', methods=['POST'])
def background_process_test():
    db_sess = db_session.create_session()
    check = []
    google_book_id = request.form['google_book_id']
    flag = int(request.form['delete_flag'])

    if flag == 0:
        for favorite_ in db_sess.query(Favorite).all():
            f = str(favorite_)
            f = f.split()
            if int(f[1]) == int(current_user.id):
                check.append(f[2])

        if google_book_id in check:
            return redirect("/error")
        else:
            fav = Favorite()

            fav.user_id = current_user.id
            fav.google_id = google_book_id

            db_sess.add(fav)
            db_sess.commit()

            return redirect(f"/book_information/{google_book_id}")

    else:
        fav = db_sess.query(Favorite).filter(Favorite.user_id == str(current_user.id),
                                             Favorite.google_id == str(google_book_id)
                                             ).first()
        if fav:
            db_sess.delete(fav)
            db_sess.commit()

        return redirect(f"/book_information/{google_book_id}")


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
    # получаем данные о пользователе
    user = requests.get(
        f'https://knigapoisk.herokuapp.com/api/users/{current_user.id}').json()[
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


@app.route('/profile/delete')
@login_required
def delete_user():
    # удаление пользователя
    # удаляем его изображение
    os.remove(f'static/img/profile_img/{current_user.id}.png')
    # удаляем его самого
    requests.delete(f'https://knigapoisk.herokuapp.com/api/users/{current_user.id}')
    return redirect('/')


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


@app.errorhandler(401)
def page_not_found2(e):
    return render_template('401_Unauthorized.html', title='401 Error'), 401


def main():
    # иницилизация базы данных
    db_session.global_init("db/knigapoisk_db.db")

    # для списка объектов
    api.add_resource(users_resource.UsersListResource, '/api/users')
    # для одного объекта
    api.add_resource(users_resource.UsersResource, '/api/users/<int:users_id>')

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()

# db_sess = db_session.create_session() Создаю ссесию
#    check = [] список  подходящими ключами
#
#    for favorite_ in db_sess.query(Favorite).all(): перебираю всю таблицу
#        f = str(favorite_)
#        f = f.split()
#        if int(f[1]) == int(current_user.id): если нахожу совпадение с id пользователя
#            check.append(f[2]) то добавляю в список
#  f[0] - id избранного
#  f[1] - id пользователя
#  f[2] - id google book
