from handletask import HandleTask
import time


def main():
    last_update_id = None
    mytask = HandleTask()
    while True:

        print("Updates")
        updates = mytask.get_updates(last_update_id)

        if len(updates["result"]) > 0:
            last_update_id = mytask.get_last_update_id(updates) + 1
            mytask.handle_updates(updates)

        time.sleep(0.5)


if __name__ == '__main__':
    main()
