from flask import Flask, render_template, url_for, request
import ibm_db

import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

SENDGRID_API_KEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # sendgrid

conn = ibm_db.connect(
    "DATABASE=bludb;HOSTNAME=ea286ace-86c7-4db-850-3fbfa461c66.bs2io90l081od8lcg.databases.appdomain.cloud;PORT"
    "=31505;SECURITY=SSL;SSLServerCertificate=DigiCertGlobalRootCA.crt;UID=xnc98967;PWD=wQioPYLq4Oanh0",
    '', '')

print(conn)

app = Flask(__name__)

app.secret_key = "\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"


# sendgrid
def send_mail(email):
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    from_email = Email("xxxxxxxxxxxxxxxxxx@gmail.com")  # Change to your verified sender
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
    print(response.status_code)
    print(response.headers)


@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def homepage():
    if request.method == 'POST' and 'email' in request.form and 'pass' in request.form:
        return render_template('index.html', error="Wrong Password!")

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
                ibm_db.bind_param(prep_stmt, 3, pass_up)
                ibm_db.execute(prep_stmt)
                send_mail(email_up)
                return render_template('index.html', error="Successfully created")
            except ibm_db.stmt_error:
                print(ibm_db.stmt_error())
                return render_template('index.html', error="Failed to create Account")
    return render_template('index.html')


if __name__ == '__main__':
    app.debug = True
    app.run()