#!/usr/bin/env python3

import json
import requests
import time
import urllib
import sqlalchemy
import db
from db import Task

TOKEN_FILENAME = "token.txt"

tokenopen = open(TOKEN_FILENAME, 'r')
tokenread = tokenopen.readline()
URL = "https://api.telegram.org/bot{}/".format(tokenread.rstrip())

EMOJI_DONE = '\U00002611'
EMOJI_STATUS = '\U0001F4DD'
EMOJI_TASK = '\U0001F4CB'
EMOJI_DOING = '\U000023FA'
EMOJI_TODO = '\U0001F195'
EMOJI_LOW = '\U0001F600'
EMOJI_MEDIUM = '\U0001F610'
EMOJI_HIGH = '\U0001F621'

HELP = """
 /new NOME
 /todo ID
 /doing ID
 /done ID
 /delete ID
 /list
 /rename ID NOME
 /dependson ID ID...
 /duplicate ID
 /priorityview
 /priority ID PRIORITY{low, medium, high}
 priority low = """ + EMOJI_LOW + """
 priority medium = """ + EMOJI_MEDIUM + """
 priority high = """ + EMOJI_HIGH + """
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
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
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
        query = db.session.query(Task).filter_by(id=int(task.dependencies.split(',')[:-1][i]), chat=chat)
        dep = query.one()

        icon = '\U0001F195'
        if dep.status == 'DOING':
            icon = '\U000023FA'
        elif dep.status == 'DONE':
            icon = '\U00002611'

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
    send_message("You must inform the task id", chat)
    return False


def new_task(msg, chat):
    task = Task(chat=chat, name=msg, status='TODO',
                dependencies='', parents='', priority='')
    db.session.add(task)
    db.session.commit()
    send_message("New task *TODO* [[{}]] {}".format(task.id, task.name), chat)


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
    response += EMOJI_TASK + 'Task List\n'
    query = db.session.query(Task).filter_by(parents='',
                                             chat=chat).order_by(Task.id)

    for task in query.all():
        if task.status == 'DOING':
            icon = EMOJI_DOING
        elif task.status == 'DONE':
            icon = EMOJI_DONE
        elif task.status == 'TODO':
            icon = EMOJI_TODO

        response += '[[{}]] {} {} {}\n'.format(task.id,
                                               icon, task.name, task.priority)
        response += deps_text(task, chat)

    send_message(response, chat)
    response = ''

    response += EMOJI_STATUS + ' _Status_\n'

    query = db.session.query(Task).filter_by(status='TODO',
                                             chat=chat).order_by(Task.id)
    response += '\n' + EMOJI_TODO + ' *TODO*\n'
    for task in query.all():
        response += '[[{}]] {} {}\n'.format(task.id, task.name, task.priority)
    query = db.session.query(Task).filter_by(status='DOING',
                                             chat=chat).order_by(Task.id)

    response += '\n' + EMOJI_DOING + ' *DOING*\n'
    for task in query.all():
        response += '[[{}]] {} {}\n'.format(task.id, task.name, task.priority)
    query = db.session.query(Task).filter_by(status='DONE',
                                             chat=chat).order_by(Task.id)

    response += '\n' + EMOJI_DONE + ' *DONE*\n'
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
                    task.priority = EMOJI_LOW
                elif priority.lower() == 'medium':
                    task.priority = EMOJI_MEDIUM
                elif priority.lower() == 'high':
                    task.priority = EMOJI_HIGH

                send_message("*Task {}* priority has priority *{}*"
                             .format(task_id, priority.lower()), chat)
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
                db.session.delete(task)
                db.session.commit()
                send_message("Task [[{}]] deleted".format(task_id), chat)

        elif command == '/todo':
            if is_msg_digit(msg, chat):
                task_id = int(msg)
                query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                try:
                    task = query.one()
                except sqlalchemy.orm.exc.NoResultFound:
                    send_message("_404_ Task {} not found x.x".format(task_id), chat)
                    return
                task.status = 'TODO'
                db.session.commit()
                send_message("*TODO* task [[{}]] {} {}".format(task.id, task.name, task.priority), chat)

        elif command == '/doing':
            if is_msg_digit(msg, chat):
                task_id = int(msg)
                query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                try:
                    task = query.one()
                except sqlalchemy.orm.exc.NoResultFound:
                    send_message("_404_ Task {} not found x.x".format(task_id), chat)
                    return
                task.status = 'DOING'
                db.session.commit()
                send_message("*DOING* task [[{}]] {} {}".format(task.id, task.name, task.priority), chat)

        elif command == '/done':
            if is_msg_digit(msg, chat):
                task_id = int(msg)
                query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                try:
                    task = query.one()
                except sqlalchemy.orm.exc.NoResultFound:
                    send_message("_404_ Task {} not found x.x".format(task_id), chat)
                    return
                task.status = 'DONE'
                db.session.commit()
                send_message("*DONE* task [[{}]] {} {}".format(task.id, task.name, task.priority), chat)

        elif command == '/list':
            list_tasks(msg, chat)
        elif command == '/dependson':
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
                    send_message("Dependencies removed from task {}".format(task_id), chat)
                else:
                    for depid in text.split(' '):
                        if not depid.isdigit():
                            send_message("All dependencies ids must be numeric, and not {}".format(depid), chat)
                        else:
                            depid = int(depid)
                            query = db.session.query(Task).filter_by(id=depid, chat=chat)
                            try:
                                taskdep = query.one()
                                taskdep.parents += str(task.id) + ','
                            except sqlalchemy.orm.exc.NoResultFound:
                                send_message("_404_ Task {} not found x.x".format(depid), chat)
                                continue

                            deplist = task.dependencies.split(',')
                            if str(depid) not in deplist:
                                task.dependencies += str(depid) + ','

                db.session.commit()
                send_message("Task {} dependencies up to date".format(task_id), chat)
        elif command == '/priority':
            change_priority(msg, chat)
        elif command == '/start':
            send_message("Welcome! Here is a list of things you can do.", chat)
            send_message(HELP, chat)
        elif command == '/help':
            send_message("Here is a list of things you can do.", chat)
            send_message(HELP, chat)
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
