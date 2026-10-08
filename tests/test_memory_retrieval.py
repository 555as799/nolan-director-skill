"""Scene-level memory/time retrieval regressions, not a generated-dialogue grade."""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/nolan-director'
spec = importlib.util.spec_from_file_location('memory_recall', SKILL / 'scripts/recall.py')
recall = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recall)


class MemoryRetrievalTests(unittest.TestCase):
    def search(self, query, mode='experience'):
        return recall.recall(query, mode=mode, limit=4, root=SKILL, backend='json')

    def test_synthetic_scene_reaches_specific_time_and_emotion_experience(self):
        result = self.search('我想拍离站的一瞬间回想起曾经生活的城市，这段记忆怎么表现？')
        self.assertIn('subjective_memory', result['situations'])
        first = {card['id'] for card in result['cards'][:3]}
        self.assertIn('QA12-DI02', first)
        self.assertIn('EXP-IN01', first)

    def test_new_memory_scene_is_not_tied_to_station(self):
        result = self.search('想拍毕业典礼的镜头，掌声中她回忆起童年的三个场景，怎样表现这段记忆？')
        self.assertIn('subjective_memory', result['situations'])
        self.assertIn('EXP-IN01', {card['id'] for card in result['cards'][:3]})

    def test_subjective_time_without_memory_keyword(self):
        result = self.search('雨滴即将碰到玻璃，我想让这一秒容纳十年的相聚与离别，时间怎么处理？')
        self.assertIn('subjective_time', result['situations'])
        self.assertIn('QA12-DI02', {card['id'] for card in result['cards'][:3]})

    def test_english_memory_montage_reaches_relevant_experience(self):
        result = self.search('How can a memory montage while waiting for a train show why she is ready to leave?')
        self.assertIn('subjective_memory', result['situations'])
        self.assertTrue({'QA12-DI02', 'EXP-IN01'} & {card['id'] for card in result['cards'][:3]})

    def test_english_subjective_time_reaches_relevant_experience(self):
        result = self.search('I want to stretch a moment before a train arrives into years of longing.')
        self.assertIn('subjective_time', result['situations'])
        self.assertIn('QA12-DI02', {card['id'] for card in result['cards'][:3]})

    def test_station_alone_does_not_impose_flashbacks(self):
        result = self.search('上车后两个人坐在窗边，这场对白怎么写？')
        self.assertNotIn('subjective_memory', result['situations'])
        self.assertNotIn('subjective_time', result['situations'])

    def test_background_memory_does_not_override_local_revision(self):
        result = self.search('前面是站台上回忆童年的镜头，现在只改她上车以后这句对白，让它听起来不像解释。')
        self.assertNotIn('subjective_memory', result['situations'])
        self.assertNotIn('subjective_time', result['situations'])
        self.assertIn('exposition', result['situations'])

    def test_declined_memory_does_not_trigger_memory_route(self):
        result = self.search('我不需要闪回或主观时间，只谈上车后这句道谢。')
        self.assertNotIn('subjective_memory', result['situations'])
        self.assertNotIn('subjective_time', result['situations'])

    def test_english_declined_memory_does_not_trigger_memory_route(self):
        result = self.search('Do not discuss flashbacks or subjective time. Instead fix the final line of dialogue.')
        self.assertNotIn('subjective_memory', result['situations'])
        self.assertNotIn('subjective_time', result['situations'])

    def test_joint_photography_account_remains_collaborator(self):
        result = recall.recall('QA12-DI03', mode='craft', root=SKILL, backend='json')
        card = result['cards'][0]
        self.assertEqual(card['id'], 'QA12-DI03')
        self.assertEqual(card['kind'], 'collaborator')
        self.assertIn('Wally Pfister', card['speaker'])


if __name__ == '__main__':
    unittest.main()
