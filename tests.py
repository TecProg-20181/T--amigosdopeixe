import unittest
from handletask import HandleTask
from person import Person
from os import remove


class TestHandleTask(unittest.TestCase):
    def test_date_format_assert_false(self):
        date = '30/30/30'
        value = HandleTask.date_format(self, date)
        self.assertFalse(value)

    def test_date_format_assert_true(self):
        date = '10/05/2010'
        value = HandleTask.date_format(self, date)
        self.assertTrue(value)

    def test_get_id_list_returns_list(self):
        msg = '1 2 3 4 5'
        value = HandleTask.get_id_list(self, msg)
        self.assertIsInstance(value, list)


class TestToken(unittest.TestCase):
    def test_show_token_str(self):
        file = 'token.txt'
        token = Person.showToken(file)
        self.assertIsInstance(token, str)

    def test_show_login_str(self):
        # file = open('login_test.txt', 'w')
        # file.write("usuario")
        file = 'login.txt'
        login = Person.showLogin(file)
        # remove('login_test.txt')
        self.assertIsInstance(login, str)

    def test_show_password_str(self):
        file = 'password.txt'
        password = Person.showLogin(file)
        self.assertIsInstance(password, str)


if __name__ == '__main__':
    unittest.main()
