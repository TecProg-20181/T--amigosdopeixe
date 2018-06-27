import sqlalchemy
import db
from db import Task
from datetime import datetime
from theBot import PeixeBot
from emojis import Emojis

class HandleTask(PeixeBot):
    
    def __init__(self):
        PeixeBot.__init__(self)

    def deps_text(self, task, chat, preceed=''):
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
                line += self.deps_text(dep, chat, preceed + '    ')
            else:
                line += '├── [[{}]] {} {}\n'.format(dep.id, icon, dep.name)
                line += self.deps_text(dep, chat, preceed + '│   ')

            text += line

        return text

    def is_msg_digit(self, msg, chat):
        if msg.isdigit():
            return True
        self.send_message("The task id is missing or invalid", chat)
        return False


    def new_task(self, msg, chat):
        task = Task(chat=chat, name=msg, status='TODO',
                    dependencies='', parents='', priority='')
        db.session.add(task)
        db.session.commit()
        self.send_message("New task *TODO* [[{}]] {}".format(task.id, task.name), chat)
        self.create_issue(task.name, 'Task ID: [{}]\n\ Task Name: {}'.format(task.id, task.name))

    def rename_task(self, msg, chat):
        new_name = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                new_name = msg.split(' ', 1)[1]
            msg = msg.split(' ', 1)[0]

        if self.is_msg_digit(msg, chat):
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                return

            if new_name == '':
                self.send_message("You want to modify task {},\
                            but you didn't provide any new text".
                            format(task_id), chat)
                return

            old_name = task.name
            task.name = new_name
            db.session.commit()
            self.send_message("Task {} redefined from {} to {}".
                        format(task_id, old_name, new_name), chat)

    def list_tasks(self, msg, chat):
        response = ''
        response += Emojis.EMOJI_TASK + 'Task List\n'
        query = db.session.query(Task).filter_by(parents='',
                                                chat=chat).order_by(Task.id)

        for task in query.all():
            if task.status == 'DOING':
                icon = Emojis.EMOJI_DOING
            elif task.status == 'DONE':
                icon = Emojis.EMOJI_DONE
            elif task.status == 'TODO':
                icon = Emojis.EMOJI_TODO

            response += '[[{}]] {} {} {} *DEADLINE:* {}\n'.format(task.id, icon, task.name, task.priority, task.duedate)
            response += self.deps_text(task, chat)

        self.send_message(response, chat)
        response = ''

        response += Emojis.EMOJI_STATUS + ' _Status_\n'

        query = db.session.query(Task).filter_by(status='TODO',
                                                chat=chat).order_by(Task.id)
        response += '\n' + Emojis.EMOJI_TODO + ' *TODO*\n'
        for task in query.all():
            response += '[[{}]] {} {} *DEADLINE:*{}\n'.format(task.id, task.name, task.priority, task.duedate)
        query = db.session.query(Task).filter_by(status='DOING',
                                                chat=chat).order_by(Task.id)

        response += '\n' + Emojis.EMOJI_DOING + ' *DOING*\n'
        for task in query.all():
            response += '[[{}]] {} {} *DEADLINE:*{}\n'.format(task.id, task.name, task.priority, task.duedate)
        query = db.session.query(Task).filter_by(status='DONE',
                                                chat=chat).order_by(Task.id)

        response += '\n' + Emojis.EMOJI_DONE + ' *DONE*\n'
        for task in query.all():
            response += '[[{}]] {} {}\n'.format(task.id, task.name, task.priority)

        self.send_message(response, chat)

    def duplicate_task(self, msg, chat):
        if self.is_msg_digit(msg, chat):
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x".format(task_id), chat)
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
            self.send_message("New task *TODO* [[{}]] {}".
                        format(new_task.id, new_task.name), chat)

    def get_id_list(self, msg):
        id_list = msg.split(' ')
        return id_list

    def update_status(self, msg, status, chat):
        ids = self.get_id_list(msg)
        print(ids)
        for id in ids:
            if(self.is_msg_digit(id, chat)):
                task_id = int(id)
                query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                try:
                    task = query.one()
                except sqlalchemy.orm.exc.NoResultFound:
                    self.send_message("_404_ Task {} not found x.x".format(task_id),
                                chat)
                    return
                task.status = status
                db.session.commit()
                self.send_message("*" + status + "* task [[{}]] {} {}".format(
                            task.id, task.name, task.priority), chat)

    def delete_task(self, msg, chat):
        if self.is_msg_digit(msg, chat):
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x".format(task_id), chat)
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
            self.send_message("Task [[{}]] deleted".format(task_id), chat)

    def add_dependency(self, msg, chat):
        text = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                text = msg.split(' ', 1)[1]
            msg = msg.split(' ', 1)[0]

        if self.is_msg_digit(msg, chat):
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                return

            if text == '':
                for i in task.dependencies.split(',')[:-1]:
                    i = int(i)
                    q = db.session.query(Task).filter_by(id=i, chat=chat)
                    t = q.one()
                    t.parents = t.parents.replace('{},'.format(task.id), '')

                task.dependencies = ''
                self.send_message("Dependencies removed from task {}"
                            .format(task_id), chat)
            else:
                for depid in text.split(' '):
                    if not depid.isdigit():
                        self.send_message("All dependencies ids must be numeric,\
                                    and not {}".format(depid), chat)
                    else:
                        depid = int(depid)
                        query = db.session.query(Task).filter_by(id=depid,
                                                                chat=chat)
                        try:
                            taskdep = query.one()
                            taskdep.parents += str(task.id) + ','
                        except sqlalchemy.orm.exc.NoResultFound:
                            self.send_message("_404_ Task {} not found x.x"
                                        .format(depid), chat)
                            continue

                        deplist = task.dependencies.split(',')
                        if str(depid) not in deplist:
                            task.dependencies += str(depid) + ','

            db.session.commit()
            self.send_message("Task {} dependencies up to date".format(task_id), chat)

    def change_priority(self, msg, chat):
        priority = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                priority = msg.split(' ', 1)[1]
            msg = msg.split(' ', 1)[0]

        if self.is_msg_digit(msg, chat):
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                return

            if priority == '':
                task.priority = ''
                self.send_message("_Cleared_ all priorities from task {}"
                            .format(task_id), chat)
            else:
                if priority.lower() not in ['high', 'medium', 'low']:
                    self.send_message("The priority *must be* one of the following:\
                                high, medium, low", chat)
                else:
                    if priority.lower() == 'low':
                        task.priority = Emojis.EMOJI_LOW
                    elif priority.lower() == 'medium':
                        task.priority = Emojis.EMOJI_MEDIUM
                    elif priority.lower() == 'high':
                        task.priority = Emojis.EMOJI_HIGH

                    self.send_message("*Task {}* priority has priority *{}*"
                                .format(task_id, priority.lower()), chat)
            db.session.commit()                        

    def date_format(self, text):
        try:
            datetime.strptime(text, '%m/%d/%Y')
            return True
        except ValueError:
            return False

    def duedate(self, msg, chat):
        text = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                text = msg.split(' ', 1)[1]
                msg = msg.split(' ', 1)[0]

                if not msg.isdigit():
                    self.send_message("You must inform the task id", chat)
                else:
                    task_id = int(msg)
                    query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                    try:
                        task = query.one()
                    except sqlalchemy.orm.exc.NoResultFound:
                        self.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                        return

                    if text == '':
                        self.send_message("You want to give a duedate to task {}, but you didn't provide any date".format(task_id), chat)
                        return
                    else:
                        if not self.date_format(text):
                            self.send_message("The duedate needs to be on US Format: mm/dd/YYYY", chat)
                        else:
                            task.duedate = datetime.strptime(text, '%m/%d/%Y')
                            self.send_message("Task {} deadline is on: {}".format(task_id, text), chat)
                    db.session.commit()

    def handle_updates(self, updates):
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
                self.new_task(msg, chat)

            elif command == '/rename':
                self.rename_task(msg, chat)

            elif command == '/duplicate':
                self.duplicate_task(msg, chat)

            elif command == '/delete':
                self.delete_task(msg, chat)

            elif command == '/todo':
                self.update_status(msg, "TODO", chat)

            elif command == '/doing':
                self.update_status(msg, "DOING", chat)

            elif command == '/done':
                self.update_status(msg, "DONE", chat)

            elif command == '/list':
                self.list_tasks(msg, chat)

            elif command == '/dependson':
                self.add_dependency(msg, chat)

            elif command == '/priority':
                self.change_priority(msg, chat)

            elif command == '/start':
                self.send_message("Welcome! Here is a list"
                                      " of things you can do.", chat)
                self.send_message(self.HELP, chat)

            elif command == '/help':
                self.send_message("Here is a list " 
                                      "of things you can do.", chat)
                self.send_message(self.HELP, chat)
            elif command == '/duedate':
                self.duedate(msg, chat)

            else:
                self.send_message("I'm sorry dave. I'm afraid I can't do that.", chat)