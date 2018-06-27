import json
import requests
import urllib
from person import Person

class PeixeBot():
    def __init__(self):
        self.tokenread = Person.showToken("token.txt")
        self.loginread = Person.showLogin("login.txt")
        self.passwordread = Person.showPassword("password.txt")
        self.URL = "https://api.telegram.org/bot{}/".format(tokenread.rstrip())

        self.HELP = """
                    /new NOME
                    /todo ID1 ID2 ID3...
                    /doing ID ID2 ID3...
                    /done ID ID2 ID3...
                    /delete ID
                    /list
                    /rename ID NOME
                    /dependson ID ID...
                    /duplicate ID
                    /duedate ID DATE(mm/dd/YYYY)
                    /priority ID PRIORITY{low, medium, high}
                    priority low = """ + Emojis.EMOJI_LOW.value + """
                    priority medium = """ + Emojis.EMOJI_MEDIUM.value + """
                    priority high = """ + Emojis.EMOJI_HIGH.value + """
                    /help
                    """

    def get_url(url):
        response = requests.get(url)
        content = response.content.decode("utf8")
        return content

    def get_json_from_url(url):
        content = get_url(url)
        js = json.loads(content)
        return js

    def get_updates(offset=None):
        url = URL + "getUpdates?timeout=100"
        if offset:
            url += "&offset={}".format(offset)
        js = get_json_from_url(url)
        return js

    def send_message(text, chat_id, reply_markup=None):
        text = urllib.parse.quote_plus(text)
        url = URL + "sendMessage?text={}&chat_id={}\
                    &parse_mode=Markdown".format(text, chat_id)
        if reply_markup:
            url += "&reply_markup={}".format(reply_markup)
        get_url(url)
    
    def get_last_update_id(updates):
        update_ids = []
        for update in updates["result"]:
            update_ids.append(int(update["update_id"]))

        return max(update_ids)
    
    def create_issue(title, body=None):
        url = 'https://api.github.com/repos/TecProg-20181/T--amigosdopeixe/issues'
        request = requests.Session()
        request.auth =(loginread.rstrip(), passwordread.rstrip())
        issue = {'title': title,
                'body': body}
        post = request.post(url, json.dumps(issue))
        if post.status_code == 201:
            print ('Issue is created!')
        else:
            print ("Issue not created.") 