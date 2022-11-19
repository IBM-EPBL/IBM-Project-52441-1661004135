import unittest

try:
    from app import app

except Exception as e:
    print('Some modules missing {}'.format(e))


class FlaskTest(unittest.TestCase):

    # check if response is 200
    def test_index(self):
        tester = app.test_client(self)
        response = tester.get("/")
        statuscode = response.status_code
        self.assertEqual(statuscode, 200)

    # check content type
    def test_index_content(self):
        tester = app.test_client(self)
        response = tester.get("/")
        self.assertEqual(response.content_type, 'text/html; charset=utf-8')

    def test_register(self):
        tester = app.test_client(self)
        response = tester.post('/register', data=dict(email='username', password='password'), follow_redirects=True)
        self.assertTrue(b'email' in response.data)

    # check log in
    def test_login(self):
        tester = app.test_client(self)
        response = tester.post('/', data=dict(email='username', password='password'), follow_redirects=True)
        self.assertTrue(b'email' in response.data)

    # checking forgot function
    def test_forgot(self):
        tester = app.test_client(self)
        response = tester.post('/', data=dict(email='username'), follow_redirects=True)
        self.assertTrue(b'email' in response.data)


if __name__ == '__main__':
    unittest.main()
