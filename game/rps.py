# -*- coding: utf-8 -*-

from enum import Enum
from tool import random_gen
from error import error
import time
from collections import defaultdict

class rps(object):
    """Game of Rock-Paper-Scissors"""

    def __init__(self, vs_bot):
        self._gap_time = -1
        self._vs_bot = vs_bot
        self._battle_dict = {battle_item.rock: [],
                             battle_item.paper: [],
                             battle_item.scissor: []}
        self._result_generated = False

    def init_register(self, rock, paper, scissor):
        """
        Initially register process must use sticker ID to create instance
        Return void when successfully initialized
        """
        try:
            int(rock)
        except ValueError:
            return error.main.invalid_thing_with_correct_format(u'石頭貼圖ID', u'整數', rock)
        try:
            int(paper)
        except ValueError:
            return error.main.invalid_thing_with_correct_format(u'布貼圖ID', u'整數', rock)
        try:
            int(scissor)
        except ValueError:
            return error.main.invalid_thing_with_correct_format(u'剪刀貼圖ID', u'整數', rock)

        if scissor == rock == paper:
            return error.main.miscellaneous(u'剪刀、石頭、布不可相同，請重新輸入。')
        elif scissor == rock:
            return error.main.miscellaneous(u'剪刀和石頭的定義衝突(相同)，請重新輸入。')
        elif rock == paper:
            return error.main.miscellaneous(u'石頭和布的定義衝突(相同)，請重新輸入。')
        elif paper == scissor:
            return error.main.miscellaneous(u'布和剪刀的定義衝突(相同)，請重新輸入。')
        
        self.register_battle_item(battle_item.paper, True, paper)
        self.register_battle_item(battle_item.rock, True, rock)
        self.register_battle_item(battle_item.scissor, True, scissor)
        self._player_dict = defaultdict(battle_player)
        if self._vs_bot:
            self._player_dict[0] = battle_player(u'電腦', 0)

        self._reset()

    def register_battle_item(self, battle_item, is_sticker, content):
        self._battle_dict[battle_item].append(battle_item_representative(battle_item, is_sticker, content))

    def register_player(self, name, uid):
        self._player_dict[uid] = battle_player(name, uid)

    def play(self, item, player_uid):
        """
        return not void if error occurred.
        No action if player not exist.
        """
        if len(self._player_dict) < 2:
            return error.main.miscellaneous(u'玩家人數不足，需要先註冊2名玩家以後方可遊玩。')
        else:
            if self._play_entered:
                self._play2(item, player_uid)
            else:
                self._play1(item, player_uid)

    def result_text(self):
        """
        Player object will be released after calling this method.
        """
        if self._result_enum == battle_result.tie:
            text = u'【平手】'
        elif self._result_enum == battle_result.win1:
            text = u'【{} 勝利】'.format(self._player1.name)
            text += u'\n【{} 敗北】'.format(self._player2.name)
        elif self._result_enum == battle_result.win2:
            text = u'【{} 勝利】'.format(self._player2.name)
            text += u'\n【{} 敗北】'.format(self._player1.name)
        elif self._result_enum == battle_result.undefined:
            text = u'【尚未猜拳】'
        else:
            raise ValueError(error.main.invalid_thing(u'猜拳結果', result_enum))
        
        text += u'\n本次猜拳兩拳間格時間(包含程式處理時間) {:.2f} 秒'.format(self._gap_time)
        text += u'\n\n【最新玩家結果】'
        text += u'\n'.join([u'{} - {}W {}L {}T'.format(player.name, player.win, player.lose, player.tied) for player in self._player_dict])

        self._reset()
        return text

    def reset_statistics(self):
        for player in self._player_dict:
            player.reset_statistics() 

    def find_battle_item(self, is_sticker, content):
        for battle_item_key, representatives in self._battle_dict:
            for representative in representatives:
                if representative.is_sticker == is_sticker and representative.content == content:
                    return battle_item_key

        return battle_item.none

    def _play1(self, item, player_uid):
        player_obj = self._player_dict.get(player_uid)
        if player_obj is not None:
            self._player1 = player_obj
            player_obj.last_item = self._battle_dict[item]
            self._play_begin_time = time.time()

            if self._vs_bot:
                self._play2(random_gen.random_drawer.draw_text(self._battle_dict.keys()), 0)
            else:
                self._play_entered = True

    def _play2(self, item, player_uid):
        player_obj = self._player_dict.get(player_uid)
        if player_obj is not None:
            self._player2 = player_obj
            player_obj.last_item = self._battle_dict[item]
            self._gap_time = time.time() - self._play_begin_time
            self._play_entered = False
            self._calculate_result()

    def _calculate_result(self):
        result = self._player1.last_item - self._player2.last_item
        result = result % 3
        self._result_enum = battle_result(result)
        if self._result_enum == battle_result.win1:
            self._player1.win()
            self._player2.lose()
        elif self._result_enum == battle_result.win2:
            self._player2.win()
            self._player1.lose()
        elif self._result_enum == battle_result.tie:
            self._player1.tied()
            self._player2.tied()
        self._result_generated = True
            
    def _reset(self):
        self._play_entered = False
        self._result_generated = False
        self._play_begin_time = 0
        self._result_enum = battle_result.undefined
        self._player1 = None
        self._player2 = None

    @property
    def gap_time(self):
        return self._gap_time

    @property
    def vs_bot(self):
        return self._vs_bot

    @property
    def battle_dict(self):
        try:
            return self._battle_dict
        except NameError:
            pass

    @property
    def player_dict(self):
        try:
            return self._player_dict
        except NameError:
            pass

    @property
    def is_waiting_next(self):
        try:
            return self._play_entered
        except NameError:
            pass

    @property
    def result_generated(self):
        return self._result_generated


class battle_item(Enum):
    rock = 1
    paper = 2
    scissor = 3
    none = -1


class battle_item_representative(object):
    def __init__(self, battle_item, is_sticker, content):
        if is_sticker:
            try:
                int(content)
            except Exception as ex:
                raise ex
        self._battle_item = battle_item
        self._is_sticker = is_sticker
        self._content = content

    @property
    def is_sticker(self):
        return self._is_sticker

    @property
    def content(self):
        return self._content

    @property
    def battle_item(self):
        return self._battle_item


class battle_result(Enum):
    undefined = -1
    tie = 0
    win1 = 1
    win2 = 2


class battle_player(object):
    def __init__(self, name, uid):
        self._name = name
        self._uid = uid
        self.reset_statistics()

    def win(self):
        self._win += 1
        
    def lose(self):
        self._lose += 1
        
    def tied(self):
        self._tied += 1

    def reset_statistics(self):
        self._win = 0
        self._lose = 0
        self._tied = 0
        self._last_item = battle_item.none

    @property
    def name(self):
        return self._name
    
    @property
    def win(self):
        return self._win
    
    @property
    def lose(self):
        return self._lose
    
    @property
    def tied(self):
        return self._tied
    
    @property
    def last_item(self):
        return self._last_item

    @last_item.setter
    def last_item(self, value):
        self._last_item = value
        

