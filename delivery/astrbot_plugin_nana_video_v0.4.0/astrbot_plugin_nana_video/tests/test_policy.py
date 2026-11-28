import tempfile
import unittest
from pathlib import Path
from astrbot_plugin_nana_video.policy import Budget,BudgetDenied,route,frame_limit,recall_intent
class PolicyTest(unittest.TestCase):
    def test_route(self):
        self.assertEqual(route('coexist_bv',1,False,['BV1234567890'],'看看'),'delegate')
        self.assertEqual(route('standalone',1,False,[],'看看'),'direct')
        self.assertEqual(route('standalone',1,True,[],'看看'),'delegate')
        self.assertEqual(route('coexist_bv',0,False,['BV1234567890'],'看看'),'bili')
        self.assertEqual(route('coexist_bv',0,False,['a','b'],'看看'),'ambiguous')
    def test_recall(self):
        for q in ('视频','字幕','片段','今天看了个视频','第1秒','那个视频怎么样'):
            self.assertFalse(recall_intent(q),q)
        for q in ('回看第1秒','刚才的视频第23秒发生了什么','重新观察视频'):
            self.assertTrue(recall_intent(q),q)
    def test_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'quota.db';b=Budget(p)
            b.reserve('a',3,2,30)
            with self.assertRaises(BudgetDenied):b.reserve('a',3,2,30)
            b.reserve('a',3,2,30,same_request=True)
            with self.assertRaises(BudgetDenied):b.reserve('a',3,2,0)
            b.reserve('b',3,2,0)
            self.assertEqual(Budget(p).total(),3)
            with self.assertRaises(BudgetDenied):Budget(p).reserve('c',3,2,0)
    def test_frames(self):
        self.assertEqual(frame_limit(8,'看看',8),4)
        self.assertEqual(frame_limit(100,'看看',8),6)
        self.assertEqual(frame_limit(400,'看看',8),8)
        self.assertEqual(frame_limit(400,'回看第23秒',2),2)
