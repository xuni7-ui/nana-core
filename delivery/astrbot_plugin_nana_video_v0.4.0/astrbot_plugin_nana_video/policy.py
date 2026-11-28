"""Host routing and durable attempt limits; independent of AstrBot and the vision engine."""
import datetime
import hashlib
import re
import sqlite3
import time
from pathlib import Path

# No implicit old-summary insertion on bare 'video', 'subtitle', 'clip', or a bare second.
RECALL=re.compile(r'(?:回看|重看|再看|再观察|重新(?:看|观察|分析)).{0,24}(?:视频|画面|字幕|片段|秒|分钟)|(?:上(?:一)?个|刚才的|前面那个|之前的)(?:B站)?视频.{0,50}(?:看看|看一下|看下|哪|什么|怎么|是否|有没有|发生|秒|分钟|回看|再看)|(?:回看|重看|再看|重新观察)\s*(?:第)?\d')
REQUEST=re.compile(r'看看|看一下|看下|分析|解读|总结|回看|重看|再看|看视频|讲讲|视频.{0,16}(?:怎么样|什么|怎么|发生|是否|有没有)')
DETAIL=re.compile(r'回看|重看|再看|重新|字幕|文字|细节|角落|第\s*\d+\s*秒|\d+\s*(?:秒|分钟)|\d{1,3}:\d{2}')

def recall_intent(text): return bool(RECALL.search(text))

def route(mode,video_count,foreign,bvids,text):
    if mode not in ('coexist_bv','standalone'): return 'delegate'
    if foreign: return 'delegate'
    if video_count and mode=='coexist_bv': return 'delegate'
    if video_count+len(bvids)>1: return 'ambiguous'
    if video_count: return 'direct'
    if bvids: return 'bili'
    return 'recall' if recall_intent(text) else 'none'

def _items(value):
    if not isinstance(value,str): return set()
    return {x.strip() for x in re.split(r'[,，\n]',value) if x.strip()}

def allowed(event,cfg,text):
    sender=str(event.get_sender_id())
    if not sender: return False
    users=_items(cfg.get('allowed_senders',''))
    if users and sender not in users: return False
    if event.is_private_chat(): return True
    group=str(event.get_group_id())
    if not group or group not in _items(cfg.get('allowed_groups','')): return False
    return cfg.get('group_explicit_only',True) is False or bool(REQUEST.search(text))

def frame_limit(duration,question,maximum):
    target=4 if duration<=20 else 6 if duration<=120 else 8
    if DETAIL.search(question): target=max(4,min(8,maximum))
    return min(maximum,target)

class BudgetDenied(ValueError):
    pass

class Budget:
    """Counts potentially billable attempts (not dollars or confirmed usage).
    A failed or ambiguous model call is not refunded. SQLite serializes admission
    across concurrent plugin instances and survives process restart. UTC+8 day.
    """
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS attempts(day TEXT NOT NULL, sender TEXT NOT NULL, count INTEGER NOT NULL, last REAL NOT NULL, PRIMARY KEY(day,sender))')

    def connect(self):
        return sqlite3.connect(str(self.path),timeout=2)

    @staticmethod
    def day(now):
        return datetime.datetime.fromtimestamp(now,datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()

    @staticmethod
    def key(sender):
        return hashlib.sha256(sender.encode('utf-8')).hexdigest()

    def _read(self,db,day,key):
        total=db.execute('SELECT COALESCE(SUM(count),0) FROM attempts WHERE day=?',(day,)).fetchone()[0]
        row=db.execute('SELECT count,last FROM attempts WHERE day=? AND sender=?',(day,key)).fetchone() or (0,0)
        return total,*row

    @staticmethod
    def _gate(total,count,last,now,daily,personal,interval,same_request):
        if total>=daily: raise BudgetDenied('插件今日模型调用额度已用完')
        if count>=personal: raise BudgetDenied('该发送者今日模型调用额度已用完')
        if not same_request and last and now-last<interval: raise BudgetDenied('视频观察冷却中')

    def check(self,sender,daily,personal,interval):
        now=time.time()
        with self.connect() as db:
            total,count,last=self._read(db,self.day(now),self.key(sender))
            self._gate(total,count,last,now,daily,personal,interval,False)

    def reserve(self,sender,daily,personal,interval,*,same_request=False):
        now=time.time(); day=self.day(now); key=self.key(sender)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            total,count,last=self._read(db,day,key)
            self._gate(total,count,last,now,daily,personal,interval,same_request)
            db.execute('INSERT INTO attempts(day,sender,count,last) VALUES(?,?,1,?) ON CONFLICT(day,sender) DO UPDATE SET count=count+1,last=excluded.last',(day,key,now))
            cutoff=self.day(now-8*86400)
            db.execute('DELETE FROM attempts WHERE day<?',(cutoff,))

    def total(self):
        with self.connect() as db:
            return db.execute('SELECT COALESCE(SUM(count),0) FROM attempts WHERE day=?',(self.day(time.time()),)).fetchone()[0]
