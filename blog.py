from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
import psycopg2
import psycopg2.extras
from functools import wraps
import os

DB_HOST = os.getenv('PSQL_URL')
DB_NAME = os.getenv('PSQL_DB')
DB_USER = os.getenv('PSQL_USER')
DB_PASS = os.getenv('PSQL_PASS')

connection_string = "host={} dbname={} user={} password={}".format(
    DB_HOST, DB_NAME, DB_USER, DB_PASS)

app = Flask(__name__)
app.secret_key = 'show_message'  # for flash message


# DB_CONNECTION_STRING = "host=%s database=%s user=%s password=%s" % (DB_URL, DB_NAME, DB_USER, DB_PASS)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# register form
class RegisterForm(Form):
    fullname = StringField(
        'isim soyisim', [validators.required(), validators.length(min=4, max=100)])
    username = StringField(
        'Kullanici Adi', [validators.required(), validators.length(min=4, max=50)])
    email = StringField('e-mail', [
        validators.required(),
        # validators.Email(message='Email adresi gecersiz')
    ])
    password = PasswordField(
        'sifre', [validators.DataRequired(message='parola giriniz')])
    confirm = PasswordField('sifre tekrar', [
        validators.DataRequired(message='parola giriniz'),
        validators.EqualTo(fieldname="password",
                           message='sifreninz eslesmiyor')
    ])
    #  first_name = StringField(u'First Name', validators=[validators.input_required()])
    #  last_name  = StringField(u'Last Name', validators=[validators.optional()])


class LoginForm(Form):
    username = StringField(
        'Kullanici adi', [validators.InputRequired(message='kullanici adi giriniz')])
    password = StringField(
        'parola', [validators.InputRequired('sifre giriniz')])


class ArticleForm(Form):
    title = StringField('title', [
        validators.DataRequired(message='required'),
        validators.Length(min=5, max=300)
    ])
    content = TextAreaField('content', [
        validators.InputRequired(message='required'),
        validators.Length(min=10)
    ])


@app.route('/')
# @app.route('/<name>')
def index():
    article = {}
    article['title'] = 'Deneme'
    article['body'] = 'lorem ipsum bla bla'
    article['author'] = 'Mustafa gunes'
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    return render_template('index.html', article=article, numbers=numbers)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/addarticle', methods=['GET', 'POST'])
def addArticles():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        content = form.content.data

        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        query = 'insert into articles(title,content,author,user_id) VALUES(%s,%s,%s,%s)'
        cursor.execute(
            query, (title, content, session['username'], session['user_id']))
        conn.commit()

        cursor.close()
        conn.close()
        flash('Makaleniz basarili bir sekilde eklendi', 'success')
        return redirect(url_for('dashboard'))

    return render_template('addArticles.html', form=form)


@app.route('/articles')
def articles():
    #'host="localhost",database="blog", user="mgunes", password="postgres"'

    # conn_string = "host="+ host +" dbname="+ database +" user=" + user +" password="+ password
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = 'SELECT * FROM articles'
    result = cursor.execute(query)
    articles_list = cursor.fetchall()

    cursor.close()
    conn.close()

    if articles_list:
        return render_template('articles.html', articles=articles_list)

    return render_template('articles.html')


@app.route('/article/<string:id>')
def articleDetail(id):
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = 'SELECT * FROM articles WHERE id = %s'
    cursor.execute(query, (id,))
    article = cursor.fetchone()
    if article:
        return render_template('article_detail.html', article=article)

    return render_template('article_detail.html')


@app.route('/remove/<string:id>')
@login_required
def remove(id):
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()

    # check article and user
    query = 'SELECT * FROM articles WHERE id = %s and user_id = %s'
    cursor.execute(query, (id, session['user_id']))
    is_article = cursor.fetchone()

    if is_article:
        delete_query = 'DELETE FROM articles WHERE id = %s'
        cursor.execute(delete_query, (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('article was successfully deleted', 'success')

        return redirect(url_for('dashboard'))

    cursor.close()
    conn.close()
    flash('article not found or you don"t have permission', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/edit/<string:id>', methods=['GET', 'POST'])
@login_required
def updateArticle(id):
    if request.method == 'GET':
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = 'SELECT * FROM articles WHERE id = %s and user_id = %s'
        cursor.execute(query, (id, session['user_id']))
        article = cursor.fetchone()

        if article:
            form = ArticleForm()
            form.title.data = article['title']
            form.content.data = article['content']
            cursor.close()
            conn.close()
            return render_template('updateArticle.html', form=form)
        else:
            flash("Article not found or you don't have permission", "danger")
            return redirect(url_for('index'))
    else:
        # Post request
        form = ArticleForm(request.form)
        new_title = form.title.data
        new_content = form.content.data

        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        query = 'UPDATE articles SET title = %s, content = %s WHERE id = %s'
        cursor.execute(query, (new_title, new_content, id))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Article is successifully updated', 'success')
        return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = 'SELECT * FROM articles WHERE user_id = %s'
    cursor.execute(query, (session['user_id'],))
    user_articles = cursor.fetchall()
    if user_articles:
        return render_template('dashboard.html', articles=user_articles)

    return render_template('dashboard.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    print('form ___ ', form)
    if request.method == 'POST' and form.validate():
        fullname = form.fullname.data
        email = form.email.data
        username = form.username.data
        # password= form.password.data
        password = sha256_crypt.encrypt(form.password.data)

        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        query = 'insert into users(fullname, email, username, password) VALUES(%s,%s,%s,%s)'
        cursor.execute(query, (fullname, email, username, password))
        conn.commit()  # db de bir duzenleme olacaksa commit()

        cursor.close()
        conn.close()

        flash('Kayit isleminiz basari ile gerceklesti', 'success')

        return redirect(url_for('login'))
    else:
        return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password = form.password.data

        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = 'SELECT * FROM users WHERE username = %s'
        result = cursor.execute(query, (username,))
        record = cursor.fetchone()
        cursor.close()
        conn.close()
        if(record):
            realPassword = record['password']
            if sha256_crypt.verify(password, realPassword):
                session['logged_in'] = True
                session['username'] = record['username']
                session['user_id'] = record['id']
                flash('basari ile giris yaptiniz', 'success')
                return redirect(url_for('index'))
            else:
                flash('sifre yanlis', 'danger')
                return redirect(url_for('login'))
        else:
            flash('kullanici adi yanlis', 'danger')
            return redirect(url_for('login'))

    else:
        return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/search', methods=['GET','POST'])
def searchArticle():
    # without click btn
    if request.method == 'GET':
        return redirect(url_for('index'))
    else:
        keyword = request.form.get('keyword')
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # query = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%'"
        query = "SELECT * FROM articles WHERE title ILIKE '%{}%'".format(keyword)
        cursor.execute(query)
        articles = cursor.fetchall()
        if articles:
            return render_template('articles.html', articles=articles)
        else:
            flash('Not found', 'warning')
            return redirect(url_for('articles'))
            

if __name__ == '__main__':
    app.run(debug=True)  # Production env false
