import binascii
import math
import random
import requests as res
import secrets
import time
from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d
from pytz import timezone
from datetime import datetime
import os

import ibm_db
import sendgrid
from clarifai_grpc.channel.clarifai_channel import ClarifaiChannel
from clarifai_grpc.grpc.api import resources_pb2, service_pb2, service_pb2_grpc
from clarifai_grpc.grpc.api.status import status_code_pb2
from cryptography.fernet import InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from flask import Flask, render_template, request, session, redirect

from markupsafe import escape
from sendgrid.helpers.mail import Mail, Email, To, Content

# clarifai
YOUR_CLARIFAI_API_KEY = os.environ.get('CLARIFAI_API_KEY')
YOUR_APPLICATION_ID = os.environ.get('APP_ID')

# key for hashing
KEY = os.environ.get('KEY')
# sendgrid API key
SENDGRID_API_KEY = os.environ.get('S_API_KEY')

# admin email
E_MAIL = os.environ.get('EMAIL_ID')

# DATABASE connection credentials
conn = ibm_db.connect(
    "DATABASE=bludb;HOSTNAME=ea245ace-86c7-4d5b-8220-3fbfa46b1c66.bs2io90l08kqb1od8lcg.databases.appdomain.cloud;PORT"
    "=30121;SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID=xnc26467;PWD=whgFkKYLq4Oanh0V",
    '', '')

# header for nutrition API.
headers = {"content-type": "application/x-www-form-urlencoded",
           "X-RapidAPI-Key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
           "X-RapidAPI-Host": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
           }

metadata = (("authorization", f"Key {YOUR_CLARIFAI_API_KEY}"),)
channel = ClarifaiChannel.get_json_channel()
stub = service_pb2_grpc.V2Stub(channel)

# rapid API
url = os.environ.get('URL_ID')
querystring = os.environ.get('Q_STRING')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif'}

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY')


# sendgrid
def send_mail(email):
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    from_email = Email(os.environ.get('EMAIL_ID'))
    to_email = To(email)  # Change to your recipient
    subject = "Nutrition is a basic human need and a prerequisite for healthy life"
    content = Content("text/plain",
                      "Thank you for creating an account on our platform. Now you can utilise our platform "
                      "to maintain a healthier life.")
    mail = Mail(from_email, to_email, subject, content)

    # Get a JSON-ready representation of the Mail object
    mail_json = mail.get()
    sg.client.mail.send.post(request_body=mail_json)


def custom_send_mail(email, data):
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    from_email = Email(os.environ.get('EMAIL_ID'))
    to_email = To(email)  # Change to your recipient
    subject = "Nutrition is a basic human need and a prerequisite for healthy life"
    content = Content("text/plain",
                      f"'{data}'")
    mail = Mail(from_email, to_email, subject, content)

    # Get a JSON-ready representation of the Mail object
    mail_json = mail.get()
    sg.client.mail.send.post(request_body=mail_json)


def generateOTP():
    digits = os.environ.get('DIGIT')
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
    history = []
    sql = f"SELECT * FROM PERSON WHERE time = '{time}'"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_both(stmt)
    while dictionary:
        history.append(dictionary)
        dictionary = ibm_db.fetch_both(stmt)
    return history


def get_user():
    user = []
    sql = f"SELECT * FROM USER"
    stmt = ibm_db.exec_immediate(conn, sql)
    dictionary = ibm_db.fetch_both(stmt)
    while dictionary:
        user.append(dictionary)
        dictionary = ibm_db.fetch_both(stmt)
    return user


backend = default_backend()


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
        sql = f"SELECT * FROM USER WHERE email='{escape(email_user)}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_row(stmt)
        if row:
            sql = f"DELETE FROM USER WHERE email='{escape(email_user)}'"
            stmt = ibm_db.exec_immediate(conn, sql)
        sql = f"SELECT * FROM PERSON WHERE email='{escape(email_user)}'"
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_row(stmt)
        if row:
            sql = f"DELETE FROM PERSON WHERE email='{escape(email_user)}'"
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
                msg = 'A new user was registered to your platform, name : {}'.format(name)
                custom_send_mail(E_MAIL, msg)
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
            requests = service_pb2.PostModelOutputsRequest(
                model_id="food-item-recognition",
                user_app_id=resources_pb2.UserAppIDSet(app_id=YOUR_APPLICATION_ID),
                inputs=[
                    resources_pb2.Input(
                        data=resources_pb2.Data(image=resources_pb2.Image(base64=baseimage))
                    )
                ],
            )
            response = stub.PostModelOutputs(requests, metadata=metadata)

            if response.status.code != status_code_pb2.SUCCESS:
                return render_template('dashboard.html', msg=f'Failed {response.status}', history=history)

            calcium = 0
            vitaminb5 = 0
            protein = 0
            vitamind = 0
            vitamina = 0
            vitaminb2 = 0
            carbohydrates = 0
            fiber = 0
            fat = 0
            sodium = 0
            vitaminc = 0
            calories = 0
            vitaminb1 = 0
            folicacid = 0
            sugar = 0
            vitamink = 0
            cholesterol = 0
            potassium = 0
            monounsaturatedfat = 0
            polyunsaturatedfat = 0
            saturatedfat = 0
            totalfat = 0
            calciumu = 'g'
            vitaminb5u = 'g'
            proteinu = 'g'
            vitamindu = 'g'
            vitaminau = 'g'
            carbohydratesu = 'g'
            sodiumu = 'g'
            vitamincu = 'g'
            caloriesu = 'cal'
            sugaru = 'g'
            cholesterolu = 'g'
            potassiumu = 'g'
            monounsaturatedfatu = 'g'
            polyunsaturatedfatu = 'g'
            saturatedfatu = 'g'

            for concept in response.outputs[0].data.concepts:
                print("%12s: %.2f" % (concept.name, concept.value))
                if concept.value > 0.5:
                    payload = "ingredientList=" + concept.name + "&servings=1"
                    response1 = res.request("POST", url, data=payload, headers=headers, params=querystring)
                    data = response1.json()
                    for i in range(0, 1):
                        nutri_array = data[i]
                        nutri_dic = nutri_array['nutrition']
                        nutri = nutri_dic['nutrients']

                        for z in range(0, len(nutri)):
                            temp = nutri[z]
                            if temp['name'] == 'Calcium':
                                calcium += round(temp['amount'], 2)
                                calciumu = temp['unit']
                            elif temp['name'] == 'Vitamin B5':
                                vitaminb5 += round(temp['amount'], 2)
                                vitaminb5u = temp['unit']
                            elif temp['name'] == 'Protein':
                                protein += round(temp['amount'], 2)
                                proteinu = temp['unit']
                            elif temp['name'] == 'Vitamin D':
                                vitamind += round(temp['amount'], 2)
                                vitamindu = temp['unit']
                            elif temp['name'] == 'Vitamin A':
                                vitamina += round(temp['amount'], 2)
                                vitaminau = temp['unit']
                            elif temp['name'] == 'Vitamin B2':
                                vitaminb2 += round(temp['amount'], 2)
                                vitaminb2u = temp['unit']
                            elif temp['name'] == 'Carbohydrates':
                                carbohydrates += round(temp['amount'], 2)
                                carbohydratesu = temp['unit']
                            elif temp['name'] == 'Fiber':
                                fiber += round(temp['amount'], 2)
                                fiberu = temp['unit']
                            elif temp['name'] == 'Vitamin C':
                                vitaminc += round(temp['amount'], 2)
                                vitamincu = temp['unit']
                            elif temp['name'] == 'Calories':
                                calories += round(temp['amount'], 2)
                                caloriesu = 'cal'
                            elif temp['name'] == 'Vitamin B1':
                                vitaminb1 += round(temp['amount'], 2)
                                vitaminb1u = temp['unit']
                            elif temp['name'] == 'Folic Acid':
                                folicacid += round(temp['amount'], 2)
                                folicacidu = temp['unit']
                            elif temp['name'] == 'Sugar':
                                sugar += round(temp['amount'], 2)
                                sugaru = temp['unit']
                            elif temp['name'] == 'Vitamin K':
                                vitamink += round(temp['amount'], 2)
                                vitaminku = temp['unit']
                            elif temp['name'] == 'Cholesterol':
                                cholesterol += round(temp['amount'], 2)
                                cholesterolu = temp['unit']
                            elif temp['name'] == 'Mono Unsaturated Fat':
                                monounsaturatedfat += round(temp['amount'], 2)
                                monounsaturatedfatu = temp['unit']
                            elif temp['name'] == 'Poly Unsaturated Fat':
                                polyunsaturatedfat += round(temp['amount'], 2)
                                polyunsaturatedfatu = temp['unit']
                            elif temp['name'] == 'Saturated Fat':
                                saturatedfat += round(temp['amount'], 2)
                                saturatedfatu = temp['unit']
                            elif temp['name'] == 'Fat':
                                fat += round(temp['amount'], 2)
                                fatu = temp['unit']
                            elif temp['name'] == 'Sodium':
                                sodium += round(temp['amount'], 2)
                                sodiumu = temp['unit']
                            elif temp['name'] == 'Potassium':
                                potassium += round(temp['amount'], 2)
                                potassiumu = temp['unit']
                            else:
                                pass

            totalfat += saturatedfat + polyunsaturatedfat + monounsaturatedfat
            data = [round(calories, 2), round(totalfat, 2), round(saturatedfat, 2), round(polyunsaturatedfat, 2),
                    round(monounsaturatedfat, 2), round(cholesterol, 2), round(sodium, 2), round(potassium, 2),
                    round(sugar, 2), round(protein, 2), round(carbohydrates, 2), round(vitamina, 2), round(vitaminc, 2),
                    round(vitamind, 2), round(vitaminb5, 2), round(calcium, 2)]

            unit = [caloriesu, "g", saturatedfatu, polyunsaturatedfatu, monounsaturatedfatu, cholesterolu, sodiumu,
                    potassiumu, sugaru, proteinu, carbohydratesu, vitaminau, vitamincu, vitamindu, vitaminb5u, calciumu]

            to_string = "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(data[0], data[1], data[2], data[3],
                                                                                 data[4],
                                                                                 data[5], data[6], data[7], data[8],
                                                                                 data[9],
                                                                                 data[10], data[11], data[12], data[13],
                                                                                 data[14], data[15])

            to_unit = "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(unit[0], unit[1], unit[2], unit[3],
                                                                               unit[4], unit[5], unit[6], unit[7],
                                                                               unit[8], unit[9], unit[10], unit[11],
                                                                               unit[12], unit[13], unit[14], unit[15])

            current_time = datetime.now(timezone("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')

            complete_value = to_string + ',' + to_unit
            val_arr = complete_value.split(',')

            to_units = "Calories : {}{}" \
                       "Total Fat : {}{}" \
                       "Saturated Fat : {}{}" \
                       "Polyunsaturated Fat : {}{}" \
                       "Monounsaturated Fat : {}{}" \
                       "Cholesterol : {}{}" \
                       "Sodium : {}{}" \
                       "Potassium : {}{}" \
                       "Sugar : {}{}" \
                       "Protein : {}{}" \
                       "Carbohydrates : {}{}" \
                       "Vitamin A : {}{}" \
                       "Vitamin C : {}{}" \
                       "Vitamin D : {}{}" \
                       "Vitamin B5 : {}{}" \
                       "Calcium : {}{}".format(data[0], unit[1], data[1], unit[1], data[2], unit[2], data[3], unit[3],
                                               data[4], unit[4], data[5], unit[5], data[6], unit[6], data[7], unit[7],
                                               data[8], unit[8], data[9], unit[9], data[10], unit[10], data[11],
                                               unit[11], data[12], unit[12], data[13], unit[13], data[14], unit[14],
                                               data[15], unit[15])

            custom_send_mail(session['email'], to_units)

            try:
                insert_sql = "INSERT INTO PERSON VALUES (?,?,?,?)"
                prep_stmt = ibm_db.prepare(conn, insert_sql)
                ibm_db.bind_param(prep_stmt, 1, session['name'])
                ibm_db.bind_param(prep_stmt, 2, session['email'])
                ibm_db.bind_param(prep_stmt, 3, complete_value)
                ibm_db.bind_param(prep_stmt, 4, current_time)
                ibm_db.execute(prep_stmt)
                return render_template('dashboard.html', user=session['name'], email=session['email'], data=val_arr,
                                       history=history)
            except ibm_db.stmt_error:
                print(ibm_db.stmt_error())
                return render_template('dashboard.html', msg='Something wnt wrong', user=session['name'],
                                       email=session['email'], data=val_arr, history=history)

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
            otp = "OTP : " + otp
            custom_send_mail(email, otp)
            current_time = datetime.now(timezone("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S')
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
            ibm_db.bind_param(prep_stmt, 3, current_time)
            ibm_db.execute(prep_stmt)
            return render_template('forgot_password.html', error='Successfully OTP sent!')
        return render_template('forgot_password.html', error='User not found!')

    elif request.method == 'POST' and 'f_otp' in request.form:
        otp = request.form['f_otp']
        psw = request.form['f_psw']
        psws = request.form['f_psws']
        if psw != psws:
            return render_template('forgot_password.html', error='Password mismatch!')
        sql_f = f"SELECT * FROM FORGOT WHERE otp = '{otp}'"
        stmt_f = ibm_db.exec_immediate(conn, sql_f)
        dictionary = ibm_db.fetch_both(stmt_f)
        if dictionary:
            email_n = dictionary['EMAIL']
            sql_u = f"SELECT * FROM USER WHERE email = '{escape(email_n)}'"
            stmt_u = ibm_db.exec_immediate(conn, sql_u)
            dictionary_of = ibm_db.fetch_both(stmt_u)
            if dictionary_of:
                name_p = dictionary_of['NAME']
                email_p = dictionary['EMAIL']
                sqlf = f"DELETE FROM USER WHERE email='{escape(email_p)}'"
                stmt = ibm_db.exec_immediate(conn, sqlf)
                insert_sql = f"INSERT INTO USER VALUES (?,?,?)"
                prep_stmt = ibm_db.prepare(conn, insert_sql)
                ibm_db.bind_param(prep_stmt, 1, name_p)
                ibm_db.bind_param(prep_stmt, 2, email_p)
                ibm_db.bind_param(prep_stmt, 3, aes_gcm_encrypt(bytes(psws, 'utf-8'), bytes(KEY, 'utf-8')))
                ibm_db.execute(prep_stmt)
                sql_s = f"DELETE FROM FORGOT WHERE email='{escape(email_p)}'"
                stmt = ibm_db.exec_immediate(conn, sql_s)
                return render_template('index.html', error='Password was successfully changed!')
            return render_template('index.html', error='Something went wrong!')
        return render_template('forgot_password.html', error='OTP mismatch!')

    if request.method == 'GET':
        return render_template('forgot_password.html')
    return render_template('index.html')


if __name__ == '__main__':
    app.debug = False
    app.run(host="0.0.0.0", port=5000)
