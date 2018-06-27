
class Person:

    def __init__(self, login, password, token):
        self.login = login
        self.password = password
        self.token = token
    
    def showLogin(AUTHORIZATION_LOGIN_FILENAME):
        loginopen = open(AUTHORIZATION_LOGIN_FILENAME, 'r')
        login = loginopen.readline()
        return login

    def showPassword(AUTHORIZATION_PASSWORD_FILENAME):
        passwordopen = open(AUTHORIZATION_PASSWORD_FILENAME, 'r')
        password = passwordopen.readline()  
        return password

    def showToken(TOKEN_FILENAME):
        tokenopen = open(TOKEN_FILENAME, 'r')
        token = tokenopen.readline() 
        return token