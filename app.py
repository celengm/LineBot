# -*- coding: utf-8 -*-

import errno
import os
import sys
import tempfile
import traceback
import hashlib 
import datetime

# Database import
from db import kw_dict_mgr, group_ban, kwdict_col, gb_col

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler, exceptions
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, URITemplateAction, PostbackTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent
)

# Main initializing
app = Flask(__name__)
administrator = os.getenv('ADMIN', None)
group_admin = os.getenv('G_ADMIN', None)
group_mod = os.getenv('G_MOD', None)
if administrator is None:
    print('The SHA224 of ADMIN not defined. Program will be terminated.')
    sys.exit(1)
if group_admin is None:
    print('The SHA224 of G_ADMIN not defined. Program will be terminated.')
    sys.exit(1)
if group_mod is None:
    print('The SHA224 of G_MOD not defined. Program will be terminated.')
    sys.exit(1)
boot_up = datetime.datetime.now()
rec = {'JC_called': 0}
cmd_called_time = {'S': 0, 'A': 0, 'M': 0, 'D': 0, 'R': 0, 'Q': 0, 'C': 0, 'I': 0, 'K': 0, 'P': 0, 'G': 0, 'H': 2, 'SHA': 0}

# Database initializing
kwd = kw_dict_mgr("postgres", os.environ["DATABASE_URL"])
gb = group_ban("postgres", os.environ["DATABASE_URL"])

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)
api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# File path
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')


# function for create tmp dir for download content
def make_static_tmp_dir():
    try:
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except exceptions.InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    rep = event.reply_token
    text = event.message.text
    splitter = '  '

    if len(text.split(splitter)) > 1 and text.startswith('JC'):
        try:
            head, oth = split(text, splitter, 2)
            split_count = {'S': 4, 'A': 4, 'M': 5, 'D': 3, 'R': 5, 'Q': 3, 'C': 2, 'I': 3, 'K': 3, 'P': 2, 'G': 2, 'H': 2, 'SHA': 3}

            if head == 'JC':
                rec['JC_called'] += 1

                try:
                    params = split(oth, splitter, split_count[oth[0]] - 1)
                    cmd, param1, param2, param3 = [params.pop(0) if len(params) > 0 else None for i in range(4)]
                except ValueError:
                    text = u'Lack of parameter(s). Please recheck your parameter(s) that correspond to the command.'
                    api.reply_message(rep, TextSendMessage(text=text))
                    return

                cmd_called_time[cmd] += 1
                
                # SQL Command
                if cmd == 'S':
                    if isinstance(event.source, SourceUser) and hashlib.sha224(param2).hexdigest() == administrator:
                        results = kwd.sql_cmd(param1)
                        if results is not None:
                            text = u'SQL command result({len}): \n'.format(len=len(results))
                            for result in results:
                                text += u'{result}\n'.format(result=result)
                                
                    else:
                        text = 'This is a restricted function.'

                    api.reply_message(rep, TextSendMessage(text=text))
                # ADD keyword
                elif cmd == 'A':
                    text = 'Unavailable to add keyword pair in GROUP or ROOM. Please go to 1v1 CHAT to execute this command.'

                    if isinstance(event.source, SourceUser):
                        uid = event.source.user_id
                        results = kwd.insert_keyword(param1, param2, uid)
                        text = u'Pair Added. Total: {len}\n'.format(len=len(results))
                        for result in results:
                            text += u'ID: {id}\n'.format(id=result[kwdict_col.id])
                            text += u'Keyword: {kw}\n'.format(kw=result[kwdict_col.keyword].decode('utf8'))
                            text += u'Reply: {rep}\n'.format(rep=result[kwdict_col.reply].decode('utf8'))

                    api.reply_message(rep, TextSendMessage(text=text))
                # ADD keyword(sys)
                elif cmd == 'M':
                    text = 'Restricted Function.'

                    if isinstance(event.source, SourceUser) and hashlib.sha224(param3).hexdigest() == administrator:
                        uid = event.source.user_id
                        results = kwd.insert_keyword_sys(param1, param2, uid)
                        text = u'System Pair Added. Total: {len}\n'.format(len=len(results))
                        for result in results:
                            text += u'ID: {id}\n'.format(id=result[kwdict_col.id])
                            text += u'Keyword: {kw}\n'.format(kw=result[kwdict_col.keyword].decode('utf8'))
                            text += u'Reply: {rep}\n'.format(rep=result[kwdict_col.reply].decode('utf8'))

                    api.reply_message(rep, TextSendMessage(text=text))
                # DELETE keyword
                elif cmd == 'D':
                    text = u'Specified keyword({kw}) to delete not exists.'.format(kw=param1)
                    results = kwd.delete_keyword(param1)

                    if results is not None:
                        for result in results:
                            text = 'Pair below DELETED.\n'
                            text += u'ID: {id}\n'.format(id=result[kwdict_col.id])
                            text += u'Keyword: {kw}\n'.format(kw=result[kwdict_col.keyword].decode('utf8'))
                            text += u'Reply: {rep}\n\n'.format(rep=result[kwdict_col.reply].decode('utf8'))
                            profile = api.get_profile(result[kwdict_col.creator])
                            text += u'This pair is created by {name}.\n'.format(name=profile.display_name)

                    api.reply_message(rep, TextSendMessage(text=text))
                # DELETE keyword(sys)
                elif cmd == 'R':
                    text = 'Restricted Function.'

                    if isinstance(event.source, SourceUser) and hashlib.sha224(param3).hexdigest() == administrator:
                        text = u'Specified keyword({kw}) to delete not exists.'.format(kw=param1)
                        results = kwd.delete_keyword_sys(param1)

                        if results is not None:
                            for result in results:
                                text = 'System Pair below DELETED.\n'
                                text += u'ID: {id}\n'.format(id=result[kwdict_col.id])
                                text += u'Keyword: {kw}\n'.format(kw=result[kwdict_col.keyword].decode('utf8'))
                                text += u'Reply: {rep}\n'.format(rep=result[kwdict_col.reply].decode('utf8'))

                    api.reply_message(rep, TextSendMessage(text=text))
                # QUERY keyword
                elif cmd == 'Q':
                    text = u'Specified keyword({kw}) to query returned no result.'.format(kw=param1)
                    if len(param1.split(splitter)) > 1:
                        paramQ = split(param1, splitter, 2)
                        param1, param2 = [paramQ.pop(0) if len(paramQ) > 0 else None for i in range(2)]
                        if int(param2) - int(param1) < 15:
                            results = kwd.search_keyword_index(param1, param2)
                        else:
                            results = None
                            text = 'Maximum selecting range by ID is 15.'
                    else:
                        results = kwd.search_keyword(param1)
                        

                    if results is not None:
                        text = u'Keyword found. Total: {len}. Listed below.\n'.format(len=len(results))
                        
                        for result in results:
                            text += u'ID: {id} - {kw} {od}{delete}{adm}\n'.format(
                                kw=result[kwdict_col.keyword].decode('utf8'),
                                od='(OVR)' if bool(result[kwdict_col.override]) == True else '',
                                delete='(DEL)' if bool(result[kwdict_col.deleted]) == True else '',
                                adm='(TOP)' if bool(result[kwdict_col.admin]) == True else '',
                                id=result[kwdict_col.id])

                    api.reply_message(rep, TextSendMessage(text=text))
                # CREATE kw_dict
                elif cmd == 'C':
                    api.reply_message(rep, TextSendMessage(
                        text='Successfully Created.' if kwd.create_kwdict() == True else 'Creating failure.'))
                # INFO of keyword
                elif cmd == 'I':
                    text = u'Specified keyword({kw}) to get information returned no result.'.format(kw=param1)
                    if len(param1.split(splitter)) > 1:
                        paramQ = split(param1, splitter, 2)
                        param1, param2 = [paramQ.pop(0) if len(paramQ) > 0 else None for i in range(2)]
                        results = kwd.get_info_id(param1)   
                    else:
                        results = kwd.get_info(param1)

                    if results is None:
                        text = u'Specified keyword: {kw} not exists.'.format(kw=param1)
                        api.reply_message(rep, TextSendMessage(text=text))
                    else:
                        text = ''
                        for result in results:
                            text += u'ID: {id}\n'.format(id=result[kwdict_col.id])
                            text += u'Keyword: {kw}\n'.format(kw=result[kwdict_col.keyword].decode('utf8'))
                            text += u'Reply: {rep}\n'.format(rep=result[kwdict_col.reply].decode('utf8'))
                            text += u'Override: {od}\n'.format(od=result[kwdict_col.override])
                            text += u'Admin Pair: {ap}\n'.format(ap=result[kwdict_col.admin])
                            text += u'Has been called {ut} time(s).\n'.format(ut=result[kwdict_col.used_time])
                            profile = api.get_profile(result[kwdict_col.creator])
                            text += u'Created by {name}.\n'.format(name=profile.display_name)
                        api.reply_message(rep, TextSendMessage(text=text))
                # RANKING
                elif cmd == 'K':
                    try:
                        results = kwd.order_by_usedtime(int(param1))
                        text = u'KEYWORD CALLING RANKING (Top {rk})\n\n'.format(rk=param1)
                        rank = 0

                        for result in results:
                            rank += 1
                            text += u'No.{rk} - {kw} (ID: {id}, {ct} times.)\n'.format(rk=rank, 
                                                                      kw=result[kwdict_col.keyword].decode('utf8'), 
                                                                      id=result[kwdict_col.id],
                                                                      ct=result[kwdict_col.used_time])
                    except ValueError as err:
                        text = u'Invalid parameter. The 1st parameter of \'K\' function can be number only.\n\n'
                        text += u'Error message: {msg}'.format(msg=err.message)
                    
                    api.reply_message(rep, TextSendMessage(text=text))
                # SPECIAL record
                elif cmd == 'P':
                    text = u'Boot up Time: {bt} (UTC)\n'.format(bt=boot_up)
                    text += u'Count of Keyword Pair: {ct}\n'.format(ct=kwd.row_count())
                    text += u'Count of Reply: {crep}\n'.format(crep=kwd.used_time_sum())
                    user_list_top = kwd.user_sort_by_created_pair()[0]
                    text += u'Most Creative User:\n{name} ({num} Pairs)\n'.format(name=api.get_profile(user_list_top[0]).display_name,
                                                                               num=user_list_top[1])
                    all = kwd.order_by_usedtime_all()
                    first = all[0]
                    text += u'Most Popular Keyword:\n{kw} (ID: {id}, {c} Time(s))\n'.format(kw=first[kwdict_col.keyword].decode('utf-8'), 
                                                                                c=first[kwdict_col.used_time],
                                                                                id=first[kwdict_col.id])
                    last = all[-1]
                    text += u'Most Unpopular Keyword:\n{kw} (ID: {id}, {c} Time(s))\n\n'.format(kw=last[kwdict_col.keyword].decode('utf-8'), 
                                                                                c=last[kwdict_col.used_time],
                                                                                id=last[kwdict_col.id])
                    text += u'System command called time (including failed): {t}\n'.format(t= rec['JC_called'])
                    for cmd, time in cmd_called_time.iteritems():
                        text += u'Command \'{c}\' Called {t} Time(s).\n'.format(c=cmd, t=time)

                    api.reply_message(rep, TextSendMessage(text=text))
                # GORUP ban
                elif cmd == 'G':
                    if param1 is None and isinstance(event.source, SourceGroup):
                        # is_silence
                        group_detail = gb.is_silence(event.source.group_id)
                        if group_detail is not None:
                            text = u'Group ID: {id}\n'.format(id=group_detail[gb_col.groupId])
                            text += u'Silence: {sl}\n'.format(sl=group_detail[gb_col.silence])
                            text += u'Admin: {name}\n'.format(name=api.get_profile(group_detail[gb_col.admin]))
                        else:
                            text = u'Group ID: {id}\n'.format(id=event.source.group_id)
                            text += u'Silence: False'
                    else:
                        text = 'Temporarily Unavailable for \'G\' Function.'
                        return


                    # =============== UNDONE ===============


                        insuff_p = 'Insufficient permission to use this function.'
                        illegal_type = 'This function can be used in 1v1 CHAT only. Permission key required. Please contact admin.'
                        uid = event.source.user_id

                        if hashlib.sha224(param1).hexdigest() == administrator:
                            perm = 3
                        elif hashlib.sha224(param1).hexdigest() == group_admin:
                            perm = 2
                        elif hashlib.sha224(param1).hexdigest() == group_mod:
                            perm = 1
                        else:
                            perm = 0

                        if perm < 1:
                            text = insuff_p
                        elif isinstance(event.source, SourceUser):

                            if perm >= 3 and param2 == 'C':
                                text = 'Group ban table created successfully.' if gb.create_ban() else 'Group ban table created failed.'

                        else:
                            text = illegal_type

                    api.reply_message(rep, TextSendMessage(text=text))
                # get CHAT id
                elif cmd == 'H':
                    if isinstance(event.source, SourceUser):
                        text = event.source.user_id
                        type = 'Type: User'
                    elif isinstance(event.source, SourceGroup):
                        text = event.source.group_id
                        type = 'Type: Group'
                    elif isinstance(event.source, SourceRoom):
                        text = event.source.room_id
                        type = 'Type: Room'
                    else:
                        text = 'Unknown chatting type.'

                    api.reply_message(rep, [TextSendMessage(text=type), TextSendMessage(text=text)])
                # SHA224 generator
                elif cmd == 'SHA':
                    api.reply_message(rep, TextSendMessage(text=hashlib.sha224(param1).hexdigest()))
                else:
                    cmd_called_time[cmd] -= 1
        except KeyError as ex:
            text = u'Invalid Command: {cmd}. Please recheck the user manual.'.format(cmd=ex.message)
            api.reply_message(rep, TextSendMessage(text=text))
        except exceptions.LineBotApiError as ex:
            text = u'Line Bot Api Error. Status code: {sc}\n\n'.format(sc=ex.status_code)
            for err in ex.error.details:
                text += u'Property: {prop}\nMessage: {msg}'.format(prop=err.property, msg=err.message)
            api.reply_message(rep, TextSendMessage(text=text))
        except Exception as exc:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            text = u'Type: {type}\nMessage: {msg}\nLine {lineno}'.format(type=exc_type, lineno=exc_tb.tb_lineno, msg=exc.message)
            api.reply_message(rep, TextSendMessage(text=text))
    else:
        res = kwd.get_reply(text)
        if res is not None:
            result = res[0]
            api.reply_message(rep, TextSendMessage(text=result[kwdict_col.reply].decode('utf8')))

    return

    # MD5 generator
    # calculator

    if text == 'profile':
        if isinstance(event.source, SourceUser):
            profile = api.get_profile(event.source.user_id)
            api.reply_message(
                event.reply_token, [
                    TextSendMessage(text='Display name: ' + profile.display_name),
                    TextSendMessage(text='Status message: ' + profile.status_message),
                ]
            )
        else:
            api.reply_message(
                event.reply_token,
                TextMessage(text="Bot can't use profile API without user ID"))
    elif text == 'bye':
        if isinstance(event.source, SourceGroup):
            api.reply_message(
                event.reply_token, TextMessage(text='Leaving group'))
            api.leave_group(event.source.group_id)
        elif isinstance(event.source, SourceRoom):
            api.reply_message(
                event.reply_token, TextMessage(text='Leaving room'))
            api.leave_room(event.source.room_id)
        else:
            api.reply_message(
                event.reply_token,
                TextMessage(text="Bot can't leave from 1:1 chat"))
    elif text == 'confirm':
        confirm_template = ConfirmTemplate(text='Do it?', actions=[
            MessageTemplateAction(label='Yes', text='Yes!'),
            MessageTemplateAction(label='No', text='No!'),
        ])
        template_message = TemplateSendMessage(
            alt_text='Confirm alt text', template=confirm_template)
        api.reply_message(event.reply_token, template_message)
    elif text == 'buttons':
        buttons_template = ButtonsTemplate(
            title='My buttons sample', text='Hello, my buttons', actions=[
                URITemplateAction(
                    label='Go to line.me', uri='https://line.me'),
                PostbackTemplateAction(label='ping', data='ping'),
                PostbackTemplateAction(
                    label='ping with text', data='ping',
                    text='ping'),
                MessageTemplateAction(label='Translate Rice', text='米')
            ])
        template_message = TemplateSendMessage(
            alt_text='Buttons alt text', template=buttons_template)
        api.reply_message(event.reply_token, template_message)
    elif text == 'carousel':
        carousel_template = CarouselTemplate(columns=[
            CarouselColumn(text='hoge1', title='fuga1', actions=[
                URITemplateAction(
                    label='Go to line.me', uri='https://line.me'),
                PostbackTemplateAction(label='ping', data='ping')
            ]),
            CarouselColumn(text='hoge2', title='fuga2', actions=[
                PostbackTemplateAction(
                    label='ping with text', data='ping',
                    text='ping'),
                MessageTemplateAction(label='Translate Rice', text='米')
            ]),
        ])
        template_message = TemplateSendMessage(
            alt_text='Buttons alt text', template=carousel_template)
        api.reply_message(event.reply_token, template_message)
    elif text == 'imagemap':
        pass
    else:
        api.reply_message(
            event.reply_token, TextSendMessage(text=event.message.text))


@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    return

    api.reply_message(
        event.reply_token,
        LocationSendMessage(
            title=event.message.title, address=event.message.address,
            latitude=event.message.latitude, longitude=event.message.longitude
        )
    )


@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    package_id = event.message.package_id
    sticker_id = event.message.sticker_id

    return
    api.reply_message(
        event.reply_token,
        StickerSendMessage(package_id=2, sticker_id=144)
    )


# Other Message Type
@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
    return

    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
    elif isinstance(event.message, VideoMessage):
        ext = 'mp4'
    elif isinstance(event.message, AudioMessage):
        ext = 'm4a'
    else:
        return

    message_content = api.get_message_content(event.message.id)
    with tempfile.NamedTemporaryFile(dir=static_tmp_path, prefix=ext + '-', delete=False) as tf:
        for chunk in message_content.iter_content():
            tf.write(chunk)
        tempfile_path = tf.name

    dist_path = tempfile_path + '.' + ext
    dist_name = os.path.basename(dist_path)
    os.rename(tempfile_path, dist_path)

    api.reply_message(
        event.reply_token, [
            TextSendMessage(text='Save content.'),
            TextSendMessage(text=request.host_url + os.path.join('static', 'tmp', dist_name))
        ])


@handler.add(FollowEvent)
def handle_follow(event):
    return

    api.reply_message(
        event.reply_token, TextSendMessage(text='Got follow event'))


@handler.add(UnfollowEvent)
def handle_unfollow():
    return

    app.logger.info("Got Unfollow event")


@handler.add(JoinEvent)
def handle_join(event):
    gb.new_data(event.source.groupId, 'Ud5a2b5bb5eca86342d3ed75d1d606e2c', 'RaenonX', 'RaenonX')
    api.reply_message(
        event.reply_token,
        TextSendMessage(text='Welcome to use the shadow of JELLYFISH!\n\n' + 
                             '======================================\n' +
                             'USAGE: type in \'使用說明-JC\'' +
                             '======================================\n' +
                             'To contact the developer, use the URL below http://line.me/ti/p/~chris80124 \n\n' + 
                             'HAVE A FUNNY EXPERIENCE USING THIS BOT!'))


@handler.add(LeaveEvent)
def handle_leave():
    return
    app.logger.info("Got leave event")


@handler.add(PostbackEvent)
def handle_postback(event):
    return
    if event.postback.data == 'ping':
        api.reply_message(
            event.reply_token, TextSendMessage(text='pong'))


@handler.add(BeaconEvent)
def handle_beacon(event):
    return
    api.reply_message(
        event.reply_token,
        TextSendMessage(text='Got beacon event. hwid=' + event.beacon.hwid))


def split(text, splitter, size):
    list = []
    for i in range(size - 1):
        list.append(text[0:text.index(splitter)])
        text = text[text.index(splitter)+len(splitter):]
  
    list.append(text)
    return list


if __name__ == "__main__":
    # create tmp dir for download content
    make_static_tmp_dir()

    app.run(port=os.environ['PORT'], host='0.0.0.0')
