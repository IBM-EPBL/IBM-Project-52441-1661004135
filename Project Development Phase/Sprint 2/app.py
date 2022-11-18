import binascii
import datetime
import math
import random
import secrets
import time
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d

import ibm_db
import sendgrid
from cryptography.fernet import InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from flask import Flask, render_template, request, session, redirect

from markupsafe import escape
from sendgrid.helpers.mail import Mail, Email, To, Content

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif'}


conn = ibm_db.connect(
    "DATABASE=bludb;HOSTNAME=ea286ace-86c7-4d5b-8580-3fbfa46b66.bs2io90l08b1od8lcg.databases.appdomain.cloud;PORT"
    "=31509;SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID=xnc98967;PWD=wQioPYLq4Oanh",
    '', '')

print(conn)

# key for encryption
KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# sendgrid
SENDGRID_API_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

app = Flask(__name__)

app.secret_key = "\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"


backend = default_backend()


def generateOTP():
    digits = "0123456789"
    OTP = ""
    for i in range(6):
        OTP += digits[math.floor(random.random() * 10)]
    return OTP

def get_history():
    history = []
    sql = f"SELECT * FROM PERSON WHERE email = '{session['email']}'"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_both(stmt)
    while dictionary:
        history.append(dictionary)
        dictionary = ibm_db.fetch_both(stmt)
    return history


def get_history_person(email):
    history = []
    sql = f"SELECT * FROM PERSON WHERE email = '{email}'"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_both(stmt)
    while dictionary:
        history.append(dictionary)
        dictionary = ibm_db.fetch_both(stmt)
    return history


def get_history_person_time(time):
    historys = []
    sql = f"SELECT * FROM PERSON WHERE time = '{time}'"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_both(stmt)
    while dictionary:
        historys.append(dictionary)
        dictionary = ibm_db.fetch_both(stmt)
    return historys


def get_user():
    user = []
    sql = f"SELECT * FROM USER"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_both(stmt)
    while dictionary:
        user.append(dictionary)
        dictionary = ibm_db.fetch_both(stmt)
    return user


# sendgrid
def send_mail(email):
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    from_email = Email("xxxxxxxxxxxxxxxx@gmail.com")  # Change to your verified sender
    to_email = To(email)  # Change to your recipient
    subject = "Nutrition is a basic human need and a prerequisite for healthy life"
    content = Content("text/plain",
                      "Thank you for creating an account on our platform. Now you can utilise our platform "
                      "to maintain a healthier life.")
    mail = Mail(from_email, to_email, subject, content)

    # Get a JSON-ready representation of the Mail object
    mail_json = mail.get()

    # Send an HTTP POST request to /mail/send
    response = sg.client.mail.send.post(request_body=mail_json)
    # print(response.status_code)
    # print(response.headers)


def custom_send_mail(email, otp):
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    from_email = Email("nutritioninyourlife.foryoy@gmail.com")  # Change to your verified sender
    to_email = To(email)  # Change to your recipient
    subject = "Nutrition is a basic human need and a prerequisite for healthy life"
    content = Content("text/plain",
                      f"OTP : '{otp}'")
    mail = Mail(from_email, to_email, subject, content)

    # Get a JSON-ready representation of the Mail object
    mail_json = mail.get()

    # Send an HTTP POST request to /mail/send
    response = sg.client.mail.send.post(request_body=mail_json)
    # print(response.status_code)
    # print(response.headers)


def aes_gcm_encrypt(message: bytes, key: bytes) -> bytes:
    current_time = int(time.time()).to_bytes(8, 'big')
    algorithm = algorithms.AES(key)
    iv = secrets.token_bytes(algorithm.block_size // 8)
    cipher = Cipher(algorithm, modes.GCM(iv), backend=backend)
    encryptor = cipher.encryptor()
    encryptor.authenticate_additional_data(current_time)
    ciphertext = encryptor.update(message) + encryptor.finalize()
    return b64e(current_time + iv + ciphertext + encryptor.tag)


def aes_gcm_decrypt(token: bytes, key: bytes, ttl=None) -> bytes:
    algorithm = algorithms.AES(key)
    try:
        data = b64d(token)
    except (TypeError, binascii.Error):
        raise InvalidToken
    timestamp, iv, tag = data[:8], data[8:algorithm.block_size // 8 + 8], data[-16:]
    if ttl is not None:
        current_time = int(time.time())
        time_encrypted, = int.from_bytes(data[:8], 'big')
        if time_encrypted + ttl < current_time or current_time + 60 < time_encrypted:
            # too old or created well before our current time + 1 h to account for clock skew
            raise InvalidToken
    cipher = Cipher(algorithm, modes.GCM(iv, tag), backend=backend)
    decryptor = cipher.decryptor()
    decryptor.authenticate_additional_data(timestamp)
    ciphertext = data[8 + len(iv):-16]
    return decryptor.update(ciphertext) + decryptor.finalize()


@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def homepage():
    if request.method == 'POST' and 'email' in request.form and 'pass' in request.form:
        error = None
        username = request.form['email']
        password = request.form['pass']
        user = None

        if username == "":
            error = 'Incorrect username.'
            return render_template('index.html', error=error)

        if password == "":
            error = 'Incorrect password.'
            return render_template('index.html', error=error)

        sql = "SELECT * FROM ADMIN WHERE email =?"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(stmt, 1, username)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        if account:
            print(aes_gcm_decrypt(account['PASSWORD'], bytes(KEY, 'utf-8')))
            print(bytes(password, 'utf-8'))
            if aes_gcm_decrypt(account['PASSWORD'], bytes(KEY, 'utf-8')) == bytes(password, 'utf-8'):
                user = account['NAME']
                email = account["EMAIL"]
                session["loggedIn"] = None
                session['name'] = user
                session['email'] = email
                msg = None
                history = get_history()  # end of user

                list = get_user()
                return render_template('adminpanal.html', user=user, list=list, email=email, msg=msg)
            return render_template('index.html', error="Wrong Password!")

        sql = "SELECT * FROM USER WHERE email =?"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(stmt, 1, username)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        if not account:
            return render_template('index.html', error="Username not found!")

        print(aes_gcm_decrypt(account['PASSWORD'], bytes(KEY, 'utf-8')))
        print(bytes(password, 'utf-8'))
        if aes_gcm_decrypt(account['PASSWORD'], bytes(KEY, 'utf-8')) == bytes(password, 'utf-8'):
            user = account['NAME']
            email = account["EMAIL"]
            session["loggedIn"] = 'loggedIn'
            session['name'] = user
            session['email'] = email
            msg = None
            history = get_history()  # end of user

            list = get_user()
            return render_template('dashboard.html', user=user, email=email, msg=msg, history=history)
        return render_template('index.html', error="Wrong Password!")

    elif request.method == 'POST' and 'deleteHistory' in request.form:
        sql = f"SELECT * FROM PERSON WHERE email='{session['email']}'"
        print(sql)
        stmt = ibm_db.exec_immediate(conn, sql)
        list_of_history = ibm_db.fetch_row(stmt)
        if list_of_history:
            sql = f"DELETE FROM PERSON WHERE email='{session['email']}'"
            stmt = ibm_db.exec_immediate(conn, sql)
            history = get_history()
            if history:
                return render_template("dashboard.html", msg="Delete successfully", user=session['name'],
                                       email=session['email'])

        return render_template("dashboard.html", msg="Delete successfully", user=session['name'],
                               email=session['email'])

    elif request.method == 'POST' and 'logout' in request.form:
        session["loggedIn"] = None
        session['name'] = None
        session['email'] = None
        return render_template('index.html', error="Successfully Logged Out!")

    elif request.method == 'POST' and 'extra_submit_param_view' in request.form:
        nutrition_list = request.form["extra_submit_param_view"]
        history = get_history()
        splitted_nutrition = nutrition_list.split(",")
        return render_template('dashboard.html', user=session['name'], email=session['email'], data=splitted_nutrition,
                               history=history)

    elif request.method == 'POST' and 'extra_submit_param_delete' in request.form:
        time_identity = request.form["extra_submit_param_delete"]
        history = get_history()
        sql = f"SELECT * FROM PERSON WHERE time='{escape(time_identity)}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_row(stmt)
        if row:
            sql = f"DELETE FROM PERSON WHERE time='{escape(time_identity)}'"
            stmt = ibm_db.exec_immediate(conn, sql)
            history = get_history()
            if history:
                return render_template("dashboard.html", history=history, msg="Delete successfully")
            return render_template("dashboard.html", msg="Delete successfully")
        return render_template("dashboard.html", history=history, msg="Something went wrong, Try again")

    elif request.method == 'POST' and 'extra_submit_param_record' in request.form:
        email_user = request.form["extra_submit_param_record"]
        return render_template('adminpanal.html', user=session['name'], email=session['email'], list=get_user(),
                               history=get_history_person(email_user))

    elif request.method == 'POST' and 'extra_submit_param_delete_user' in request.form:
        email_user = request.form["extra_submit_param_delete_user"]
        sql = f"SELECT * FROM USER WHERE time='{escape(email_user)}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_row(stmt)
        if row:
            sql = f"DELETE FROM USER WHERE time='{escape(email_user)}'"
            stmt = ibm_db.exec_immediate(conn, sql)
        sql = f"SELECT * FROM PERSON WHERE time='{escape(email_user)}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_row(stmt)
        if row:
            sql = f"DELETE FROM PERSON WHERE time='{escape(email_user)}'"
            stmt = ibm_db.exec_immediate(conn, sql)
        return render_template('adminpanal.html', user=session['name'], list=get_user())

    elif request.method == 'POST' and 'extra_submit_param_nutritions' in request.form:
        user_time = request.form["extra_submit_param_nutritions"]
        user_of = get_history_person_time(user_time)
        user_dic = user_of[0]
        splitted_nutrition = user_dic['NUTRITION'].split(",")
        return render_template('adminpanal.html', user=session['name'], list=get_user(),
                               history=get_history_person(user_dic["EMAIL"]), data=splitted_nutrition)

    elif request.method == 'POST' and 'extra_submit_param_delete_record' in request.form:
        email_user = request.form["extra_submit_param_delete_record"]
        user_of = get_history_person_time(email_user)
        user_dic = user_of[0]
        sql = f"SELECT * FROM PERSON WHERE time='{escape(email_user)}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_row(stmt)
        if row:
            sql = f"DELETE FROM PERSON WHERE time='{escape(email_user)}'"
            stmt = ibm_db.exec_immediate(conn, sql)
        return render_template('adminpanal.html', user=session['name'], list=get_user(),
                               history=get_history_person(user_dic["EMAIL"]))

    elif session.get('loggedIn'):
        history = get_history()
        return render_template('dashboard.html', user=session['name'], history=history)
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST' and 'name' in request.form and 'email' in request.form and 'pass' in request.form:
        name = request.form['name']
        email_up = request.form['email']
        pass_up = request.form['pass']
        if name == "":
            error = 'Enter a valid Name.'
            return render_template('index.html', error=error)

        if email_up == "":
            error = 'Enter a valid E-mail.'
            return render_template('index.html', error=error)

        if pass_up == "":
            error = 'Enter a valid Password.'
            return render_template('index.html', error=error)

        sql = "SELECT * FROM USER WHERE email =?"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(stmt, 1, email_up)
        ibm_db.execute(stmt)
        account = ibm_db.fetch_assoc(stmt)
        if account:
            return render_template('index.html', error="You are already a member, please login using your details")
        else:
            try:
                insert_sql = "INSERT INTO USER VALUES (?,?,?)"
                prep_stmt = ibm_db.prepare(conn, insert_sql)
                ibm_db.bind_param(prep_stmt, 1, name)
                ibm_db.bind_param(prep_stmt, 2, email_up)
                ibm_db.bind_param(prep_stmt, 3, aes_gcm_encrypt(bytes(pass_up, 'utf-8'), bytes(KEY, 'utf-8')))
                ibm_db.execute(prep_stmt)
                send_mail(email_up)
                return render_template('index.html', error="Successfully created")
            except ibm_db.stmt_error:
                return render_template('index.html', error="Failed to create Account")
    return render_template('index.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/dashboard', methods=['GET', 'POST'])
def upload_file():
    history = []
    # sql = "SELECT * FROM Students"
    sql = f"SELECT * FROM PERSON WHERE email = '{session['email']}'"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_both(stmt)
    while dictionary:
        history.append(dictionary)
        dictionary = ibm_db.fetch_both(stmt)
    if request.method == 'POST':
        # check if the post request has the file part
        if 'logout' in request.form:
            session["loggedIn"] = None
            session['name'] = None
            session['email'] = None
            return render_template('index.html', error="Successfully created")
        if 'file' not in request.files:
            # flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.

        if file.filename == '':
            return render_template('dashboard.html', msg="File not found", history=history)
        baseimage = file.read()
        if file and allowed_file(file.filename):
            pass
        return render_template('dashboard.html', history=history)
    if session['name'] is None:
        return render_template('index.html')
    return render_template('dashboard.html', user=session['name'], email=session['email'], history=history)


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST' and 'f_emil' in request.form:
        email = request.form['f_emil']
        sql = f"SELECT * FROM USER WHERE email = '{email}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        dictionary = ibm_db.fetch_both(stmt)
        if dictionary:
            otp = generateOTP()
            custom_send_mail(email, otp)
            x = datetime.datetime(2020, 5, 17)
            sql = "SELECT * FROM FORGOT WHERE email =?"
            stmt = ibm_db.prepare(conn, sql)
            ibm_db.bind_param(stmt, 1, email)
            ibm_db.execute(stmt)
            account = ibm_db.fetch_assoc(stmt)
            if account:
                sql = f"DELETE FROM FORGOT WHERE email='{escape(email)}'"
                stmt = ibm_db.exec_immediate(conn, sql)
            insert_sql = "INSERT INTO FORGOT VALUES (?,?,?)"
            prep_stmt = ibm_db.prepare(conn, insert_sql)
            ibm_db.bind_param(prep_stmt, 1, email)
            ibm_db.bind_param(prep_stmt, 2, otp)
            ibm_db.bind_param(prep_stmt, 3, x)
            ibm_db.execute(prep_stmt)
            return render_template('forgot_password.html', error='Successfully OTP sent!')
        return render_template('forgot_password.html', error='User not found!')

    elif request.method == 'POST' and 'f_otp' in request.form:
        otp = request.form['f_otp']
        psw = request.form['f_psw']
        psws = request.form['f_psws']
        if psw != psws:
            return render_template('forgot_password.html', error='Password mismatch!')
        sql = f"SELECT * FROM FORGOT WHERE otp = '{otp}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        dictionary = ibm_db.fetch_both(stmt)
        if dictionary:
            email_n = dictionary['EMAIL']
            sql = f"SELECT * FROM USER WHERE email = '{escape(email_n)}'"
            stmt = ibm_db.exec_immediate(conn, sql)
            dictionary_of = ibm_db.fetch_both(stmt)
            if dictionary_of:
                name_p = dictionary_of['NAME']
                email_p = dictionary['EMAIL']
                sql = f"DELETE FROM USER WHERE email='{escape(email_p)}'"
                stmt = ibm_db.exec_immediate(conn, sql)
                insert_sql = f"INSERT INTO USER VALUES (?,?,?)"
                prep_stmt = ibm_db.prepare(conn, insert_sql)
                ibm_db.bind_param(prep_stmt, 1, name_p)
                ibm_db.bind_param(prep_stmt, 2, email_p)
                ibm_db.bind_param(prep_stmt, 3, aes_gcm_encrypt(bytes(psws, 'utf-8'), bytes(KEY, 'utf-8')))
                sql = f"DELETE FROM FORGOT WHERE email='{escape(email_p)}'"
                stmt = ibm_db.exec_immediate(conn, sql)
                return render_template('index.html', error='Password was successfully changed!')
            return render_template('index.html', error='Something went wrong!')
        return render_template('forgot_password.html', error='OTP mismatch!')

    if request.method == 'GET':
        return render_template('forgot_password.html')
    return render_template('index.html')


if __name__ == '__main__':
    app.debug = True
    app.run()
