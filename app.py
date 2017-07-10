# -*- coding: utf-8 -*-

import errno, os, sys, tempfile
import traceback
import validators
import time
from collections import defaultdict
from urlparse import urlparse
from cgi import escape
from datetime import datetime, timedelta
from error import error
from flask import Flask, request, abort, url_for

# import for 'SHA'
import hashlib 

# import for Oxford Dictionary
import httplib
import requests
import json

# Database import
from db import kw_dict_mgr, group_ban, kwdict_col, gb_col

# tool import
from tool import mff

# import from LINE MAPI
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
boot_up = datetime.now() + timedelta(hours=8)

class msg_counter(object):
    def __init__(self):
        self._rcv = 0
        self._rep = 0

    @property
    def recv(self):
        return self._rcv

    @property
    def repl(self):
        return self._rep

    def received(self):
        self._rcv += 1

    def replied(self):
        self._rep += 1

    def __repr__(self):
        return u'收到: {}, 回覆: {}'.format(self._rcv, self._rep)

rec = {'JC_called': 0, 'MFF_called': 0, 
       'Msg': defaultdict(msg_counter), 
       'Silence': False, 'Intercept': True, 
       'webpage': 0}
report_content = {'Error': {}, 
                  'FullQuery': {}, 
                  'FullInfo': {},
                  'Text': {}}

class command(object):
    def __init__(self, min_split=2, max_split=2, non_user_permission_required=False):
        self._split_max = max_split
        self._split_min = min_split
        self._count = 0
        self._non_user_permission_required = non_user_permission_required

    @property
    def split_max(self):
        """Maximum split count."""
        return self._split_max + (1 if self._non_user_permission_required else 0) 

    @property
    def split_min(self):
        """Minimum split count."""
        return self._split_min

    @property
    def count(self):
        """Called count."""
        return self._count

    @count.setter
    def count(self, value):
        """Called count."""
        self._count = value 

    @property
    def non_user_permission_required(self):
        """Required Permission"""
        return self._non_user_permission_required

cmd_dict = {'S': command(1, 1, True), 
            'A': command(2, 4, False), 
            'M': command(2, 4, True), 
            'D': command(1, 2, False), 
            'R': command(1, 2, True), 
            'Q': command(1, 2, False), 
            'C': command(0, 0, True), 
            'I': command(1, 2, False), 
            'K': command(2, 2, False), 
            'P': command(0, 0, False), 
            'G': command(0, 0, False), 
            'GA': command(1, 5, True), 
            'H': command(0, 1, False), 
            'SHA': command(1, 1, False), 
            'O': command(1, 1, False), 
            'B': command(0, 0, False), 
            'U': command(0, 1, False)}

# Line Bot Environment initializing
MAIN_UID_OLD = 'Ud5a2b5bb5eca86342d3ed75d1d606e2c'
MAIN_UID = 'U089d534654e2c5774624e8d8c813000e'
main_silent = False
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

# Database initializing
kwd = kw_dict_mgr("postgres", os.environ["DATABASE_URL"])
gb = group_ban("postgres", os.environ["DATABASE_URL"])

# Oxford Dictionary Environment initializing
oxford_id = os.getenv('OXFORD_ID', None)
oxford_key = os.getenv('OXFORD_KEY', None)
oxford_disabled = False
if oxford_id is None:
    oxford_disabled = True
if oxford_key is None:
    oxford_disabled = True
language = 'en'
oxdict_url = 'https://od-api.oxforddictionaries.com:443/api/v1/entries/' + language + '/'


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



@app.route("/error", methods=['GET'])
def get_error_list():
    rec['webpage'] += 1
    content = 'Boot up at {time}\n\nError list: '.format(time=boot_up)
    error_timestamps = report_content['Error'].keys()

    for timestamp in error_timestamps:
        content += html_hyperlink(timestamp, request.url_root + url_for('get_error_message', timestamp=timestamp)[1:])
        content += '\n'
        
    return content.replace('\n', '<br/>')

@app.route("/error/<timestamp>", methods=['GET'])
def get_error_message(timestamp):
    rec['webpage'] += 1
    error_message = report_content['Error'].get(timestamp)

    if error_message is None:
        content = error.webpage.no_content_at_time('error', float(timestamp))
    else:
        content = error_message
        
    return html_paragraph(content)

@app.route("/query/<timestamp>", methods=['GET'])
def full_query(timestamp):
    rec['webpage'] += 1
    query = report_content['FullQuery'].get(timestamp)
    
    if query is None:
        content = error.webpage.no_content_at_time('query', float(timestamp))
    else:
        content = query
        
    return html_paragraph(content)

@app.route("/info/<timestamp>", methods=['GET'])
def full_info(timestamp):
    rec['webpage'] += 1
    info = report_content['FullInfo'].get(timestamp)
    
    if info is None:
        content = error.webpage.no_content_at_time('info query', float(timestamp))
    else:
        content = info
        
    return html_paragraph(content)

@app.route("/full/<timestamp>", methods=['GET'])
def full_content(timestamp):
    rec['webpage'] += 1
    content_text = report_content['Text'].get(timestamp)
    
    if content_text is None:
        content = error.webpage.no_content_at_time('full text', float(timestamp))
    else:
        content = content_text
        
    return html_paragraph(content)

@app.route("/ranking/<type>", methods=['GET'])
def full_ranking(type):
    rec['webpage'] += 1
    if type == 'user':
        content = kw_dict_mgr.list_user_created_ranking(api, kwd.user_created_rank())
    elif type == 'used':
        content = kw_dict_mgr.list_keyword_ranking(kwd.order_by_usedrank())
    else:
        content = error.webpage.no_content()
        
    return html_paragraph(content)

def html_paragraph(content):
    return '<p>' + escape(content).replace(' ', '&nbsp;').replace('\n', '<br/>') + '</p>'

def html_hyperlink(content, link):
    return '<a href=\"{link}\">{content}</a>'.format(link=link, content=content)

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    token = event.reply_token
    text = event.message.text
    src = event.source
    splitter = '  '
    splitter_mff = '\n'
    
    rec['Msg'][get_source_channel_id(src)].received()

    if text == administrator:
        rec['Silence'] = not rec['Silence']
        api.reply_message(token, TextSendMessage(text='Bot set to {mute}.'.format(mute='Silent' if rec['Silence'] else 'Active')))
        return
    elif rec['Silence']:
        return

    if text == '561563ed706e6f696abbe050ad79cf334b9262da6f83bc1dcf7328f2':
        rec['Intercept'] = not rec['Intercept']
        api.reply_message(token, TextSendMessage(text='Bot {}.'.format(
            'start to intercept messages.' if rec['Intercept'] else 'stop intercepting messages.')))
        return
    elif rec['Intercept']:
        intercept_text(event)

    try:
        if len(text.split(splitter)) >= 2 and text.startswith('JC'):
            head, cmd, oth = split(text, splitter, 3)

            if head == 'JC':
                rec['JC_called'] += 1

                print text
                if ' ' in text and splitter not in text:
                    print "PRA"
                    text = error.message.insufficient_space_for_command();
                    api_reply(token, TextSendMessage(text=text), src)
                    return

                if cmd not in cmd_dict:
                    text = error.main.invalid_thing(u'指令', cmd)
                    api_reply(token, TextSendMessage(text=text), src)
                    return

                max_prm = cmd_dict[cmd].split_max
                min_prm = cmd_dict[cmd].split_min
                params = split(oth, splitter, max_prm)

                if min_prm > len(params) - params.count(None):
                    text = error.main.lack_of_thing(u'參數')
                    api_reply(token, TextSendMessage(text=text), src)
                    return

                params.insert(0, None)
                cmd_dict[cmd].count += 1
                
                # SQL Command
                if cmd == 'S':
                    key = params.pop(1)
                    sql = params[1]

                    if isinstance(src, SourceUser) and permission_level(key) >= 3:
                        results = kwd.sql_cmd_only(sql)
                        text = u'資料庫指令:\n{}\n\n'.format(sql)
                        if results is not None and len(results) > 0:
                            text += u'輸出結果(共{}筆):'.format(len(results))
                            for result in results:
                                text += u'\n[{}]'.format(', '.join(str(s).decode('utf-8') for s in result))
                        else:
                            text += error.main.no_result()
                    else:
                        text = error.main.restricted(3)

                    api_reply(token, TextSendMessage(text=text), src)
                # ADD keyword & ADD top keyword
                elif cmd == 'A' or cmd == 'M':
                    pinned = cmd_dict[cmd].non_user_permission_required
                    if pinned and permission_level(params.pop(1)) < 1:
                        text = error.main.restricted(1)
                    else:
                        new_uid = get_source_user_id(src)

                        if params[4] is not None:
                            action_kw = params[1]
                            kw = params[2]
                            action_rep = params[3]
                            rep = params[4]
                             
                            if action_kw != 'STK':
                                results = None
                                text = error.main.incorrect_param(u'參數1', u'STK')
                            elif not string_is_int(kw):
                                results = None
                                text = error.main.incorrect_param(u'參數2', u'整數數字')
                            elif action_rep != 'PIC':
                                results = None
                                text =  error.main.incorrect_param(u'參數3', u'PIC')
                            else:
                                if string_is_int(rep):
                                    rep = sticker_png_url(rep)
                                    url_val_result = True
                                else:
                                    url_val_result = url_val_result = True if validators.url(rep) and urlparse(rep).scheme == 'https' else False

                                if type(url_val_result) is bool and url_val_result:
                                    results = kwd.insert_keyword(kw, rep, new_uid, pinned, True, True)
                                else:
                                    results = None
                                    text = error.main.incorrect_param(u'參數4', u'HTTPS協定，並且是合法的網址。')
                        elif params[3] is not None:
                            rep = params[3]

                            if params[2] == 'PIC':
                                kw = params[1]

                                if string_is_int(rep):
                                    rep = sticker_png_url(rep)
                                    url_val_result = True
                                else:
                                    url_val_result = True if validators.url(rep) and urlparse(rep).scheme == 'https' else False

                                if type(url_val_result) is bool and url_val_result:
                                    results = kwd.insert_keyword(kw, rep, new_uid, pinned, False, True)
                                else:
                                    results = None
                                    text = error.main.incorrect_param(u'參數3', u'HTTPS協定，並且是合法的網址。')
                            elif params[1] == 'STK':
                                kw = params[2]

                                if string_is_int(kw):
                                    results = kwd.insert_keyword(kw, rep, new_uid, pinned, True, False)
                                else:
                                    results = None
                                    text = error.main.incorrect_param(u'參數2', u'整數數字')
                            else:
                                text = error.main.unable_to_determine()
                                results = None
                        elif params[2] is not None:
                            kw = params[1]
                            rep = params[2]

                            results = kwd.insert_keyword(kw, rep, new_uid, pinned, False, False)
                        else:
                            results = None
                            text = error.main.lack_of_thing(u'參數')

                        if results is not None:
                            text = u'已新增回覆組。{}\n'.format(u'(置頂)' if pinned else '')
                            for result in results:
                                text += kw_dict_mgr.entry_basic_info(result)

                    api_reply(token, TextSendMessage(text=text), src)
                # DELETE keyword & DELETE top keyword
                elif cmd == 'D' or cmd == 'R':
                    org_text = text

                    pinned = cmd_dict[cmd].non_user_permission_required
                    deletor_uid = src.user_id
                    if pinned and permission_level(paramA.pop(1)) < 2:
                        text = error.main.restricted(2)
                    else:
                        if params[2] is None:
                            kw = params[1]

                            results = kwd.delete_keyword(kw, deletor_uid, pinned)
                        else:
                            action = params[1]

                            if action == 'ID':
                                pair_id = params[2]

                                if string_is_int(pair_id):
                                    results = kwd.delete_keyword_id(pair_id, deletor_uid, pinned)
                                else:
                                    results = None
                                    text = error.main.incorrect_param(u'參數2', u'整數數字')
                            else:
                                results = None
                                text = error.main.incorrect_param(u'參數1', u'ID')

                    if results is not None:
                        for result in results:
                            line_profile = profile(result[kwdict_col.creator])

                            text = u'已刪除回覆組。{}\n'.format(u'(置頂)' if pinned else '')
                            text += kw_dict_mgr.entry_basic_info(result)
                            text += u'\n此回覆組由 {} 製作。'.format(
                                '(LINE account data not found)' if line_profile is None else line_profile.display_name)
                    elif text == org_text:
                        text = error.main.pair_not_exist()

                    api_reply(token, TextSendMessage(text=text), src)
                # QUERY keyword
                elif cmd == 'Q':
                    if params[2] is not None:
                        si = params[1]
                        ei = params[2]

                        try:
                            begin_index = int(si)
                            end_index = int(ei)

                            if end_index - begin_index < 0:
                                results = None
                                text = error.main.incorrect_param(u'參數2', u'大於參數1的數字')
                            else:
                                results = kwd.search_keyword_index(begin_index, end_index)
                        except ValueError:
                            results = None
                            text = error.main.incorrect_param(u'參數1和參數2', u'整數數字')
                    else:
                        kw = params[1]

                        results = kwd.search_keyword(kw)

                    if results is not None:
                        q_list = kw_dict_mgr.list_keyword(results)
                        text = q_list['limited']
                        text += '\n\n完整搜尋結果顯示: {}'.format(rec_query(q_list['full']))
                    else:
                        if params[2] is not None:
                            text = u'找不到和指定的ID範圍({}~{})有關的結果。'.format(si, ei)
                        else:
                            text = u'找不到和指定的關鍵字({})有關的結果。'.format(kw)

                    api_reply(token, TextSendMessage(text=text), src)
                # INFO of keyword
                elif cmd == 'I':
                    if params[2] is not None:
                        action = params[1]

                        if action != 'ID':
                            text = 'Incorrect 1st parameter to query information. To use this function, 1st parameter needs to be \'ID\'.'
                            results = None
                        else:
                            pair_id = params[2]

                            if string_is_int(pair_id):
                                results = kwd.get_info_id(pair_id)   
                            else:
                                results = None
                                text = 'Parameter 2 must be integer to represent pair ID.'
                    else:
                        kw = params[1]

                        results = kwd.get_info(kw)

                    if results is not None:
                        i_object = kw_dict_mgr.list_keyword_info(api, results)
                        text = i_object['limited']
                        text += '\n\nFull Info URL: {url}'.format(url=rec_info(i_object['full']))
                    else:
                        if params[2] is not None:
                            text = 'Specified ID to get INFORMATION (ID: {id}) returned no data.'.format(id=pair_id)
                        else:
                            text = u'Specified keyword to get INFORMATION ({kw}) returned no data.'.format(kw=kw)

                    api_reply(token, TextSendMessage(text=text), src)
                # RANKING
                elif cmd == 'K':
                    ranking_type = params[1]
                    limit = params[2]

                    try:
                        limit = int(limit)
                    except ValueError as err:
                        text = u'Invalid parameter. The 1st parameter of \'K\' function can be number only.\n\n'
                        text += u'Error message: {msg}'.format(msg=err.message)
                    else:
                        Valid = True

                        if ranking_type == 'USER':
                            text = kw_dict_mgr.list_user_created_ranking(api, kwd.user_created_rank(limit))
                        elif ranking_type == 'KW':
                            text = kw_dict_mgr.list_keyword_ranking(kwd.order_by_usedrank(limit))
                        else:
                            text = 'Parameter 1 must be \'USER\'(to look up the ranking of pair created group by user) or \'KW\' (to look up the ranking of pair\'s used time)'
                            Valid = False

                        if Valid:
                            text += '\n\nFull Ranking(user created) URL: {url_u}\nFull Ranking(keyword used) URL: {url_k}'.format(
                                url_u=request.url_root + url_for('full_ranking', type='user')[1:],
                                url_k=request.url_root + url_for('full_ranking', type='used')[1:])
                    
                    api_reply(token, TextSendMessage(text=text), src)
                # SPECIAL record
                elif cmd == 'P':
                    kwpct = kwd.row_count()

                    user_list_top = kwd.user_sort_by_created_pair()[0]
                    line_profile = profile(user_list_top[0])
                    
                    first = kwd.most_used()
                    last = kwd.least_used()
                    last_count = len(last)
                    limit = 10

                    sorted_msg = sorted(rec['Msg'].items(), key=lambda counter: (counter[1].recv + counter[1].repl), reverse=True)

                    text = u'開機後開始統計的資料\n'
                    text += u'開機時間: {} (UTC+8)\n'.format(boot_up)
                    text += u'\n網頁瀏覽次數: {}'.format(rec['webpage'])
                    text += u'\n共接收了{}則訊息 | 共回覆了{}則訊息'.format(sum(counter[1].recv for counter in sorted_msg), 
                                                                              sum(counter[1].repl for counter in sorted_msg))
                    for channel, counter in sorted_msg:
                        text += u'\n{} - 頻道: {}'.format(counter, channel)

                    cmd_dict_text = ''
                    for cmd, cmd_obj in cmd_dict.items():
                        cmd_dict_text += u'[{} ({}次)] '.format(cmd, cmd_obj.count)
                    text += u'\n\n已呼叫系統指令{}次(包含呼叫失敗)。\n{}'.format(rec['JC_called'], cmd_dict_text)
                    text += u'\n已使用MFF傷害計算輔助系統{}次。'.format(rec['MFF_called'])
                    
                    text2 = u'全時統計資料\n\n'
                    text2 += u'已登錄{}組回覆組 \n({}組貼圖關鍵字 | {}組圖片回覆)\n\n'.format(
                        kwpct,
                        kwd.sticker_keyword_count(),
                        kwd.picture_reply_count())
                    text2 += u'共{}組回覆組可使用 ({:.2%})\n({}組貼圖關鍵字 | {}組圖片回覆)\n\n'.format(
                        kwd.row_count(True),
                        kwd.row_count(True) / float(kwpct),
                        kwd.sticker_keyword_count(True),
                        kwd.picture_reply_count(True))
                    text2 += u'已使用回覆組{}次\n\n'.format(kwd.used_count_sum())

                    text2 += u'製作最多回覆組的LINE使用者:\n{} ({}組 - {:.2%})\n\n'.format(
                        u'(找不到LINE帳號資料)' if line_profile is None else line_profile.display_name,
                        user_list_top[1],
                        user_list_top[1] / float(kwpct))

                    text2 += u'使用次數最多的回覆組 ({}次，{}組):'.format(first[0][kwdict_col.used_count], len(first))
                    for entry in first:
                        text2 += u'\nID: {} - {}'.format(entry[kwdict_col.id],
                                                         u'(貼圖ID {})'.format(entry[kwdict_col.keyword]) if entry[kwdict_col.is_sticker_kw] else entry[kwdict_col.keyword].decode('utf-8'))

                    text2 += u'\n\n使用次數最少的回覆組 ({}次，{}組):'.format(last[0][kwdict_col.used_count], len(last))
                    for entry in last:
                        text2 += u'\nID: {} - {}'.format(entry[kwdict_col.id],
                                                         u'(貼圖ID {})'.format(entry[kwdict_col.keyword]) if entry[kwdict_col.is_sticker_kw] else entry[kwdict_col.keyword].decode('utf-8'))
                        
                        last_count -= 1
                        if len(last) - last_count >= limit:
                            text2 += u'\n...(還有{}組)'.format(last_count)
                            break

                    api_reply(token, [TextSendMessage(text=text), TextMessage(text=text2)], src)
                # GROUP ban basic (info)
                elif cmd == 'G':
                    if not isinstance(src, SourceUser):
                        group_detail = gb.get_group_by_id(src.sender_id)
                        gid = get_source_channel_id(src)

                        uids = {'Admin': group_detail[gb_col.admin], 'Moderator 1': group_detail[gb_col.moderator1], 
                                'Moderator 2': group_detail[gb_col.moderator2], 'Moderator 3': group_detail[gb_col.moderator3]}

                        if group_detail is not None:
                            text = u'Chat Group ID: {id}\n'.format(id=group_detail[gb_col.groupId])
                            text += u'Silence: {sl}'.format(sl=group_detail[gb_col.silence])
                            for txt, uid in uids.items():
                                if uid is not None:
                                    prof = profile(uid)
                                    text += u'\n\n{}: {}\n'.format(txt,
                                                               '(LINE account data not found)' if prof is None else prof.display_name)
                                    text += u'{} User ID: {}'.format(txt,
                                                                      uid)
                        else:
                            text = u'Chat Group ID: {id}\n'.format(id=gid)
                            text += u'Silence: False'
                    else:
                        text = 'This function can be only execute in GROUP or ROOM.'
                    
                    api_reply(token, TextSendMessage(text=text), src)
                # GROUP ban advance
                elif cmd == 'GA':
                    error_no_action_fetch = 'No command fetched.\nWrong command, parameters or insufficient permission to use the function.'
                    illegal_source = 'This function can be used in 1v1 CHAT only. Permission key required. Please contact admin.'
                    
                    perm_dict = {3: 'Permission: Bot Administrator',
                                 2: 'Permission: Group Admin',
                                 1: 'Permission: Group Moderator',
                                 0: 'Permission: User'}
                    perm = permission_level(params.pop(1))
                    pert = perm_dict[perm]

                    param_count = len(params) - params.count(None)

                    if isinstance(src, SourceUser):
                        text = error_no_action_fetch

                        if perm >= 1 and param_count == 3:
                            action = params[1]
                            gid = params[2]
                            pw = params[3]

                            action_dict = {'SF': True, 'ST': False}
                            status_silence = {True: 'disabled', False: 'enabled'}

                            if action in action_dict:
                                settarget = action_dict[action]

                                if gb.set_silence(params[2], str(settarget), pw):
                                    text = 'Group auto reply function has been {res}.\n\n'.format(res=status_silence[settarget].upper())
                                    text += 'GID: {gid}'.format(gid=gid)
                                else:
                                    text = 'Group auto reply setting not changed.\n\n'
                                    text += 'GID: {gid}'.format(gid=gid)
                            else:
                                text = 'Invalid action: {action}. Recheck User Manual.'.format(action=action)
                        elif perm >= 2 and param_count == 5:
                            action = params[1]
                            gid = params[2]
                            new_uid = params[3]
                            pw = params[4]
                            new_pw = params[5]

                            action_dict = {'SA': gb.change_admin, 
                                           'SM1': gb.set_mod1,
                                           'SM2': gb.set_mod2,
                                           'SM3': gb.set_mod3}
                            pos_name = {'SA': 'Administrator',
                                        'SM1': 'Moderator 1',
                                        'SM2': 'Moderator 2',
                                        'SM3': 'Moderator 3'}

                            line_profile = profile(new_uid)

                            if line_profile is not None:
                                try:
                                    if action_dict[action](gid, new_uid, pw, new_pw):
                                        position = pos_name[action]

                                        text = u'Group administrator has been changed.\n'
                                        text += u'Group ID: {gid}\n\n'.format(gid=gid)
                                        text += u'New {pos} User ID: {uid}\n'.format(uid=new_uid, pos=position)
                                        text += u'New {pos} User Name: {unm}\n\n'.format(
                                            unm=line_profile.display_name,
                                            pos=position)
                                        text += u'New {pos} Key: {npkey}\n'.format(npkey=new_pw, pos=position)
                                        text += u'Please protect your key well!'
                                    else:
                                        text = '{pos} changing process failed.'
                                except KeyError as Ex:
                                    text = 'Invalid action: {action}. Recheck User Manual.'.format(action=action)
                            else:
                                text = 'Profile of \'User ID: {uid}\' not found.'.format(uid=new_uid)
                        elif perm >= 3 and param_count == 4:
                            action = params[1]
                            gid = params[2]
                            uid = params[3]
                            pw = params[4]
                            
                            if action != 'N':
                                text = 'Illegal action: {action}'.format(action=action)
                            else:
                                line_profile = profile(uid)

                                if line_profile is not None:
                                    if gb.new_data(gid, uid, pw):
                                        text = u'Group data registered.\n'
                                        text += u'Group ID: {gid}'.format(gid=gid)
                                        text += u'Admin ID: {uid}'.format(uid=uid)
                                        text += u'Admin Name: {name}'.format(gid=line_profile.display_name)
                                    else:
                                        text = 'Group data register failed.'
                                else:
                                    text = 'Profile of \'User ID: {uid}\' not found.'.format(uid=new_uid)
                    else:
                        text = illegal_source

                    api_reply(token, [TextSendMessage(text=pert), TextSendMessage(text=text)], src)
                # get CHAT id
                elif cmd == 'H':
                    text = get_source_channel_id(src)

                    if params[1] is not None:
                        uid = params[1]
                        line_profile = profile(uid)

                        source_type = 'Type: User'
                        if line_profile is not None:
                            text = u'使用者ID: {}\n'.format(uid)
                            text += u'使用者名稱: {}\n'.format(line_profile.display_name)
                            text += u'使用者頭貼網址: {}\n'.format(line_profile.picture_url)
                            text += u'使用者狀態訊息: {}'.format(line_profile.status_message)
                        else:
                            text = u'找不到使用者ID - {} 的詳細資訊。'.format(uid)
                    else:
                        if isinstance(src, SourceUser):
                            source_type = 'Type: User'
                        elif isinstance(src, SourceGroup):
                            source_type = 'Type: Group'
                        elif isinstance(src, SourceRoom):
                            source_type = 'Type: Room'
                        else:
                            text = 'Unknown chatting type.'

                    api_reply(token, [TextSendMessage(text=source_type), TextSendMessage(text=text)], src)
                # SHA224 generator
                elif cmd == 'SHA':
                    target = params[1]

                    if target != None:
                        text = hashlib.sha224(target.encode('utf-8')).hexdigest()
                    else:
                        text = 'Illegal Parameter to generate SHA224 hash.'

                    api_reply(token, TextSendMessage(text=text), src)
                # Look up vocabulary in OXFORD Dictionary
                elif cmd == 'O':
                    voc = params[1]

                    if oxford_disabled:
                        text = 'Dictionary look up function has disabled because of illegal Oxford API key or ID.'
                    else:
                        j = oxford_json(voc)

                        if type(j) is int:
                            code = j

                            text = 'Dictionary look up process returned status code: {status_code} ({explanation}).'.format(
                                status_code=code,
                                explanation=httplib.responses[code])
                        else:
                            text = ''
                            section_splitter = '..........................................................................................'

                            lexents = j['results'][0]['lexicalEntries']
                            for lexent in lexents:
                                text += '=={} ({})=='.format(lexent['text'], lexent['lexicalCategory'])
                                
                                lexentarr = lexent['entries']
                                for lexentElem in lexentarr:
                                    sens = lexentElem['senses']
                                    
                                    text += '\nDefinition:'
                                    for index, sen in enumerate(sens, start=1):
                                        if 'registers' in sen:
                                            reg_text = ', '.join(sen['registers'])

                                        for de in sen['definitions']:
                                            text += '\n{}. {} {}'.format(index, 
                                                                         de, 
                                                                         '({})'.format(', '.join(sen['registers'])) if 'registers' in sen else '')

                                        if 'examples' in sen:
                                            for ex in sen['examples']:
                                                text += '\n------{}'.format(ex['text'])

                                text += '\n{}\n'.format(section_splitter)

                            text += 'Powered by Oxford Dictionary.'

                    api_reply(token, TextSendMessage(text=text), src)
                # Leave group or room
                elif cmd == 'B':
                    cid = get_source_channel_id(src)

                    if isinstance(src, SourceUser):
                        text = 'Unable to leave 1v1 chat.'
                        api_reply(token, TextSendMessage(text=text), src)
                    else:
                        api_reply(token, TextSendMessage(text='Channel ID: {cid}\nBot Contact Link: http://line.me/ti/p/@fcb0332q'.format(cid=cid)), src)

                        if isinstance(src, SourceRoom):
                            api.leave_room(cid)
                        elif isinstance(src, SourceGroup):
                            api.leave_group(cid)
                # User profile
                elif cmd == 'U':
                    uid = params[1]

                    if uid is not None and len(uid) != 33:
                        text = 'The length of user id must be 33 characters.'   
                    else:
                        if isinstance(src, SourceUser):
                            line_profile = profile(uid if uid is not None else src.sender_id)

                            text = u'User ID:\n{uid}\nUser name:\n{name}\nProfile Picture URL:\n{url}\nStatus Message:\n{msg}'.format(
                                    uid=line_profile.user_id,
                                    name=line_profile.display_name,
                                    url=line_profile.picture_url,
                                    msg=line_profile.status_message)
                        else:
                            text = 'Unable to use this function in Group or Room.'

                    api_reply(token, TextSendMessage(text=text), src)
                else:
                    cmd_dict[cmd].count -= 1
        elif len(text.split(splitter_mff)) >= 2 and text.startswith('MFF'):
            rec['MFF_called'] += 1
            data = split(text, splitter_mff, 2)

            if data[1].upper().startswith('HELP'):
                api_reply(token, [TextSendMessage(text=mff.mff_dmg_calc.help_code()),
                                  TextSendMessage(text=u'下則訊息是訊息範本，您可以直接將其複製，更改其內容，然後使用。或是遵照以下格式輸入資料。\n\n{代碼(參見上方)} {參數}(%)\n\n例如:\nMFF\nSKC 100%\n魔力 1090%\n魔力 10.9\n\n欲察看更多範例，請前往 https://sites.google.com/view/jellybot/mff傷害計算'),
                                  TextSendMessage(text=mff.mff_dmg_calc.help_sample())], src)
            else:
                job = mff.mff_dmg_calc.text_job_parser(data[1])

                dmg_calc_dict = [[u'破防前非爆擊(弱點屬性)', mff.mff_dmg_calc.dmg_weak(job)],
                                 [u'破防前爆擊(弱點屬性)', mff.mff_dmg_calc.dmg_crt_weak(job)],
                                 [u'已破防非爆擊(弱點屬性)', mff.mff_dmg_calc.dmg_break_weak(job)],
                                 [u'已破防爆擊(弱點屬性)', mff.mff_dmg_calc.dmg_break_crt_weak(job)],
                                 [u'破防前非爆擊(非弱點屬性)', mff.mff_dmg_calc.dmg(job)],
                                 [u'破防前爆擊(非弱點屬性)', mff.mff_dmg_calc.dmg_crt(job)],
                                 [u'已破防非爆擊(非弱點屬性)', mff.mff_dmg_calc.dmg_break(job)],
                                 [u'已破防爆擊(非弱點屬性)', mff.mff_dmg_calc.dmg_break_crt(job)]]

                text = u'傷害表:'
                for title, value in dmg_calc_dict:
                    text += u'\n\n'
                    text += u'{}\n首發: {:.0f}\n連發: {:.0f}\n累積傷害(依次): {}'.format(title,
                                                                                        value['first'],
                                                                                        value['continual'],
                                                                                        u', '.join('{:.0f}'.format(x) for x in value['list_of_sum']))
                
                api_reply(token, TextSendMessage(text=text), src)
        else:
            reply_message_by_keyword(get_source_channel_id(src), token, text, False, src)
    except exceptions.LineBotApiError as ex:
        text = u'Boot up time: {boot}\n\n'.format(boot=boot_up)
        text += u'Line Bot Api Error. Status code: {sc}\n\n'.format(sc=ex.status_code)
        for err in ex.error.details:
            text += u'Property: {prop}\nMessage: {msg}\n'.format(prop=err.property, msg=err.message)

        send_error_url_line(token, text, get_source_channel_id(src))
    except Exception as exc:
        text = u'Boot up time: {boot}\n\n'.format(boot=boot_up)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        text += u'Type: {type}\nMessage: {msg}\nLine {lineno}'.format(type=exc_type, lineno=exc_tb.tb_lineno, msg=exc.message)

        send_error_url_line(token, text, get_source_channel_id(src))
    return

    if text == 'confirm':
        confirm_template = ConfirmTemplate(text='Do it?', actions=[
            MessageTemplateAction(label='Yes', text='Yes!'),
            MessageTemplateAction(label='No', text='No!'),
        ])
        template_message = TemplateSendMessage(
            alt_text='Confirm alt text', template=confirm_template)
        api_reply(event.reply_token, template_message, src)
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
        api_reply(event.reply_token, template_message, src)


# Incomplete
@handler.add(PostbackEvent)
def handle_postback(event):
    return
    if event.postback.data == 'ping':
        api_reply(
            event.reply_token, TextSendMessage(text='pong'), event.source)


@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    package_id = event.message.package_id
    sticker_id = event.message.sticker_id
    rep = event.reply_token
    src = event.source

    rec['Msg'][get_source_channel_id(src)].received()

    if isinstance(event.source, SourceUser):
        results = kwd.get_reply(sticker_id, True)
        
        if results is not None:
            result = results[0]
            kwdata = 'Associated Keyword ID: {id}\n'.format(id=result[kwdict_col.id])
        else:
            kwdata = 'No associated keyword.\n'

        api_reply(
            rep,
            [TextSendMessage(text=kwdata + 'Package ID: {pck_id}\nSticker ID: {stk_id}'.format(
                pck_id=package_id, 
                stk_id=sticker_id)),
             TextSendMessage(text='Picture Location on Android(png):\nemulated\\0\\Android\\data\\jp.naver.line.android\\stickers\\{pck_id}\\{stk_id}'.format(
                pck_id=package_id, 
                stk_id=sticker_id)),
             TextSendMessage(text='Picture Location on Windows PC(png):\nC:\\Users\\USER_NAME\\AppData\\Local\\LINE\\Data\\Sticker\\{pck_id}\\{stk_id}'.format(
                pck_id=package_id, 
                stk_id=sticker_id)),
             TextSendMessage(text='Picture Location on Web(png):\n{stk_url}'.format(stk_url=sticker_png_url(sticker_id)))],
            src
        )
    else:
        reply_message_by_keyword(get_source_channel_id(src), rep, sticker_id, True, src)


# Incomplete
@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    rec['Msg'][get_source_channel_id(event.source)].received()
    return

    api_reply(
        event.reply_token,
        LocationSendMessage(
            title=event.message.title, address=event.message.address,
            latitude=event.message.latitude, longitude=event.message.longitude
        ),
        event.source
    )


# Incomplete
@handler.add(MessageEvent, message=(ImageMessage, VideoMessage, AudioMessage))
def handle_content_message(event):
    rec['Msg'][get_source_channel_id(event.source)].received()
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

    api_reply(
        event.reply_token, [
            TextSendMessage(text='Save content.'),
            TextSendMessage(text=request.host_url + os.path.join('static', 'tmp', dist_name))
        ], event.source)


@handler.add(FollowEvent)
def handle_follow(event):
    api_reply(event.reply_token, introduction_template(), event.source)

# Incomplete
@handler.add(UnfollowEvent)
def handle_unfollow():
    return

    app.logger.info("Got Unfollow event")


@handler.add(JoinEvent)
def handle_join(event):
    src = event.source
    cid = src.sender_id

    if not isinstance(event.source, SourceUser):
        added = gb.new_data(cid, MAIN_UID, 'RaenonX')

        api_reply(event.reply_token, 
                  [TextMessage(text='Channel data registering {}. Type in \'JC  G\' to get more details.'.format('succeed' if added else 'failed')),
                   introduction_template()], 
                   cid)


# Encapsulated Functions
def split(text, splitter, size):
    list = []
  
    if text is not None:
        for i in range(size):
            if splitter not in text or i == size - 1:
                list.append(text)
                break
            list.append(text[0:text.index(splitter)])
            text = text[text.index(splitter)+len(splitter):]
  
    while len(list) < size:
        list.append(None)
    
    return list


def permission_level(key):
    if hashlib.sha224(key).hexdigest() == administrator:
        return 3
    elif hashlib.sha224(key).hexdigest() == group_admin:
        return 2
    elif hashlib.sha224(key).hexdigest() == group_mod:
        return 1
    else:
        return 0


def oxford_json(word):
    url = oxdict_url + word.lower()
    r = requests.get(url, headers = {'app_id': oxford_id, 'app_key': oxford_key})
    status_code = r.status_code

    if status_code != requests.codes.ok:
        return status_code
    else:
        return r.json()


def introduction_template():
    buttons_template = ButtonsTemplate(
            title=u'機器人簡介', text='歡迎使用小水母！', 
            actions=[
                URITemplateAction(label=u'點此開啟使用說明', uri='https://sites.google.com/view/jellybot'),
                URITemplateAction(label=u'點此導向開發者LINE帳號', uri='http://line.me/ti/p/~chris80124')
            ])
    template_message = TemplateSendMessage(
        alt_text=u'機器人簡介', template=buttons_template)
    return template_message


def sticker_png_url(sticker_id):
    return kw_dict_mgr.sticker_png_url(sticker_id)


def get_source_channel_id(source_event):
    return source_event.sender_id

def get_source_user_id(source_event):
    return source_event.user_id


def string_is_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False


def api_reply(reply_token, msgs, src):
    rec['Msg'][src if isinstance(src, (str, unicode)) else get_source_channel_id(src)].replied()

    if not rec['Silence']:
        if not isinstance(msgs, (list, tuple)):
            msgs = [msgs]

        for msg in msgs:
            if isinstance(msg, TextSendMessage) and len(msg.text) > 2000:
                api.reply_message(reply_token, 
                                  TextSendMessage(
                                      text='The content to reply is too long that program is unavailable to reply with LINE API.\n\nTo view full reply text, please click the URL below:\n{url}'.format(url=rec_text(msgs))))
                return

        api.reply_message(reply_token, msgs)
    else:
        print '=================================================================='
        print 'Bot set to silence. Expected message to reply will display below: '
        print msgs
        print '=================================================================='


def intercept_text(event):
    user_id = get_source_user_id(event.source)
    user_profile = profile(user_id)

    print '==========================================='
    print 'From Channel ID \'{}\''.format(get_source_channel_id(event.source))
    print 'From User ID \'{}\' ({})'.format(user_id, user_profile.display_name.encode('utf-8') if user_profile is not None else 'unknown')
    print 'Message \'{}\''.format(event.message.text.encode('utf-8'))
    print '==========================================='


def reply_message_by_keyword(channel_id, token, keyword, is_sticker_kw, src):
        if gb.is_group_set_to_silence(channel_id):
            return

        res = kwd.get_reply(keyword, is_sticker_kw)
        if res is not None:
            result = res[0]
            reply = result[kwdict_col.reply].decode('utf-8')

            if result[kwdict_col.is_pic_reply]:
                line_profile = profile(result[kwdict_col.creator])

                api_reply(token, TemplateSendMessage(
                    alt_text='Picture / Sticker Reply.\nID: {id}'.format(id=result[kwdict_col.id]),
                    template=ButtonsTemplate(text=u'ID: {id}\nCreated by {creator}.'.format(
                        creator='(LINE account data not found)' if line_profile is None else line_profile.display_name,
                        id=result[kwdict_col.id]), 
                                             thumbnail_image_url=reply,
                                             actions=[
                                                 URITemplateAction(label=u'Original Picture', uri=reply)
                                             ])), src)
            else:
                api_reply(token, 
                          TextSendMessage(text=u'{rep}{id}'.format(rep=reply,
                                                                   id='' if not is_sticker_kw else '\n\nID: {id}'.format(id=result[kwdict_col.id]))),
                          src)


def rec_error(details, channel_id):
    if details is not None:
        timestamp = str(int(time.time()))
        report_content['Error'][timestamp] = 'Error Occurred at {time}\n'.format(time=datetime.now() + timedelta(hours=8))
        report_content['Error'][timestamp] = 'At channel ID: {cid}'.format(cid=channel_id)
        report_content['Error'][timestamp] += '\n\n'
        report_content['Error'][timestamp] += details  
        return timestamp


def rec_query(full_query):
    timestamp = str(int(time.time()))
    report_content['FullQuery'][timestamp] = full_query
    return request.url_root + url_for('full_query', timestamp=timestamp)[1:]


def rec_info(full_info):
    timestamp = str(int(time.time()))
    report_content['FullInfo'][timestamp] = full_info
    return request.url_root + url_for('full_info', timestamp=timestamp)[1:]


def rec_text(textmsg_list):
    if not isinstance(textmsg_list, (list, tuple)):
        textmsg_list = [textmsg_list]

    timestamp = str(int(time.time()))
    report_content['Text'][timestamp] = ''
    for index, txt in enumerate(textmsg_list, start=1):
        report_content['Text'][timestamp] += 'Message {index}\n'.format(index=index)
        report_content['Text'][timestamp] += txt.text
        report_content['Text'][timestamp] += '==============================='
    return request.url_root + url_for('full_content', timestamp=timestamp)[1:]



def send_error_url_line(token, error_text, channel_id):
    timestamp = rec_error(traceback.format_exc(), channel_id)
    err_detail = u'詳細錯誤URL: {url}\n錯誤清單: {url_full}'.format(
        url=request.url_root + url_for('get_error_message', timestamp=timestamp)[1:],
        url_full=request.url_root + url_for('get_error_list')[1:])
    print report_content['Error'][timestamp]
    api_reply(token, [TextSendMessage(text=error_text), TextSendMessage(text=err_detail)], channel_id)


def profile(uid):
    try:
        return api.get_profile(uid)
    except exceptions.LineBotApiError as ex:
        if ex.status_code == 404:
            return None


if __name__ == "__main__":
    # create tmp dir for download content
    make_static_tmp_dir()

    app.run(port=os.environ['PORT'], host='0.0.0.0')
