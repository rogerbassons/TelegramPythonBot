from telegram.ext import Updater, CommandHandler, PicklePersistence
import subprocess
import urllib.request
import json
from io import BytesIO

authorizedUsers = ["rogerbassons"]

def runOSCommand(cmd):
    return subprocess.check_output(cmd).decode()

def checkOutput(cmd, update, allowedUsers):
    out = ""
    try:
        message = update.message

        username = str(message.from_user.username)
        
        if len(allowedUsers) == 0 or username in allowedUsers:
            out = runOSCommand(cmd)
        else:
            print("Not authorized: " + username)

    except Exception as e:
       out = str(e)

    if out != "":
        message.reply_text(out)


def apiGet(url):
    return urllib.request.urlopen(url)

def error_callback(update, context):
    print(str(context.error))

def hello(update, context):
    update.message.reply_text(
        'Hello {}'.format(update.message.from_user.first_name))

def listTorrents(update, context):
    cmd = ["/usr/bin/transmission-remote", "-l"]
    checkOutput(cmd, update, authorizedUsers)

def startTransmission(update, context):
    cmd = ["/usr/bin/transmission-daemon"]
    checkOutput(cmd, update, authorizedUsers)

def stopTransmission(update, context):
    cmd = ["/usr/bin/transmission-remote", "--exit"]
    checkOutput(cmd, update, authorizedUsers)

def limitTransmission(update, context):
    cmd = ["/usr/bin/transmission-remote", "-as"]
    checkOutput(cmd, update, authorizedUsers)

def unlimitTransmission(update, context):
    cmd = ["/usr/bin/transmission-remote", "-AS"]
    checkOutput(cmd, update, authorizedUsers)

def sendLatestXkcd(xkcd, chat_id, bot, chat_data):
    img = apiGet(xkcd["img"])

    bot.send_message(chat_id=chat_id, text=xkcd["title"])
    bot.sendPhoto(chat_id, photo=img, caption=xkcd["alt"])
    chat_data["xkcdId"] = xkcd["num"]


def postLatestXkcd(update, context):
    try:
        chat_id = update.message.chat_id

        xkcd = json.load(apiGet("https://xkcd.com/info.0.json"))

        sendLatestXkcd(xkcd, chat_id, context.bot, context.chat_data)
    except Exception as e:
        print(str(e))

def xkcd_subscription(context, chat_data):
    try:
        job = context.job
        chat_id = job.context

        xkcd = json.load(apiGet("https://xkcd.com/info.0.json"))

        latestSentId = chat_data.get("xkcdId")

        if latestSentId == None or latestSentId != xkcd["num"]:
            sendLatestXkcd(xkcd, chat_id, context.bot, chat_data)
    except Exception as e:
        print(str(e))


def _subscribeXkcd(job_queue, chat_data, chat_id):
    minutes = 30
    job_queue.run_repeating(lambda x: xkcd_subscription(x, chat_data), 30 * 60, 0, context=chat_id, name="subXkcd")


def subscribeXkcd(update, context):
    try:
        if not context.chat_data.get("xkcdId"):
            _subscribeXkcd(context.job_queue, context.chat_data, update.message.chat_id)

            update.message.reply_text("Subscribed")
    except Exception as e:
        print(str(e))

def unsubscribeXkcd(update, context):
    try:
        jobs = context.job_queue.jobs()

        j = next((x for x in jobs if x.context == update.message.chat_id), None)
        if (j != None):
            j.schedule_removal()
            id = context.chat_data.pop("xkcdId")
            update.message.reply_text("Unsubscribed")


    except Exception as e:
        print(str(e))


handlers = [
        { "name": "hello", "fn": hello },
        { "name": "torrents", "fn": listTorrents },
        { "name": "start", "fn": startTransmission },
        { "name": "stop", "fn": stopTransmission },
        { "name": "limit", "fn": limitTransmission },
        { "name": "wrap", "fn": unlimitTransmission },
        { "name": "xkcd", "fn": postLatestXkcd },
        { "name": "subxkcd", "fn": subscribeXkcd },
        { "name": "unsubxkcd", "fn": unsubscribeXkcd }
        ]

token = ""
with open("telegram.token") as f:
    token = str(f.read().strip())

persistence = PicklePersistence(filename="bot_persistence")
updater = Updater(token, use_context=True, persistence=persistence)

for handler in handlers:
    updater.dispatcher.add_handler(CommandHandler(handler["name"], handler["fn"]))

updater.dispatcher.add_error_handler(error_callback)

chatsData = persistence.get_chat_data()
for chatId in chatsData:
    if chatsData.get(chatId).get("xkcdId") != None:
        _subscribeXkcd(updater.job_queue, chatsData.get(chatId), chatId)

updater.start_polling()
updater.idle()


