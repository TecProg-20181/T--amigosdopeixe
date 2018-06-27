#!/usr/bin/env python3

import json
import requests
import time
import urllib
import sqlalchemy
import db
from person import Person
from emojis import Emojis
from db import Task
from datetime import datetime

tokenread = Person.showToken("token.txt")

loginread = Person.showLogin("login.txt")

passwordread = Person.showPassword("password.txt")

URL = "https://api.telegram.org/bot{}/".format(tokenread.rstrip())


HELP = """
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


def deps_text(task, chat, preceed=''):
    text = ''

    for i in range(len(task.dependencies.split(',')[:-1])):
        line = preceed
        query = db.session.query(Task).\
            filter_by(id=int(task.dependencies.split(',')[:-1][i]), chat=chat)
        dep = query.one()

        icon = Emojis.EMOJI_TODO
        if dep.status == 'DOING':
            icon = Emojis.EMOJI_DOING
        elif dep.status == 'DONE':
            icon = Emojis.EMOJI_DONE

        if i + 1 == len(task.dependencies.split(',')[:-1]):
            line += '└── [[{}]] {} {}\n'.format(dep.id, icon, dep.name)
            line += deps_text(dep, chat, preceed + '    ')
        else:
            line += '├── [[{}]] {} {}\n'.format(dep.id, icon, dep.name)
            line += deps_text(dep, chat, preceed + '│   ')

        text += line

    return text


def is_msg_digit(msg, chat):
    if msg.isdigit():
        return True
    send_message("The task id is missing or invalid", chat)
    return False


def new_task(msg, chat):
    task = Task(chat=chat, name=msg, status='TODO',
                dependencies='', parents='', priority='')
    db.session.add(task)
    db.session.commit()
    send_message("New task *TODO* [[{}]] {}".format(task.id, task.name), chat)
    create_issue(task.name, 'Task ID: [{}]\n\ Task Name: {}'.format(task.id, task.name))


def rename_task(msg, chat):
    new_name = ''
    if msg != '':
        if len(msg.split(' ', 1)) > 1:
            new_name = msg.split(' ', 1)[1]
        msg = msg.split(' ', 1)[0]

    if is_msg_digit(msg, chat):
        task_id = int(msg)
        query = db.session.query(Task).filter_by(id=task_id, chat=chat)
        try:
            task = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            send_message("_404_ Task {} not found x.x".format(task_id), chat)
            return

        if new_name == '':
            send_message("You want to modify task {},\
                         but you didn't provide any new text".
                         format(task_id), chat)
            return

        old_name = task.name
        task.name = new_name
        db.session.commit()
        send_message("Task {} redefined from {} to {}".
                     format(task_id, old_name, new_name), chat)


def list_tasks(msg, chat):
    response = ''
    response += Emojis.EMOJI_TASK.value + 'Task List\n'
    query = db.session.query(Task).filter_by(parents='',
                                             chat=chat).order_by(Task.id)

    for task in query.all():
        if task.status == 'DOING':
            icon = Emojis.EMOJI_DOING.value
        elif task.status == 'DONE':
            icon = Emojis.EMOJI_DONE.value
        elif task.status == 'TODO':
            icon = Emojis.EMOJI_TODO.value

        response += '[[{}]] {} {} {} *DEADLINE:* {}\n'.format(task.id, icon, task.name, task.priority, task.duedate)
        response += deps_text(task, chat)

    send_message(response, chat)
    response = ''

    response += Emojis.EMOJI_STATUS.value + ' _Status_\n'

    query = db.session.query(Task).filter_by(status='TODO',
                                             chat=chat).order_by(Task.id)
    response += '\n' + Emojis.EMOJI_TODO.value + ' *TODO*\n'
    for task in query.all():
        response += '[[{}]] {} {} *DEADLINE:*{}\n'.format(task.id, task.name, task.priority, task.duedate)
    query = db.session.query(Task).filter_by(status='DOING',
                                             chat=chat).order_by(Task.id)

    response += '\n' + Emojis.EMOJI_DOING.value + ' *DOING*\n'
    for task in query.all():
        response += '[[{}]] {} {} *DEADLINE:*{}\n'.format(task.id, task.name, task.priority, task.duedate)
    query = db.session.query(Task).filter_by(status='DONE',
                                             chat=chat).order_by(Task.id)

    response += '\n' + Emojis.EMOJI_DONE.value + ' *DONE*\n'
    for task in query.all():
        response += '[[{}]] {} {}\n'.format(task.id, task.name, task.priority)

    send_message(response, chat)


def duplicate_task(msg, chat):
    if is_msg_digit(msg, chat):
        task_id = int(msg)
        query = db.session.query(Task).filter_by(id=task_id, chat=chat)
        try:
            task = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            send_message("_404_ Task {} not found x.x".format(task_id), chat)
            return

        new_task = Task(chat=task.chat, name=task.name, status=task.status,
                        dependencies=task.dependencies, parents=task.parents,
                        priority=task.priority, duedate=task.duedate)

        db.session.add(new_task)

        for t in task.dependencies.split(',')[:-1]:
            qy = db.session.query(Task).filter_by(id=int(t), chat=chat)
            t = qy.one()
            t.parents += '{},'.format(new_task.id)

        db.session.commit()
        send_message("New task *TODO* [[{}]] {}".
                     format(new_task.id, new_task.name), chat)


def get_id_list(msg):
    id_list = msg.split(' ')
    return id_list


def update_status(msg, status, chat):
    ids = get_id_list(msg)
    print(ids)
    for id in ids:
        if(is_msg_digit(id, chat)):
            task_id = int(id)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                send_message("_404_ Task {} not found x.x".format(task_id),
                             chat)
                return
            task.status = status
            db.session.commit()
            send_message("*" + status + "* task [[{}]] {} {}".format(
                         task.id, task.name, task.priority), chat)


def delete_task(msg, chat):
    if is_msg_digit(msg, chat):
        task_id = int(msg)
        query = db.session.query(Task).filter_by(id=task_id, chat=chat)
        try:
            task = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            send_message("_404_ Task {} not found x.x".format(task_id), chat)
            return
        for t in task.dependencies.split(',')[:-1]:
            qy = db.session.query(Task).filter_by(id=int(t), chat=chat)
            t = qy.one()
            t.parents = t.parents.replace('{},'.format(task.id), '')
        for t in task.parents.split(',')[:-1]:
            query = db.session.query(Task).filter_by(id=int(t), chat=chat)
            t = query.one()
            t.dependencies = t.dependencies.replace('{},'.format(task.id), '')

        db.session.delete(task)
        db.session.commit()
        send_message("Task [[{}]] deleted".format(task_id), chat)


def add_dependency(msg, chat):
    text = ''
    if msg != '':
        if len(msg.split(' ', 1)) > 1:
            text = msg.split(' ', 1)[1]
        msg = msg.split(' ', 1)[0]

    if is_msg_digit(msg, chat):
        task_id = int(msg)
        query = db.session.query(Task).filter_by(id=task_id, chat=chat)
        try:
            task = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            send_message("_404_ Task {} not found x.x".format(task_id), chat)
            return

        if text == '':
            for i in task.dependencies.split(',')[:-1]:
                i = int(i)
                q = db.session.query(Task).filter_by(id=i, chat=chat)
                t = q.one()
                t.parents = t.parents.replace('{},'.format(task.id), '')

            task.dependencies = ''
            send_message("Dependencies removed from task {}"
                         .format(task_id), chat)
        else:
            for depid in text.split(' '):
                if not depid.isdigit():
                    send_message("All dependencies ids must be numeric,\
                                 and not {}".format(depid), chat)
                else:
                    depid = int(depid)
                    query = db.session.query(Task).filter_by(id=depid,
                                                             chat=chat)
                    try:
                        taskdep = query.one()
                        taskdep.parents += str(task.id) + ','
                    except sqlalchemy.orm.exc.NoResultFound:
                        send_message("_404_ Task {} not found x.x"
                                     .format(depid), chat)
                        continue

                    deplist = task.dependencies.split(',')
                    if str(depid) not in deplist:
                        task.dependencies += str(depid) + ','

        db.session.commit()
        send_message("Task {} dependencies up to date".format(task_id), chat)


def change_priority(msg, chat):
    priority = ''
    if msg != '':
        if len(msg.split(' ', 1)) > 1:
            priority = msg.split(' ', 1)[1]
        msg = msg.split(' ', 1)[0]

    if is_msg_digit(msg, chat):
        task_id = int(msg)
        query = db.session.query(Task).filter_by(id=task_id, chat=chat)
        try:
            task = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            send_message("_404_ Task {} not found x.x".format(task_id), chat)
            return

        if priority == '':
            task.priority = ''
            send_message("_Cleared_ all priorities from task {}"
                         .format(task_id), chat)
        else:
            if priority.lower() not in ['high', 'medium', 'low']:
                send_message("The priority *must be* one of the following:\
                              high, medium, low", chat)
            else:
                if priority.lower() == 'low':
                    task.priority = Emojis.EMOJI_LOW.value
                elif priority.lower() == 'medium':
                    task.priority = Emojis.EMOJI_MEDIUM.value
                elif priority.lower() == 'high':
                    task.priority = Emojis.EMOJI_HIGH.value

                send_message("*Task {}* priority has priority *{}*"
                             .format(task_id, priority.lower()), chat)
        db.session.commit()


def date_format(text):
    try:
        datetime.strptime(text, '%m/%d/%Y')
        return True
    except ValueError:
        return False


def duedate(msg, chat):
            text = ''
            if msg != '':
                if len(msg.split(' ', 1)) > 1:
                    text = msg.split(' ', 1)[1]
                    msg = msg.split(' ', 1)[0]

                    if not msg.isdigit():
                        send_message("You must inform the task id", chat)
                    else:
                        task_id = int(msg)
                        query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                        try:
                            task = query.one()
                        except sqlalchemy.orm.exc.NoResultFound:
                            send_message("_404_ Task {} not found x.x".format(task_id), chat)
                            return

                        if text == '':
                            send_message("You want to give a duedate to task {}, but you didn't provide any date".format(task_id), chat)
                            return
                        else:
                            if not date_format(text):
                                send_message("The duedate needs to be on US Format: mm/dd/YYYY", chat)
                            else:
                                task.duedate = datetime.strptime(text, '%m/%d/%Y')
                                send_message("Task {} deadline is on: {}".format(task_id, text), chat)
                        db.session.commit()


def handle_updates(updates):
    for update in updates["result"]:
        if 'message' in update:
            message = update['message']
        elif 'edited_message' in update:
            message = update['edited_message']
        else:
            print('Can\'t process! {}'.format(update))
            return

        command = message["text"].split(" ", 1)[0]
        msg = ''
        if len(message["text"].split(" ", 1)) > 1:
            msg = message["text"].split(" ", 1)[1].strip()

        chat = message["chat"]["id"]

        print(command, msg, chat)

        if command == '/new':
            new_task(msg, chat)

        elif command == '/rename':
            rename_task(msg, chat)

        elif command == '/duplicate':
            duplicate_task(msg, chat)

        elif command == '/delete':
            delete_task(msg, chat)

        elif command == '/todo':
            update_status(msg, "TODO", chat)

        elif command == '/doing':
            update_status(msg, "DOING", chat)

        elif command == '/done':
            update_status(msg, "DONE", chat)

        elif command == '/list':
            list_tasks(msg, chat)

        elif command == '/dependson':
            add_dependency(msg, chat)

        elif command == '/priority':
            change_priority(msg, chat)

        elif command == '/start':
            send_message("Welcome! Here is a list of things you can do.", chat)
            send_message(HELP, chat)

        elif command == '/help':
            send_message("Here is a list of things you can do.", chat)
            send_message(HELP, chat)
        elif command == '/duedate':
            duedate(msg, chat)

        else:
            send_message("I'm sorry dave. I'm afraid I can't do that.", chat)


def main():
    last_update_id = None

    while True:
        
        print("Updates")
        updates = get_updates(last_update_id)

        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            handle_updates(updates)

        time.sleep(0.5)


if __name__ == '__main__':
    main()
