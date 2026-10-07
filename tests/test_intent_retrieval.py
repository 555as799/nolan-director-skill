"""Independent reviewer cases: lexical routing, not generated-dialogue quality."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'skills/nolan-director'
spec = importlib.util.spec_from_file_location('intent_recall', SKILL/'scripts/recall.py')
recall = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recall)


class IntentRetrievalTests(unittest.TestCase):
    def search(self, query, mode='craft'):
        return recall.recall(query, mode=mode, root=SKILL, backend='json')

    def test_explicit_topic_change_beats_background(self):
        result = self.search('我不想反复排练，演员已经很自然。现在只想处理结尾对白像说明书的问题。')
        self.assertNotIn('actor_process', result['situations'])
        self.assertIn('exposition', result['situations'])
        self.assertIn('V4-N006', [c['id'] for c in result['cards']])

    def test_declined_structure_is_not_retrieval_intent(self):
        result = self.search('不要多时间线，就顺着一天拍；怎样把房间外的城市做得像真的？')
        self.assertNotIn('audience_orientation', result['situations'])
        self.assertIn('EXP-DGA12A', [c['id'] for c in result['cards']])

    def test_declined_budget_is_not_retrieval_intent(self):
        result = self.search('我不需要低成本方案，制片人已经解决钱的问题。我要知道怎样让一句对白听起来不像解释。')
        self.assertNotIn('limited_resources', result['situations'])
        self.assertIn('exposition', result['situations'])

    def test_english_rehearsal(self):
        result = self.search('Can I preserve spontaneity while rehearsing a scene?', 'experience')
        self.assertIn('actor_process', result['situations'])
        self.assertTrue({'QA12-D01','EXP-DGA17B'} & {c['id'] for c in result['cards']})

    def test_english_time(self):
        result = self.search('I want a coherent emotional line through three different time scales.', 'experience')
        self.assertIn('audience_orientation', result['situations'])
        self.assertIn('EXP-DGA17A', [c['id'] for c in result['cards']])

    def test_english_stopwords_cannot_imply_memory(self):
        result = self.search('I am not sure what you would do.', 'experience')
        self.assertEqual(result['cards'], [])

    def test_traditional_film_name(self):
        result = self.search('想找《黑暗騎士》的攝影經驗，該怎麼讓城市像一個角色？')
        self.assertIn('F06', [c['id'] for c in result['cards']][:3])

    def test_negative_outcome_is_still_a_concern(self):
        result = self.search('不要让观众看不懂这三条时间线。')
        self.assertIn('audience_orientation', result['situations'])

    def test_actor_refusal_is_still_actor_issue(self):
        result = self.search('演员不愿意排练，但另一位要求充分准备。')
        self.assertIn('actor_process', result['situations'])

    def test_low_resources_survive_a_different_rejection(self):
        result = self.search('预算不够，但我不想削减演员。')
        self.assertIn('limited_resources', result['situations'])

    def test_only_declined_topic_does_not_return_false_experience(self):
        result = self.search('不要再谈低成本预算建议。', 'experience')
        self.assertEqual(result['cards'], [])

    def test_english_alias_matches_whole_words(self):
        self.assertFalse(recall.alias_in('resoundingly successful', 'sound'))
        self.assertTrue(recall.alias_in('sound design', 'sound'))

    def test_full_film_title_wins_over_franchise_prefix(self):
        names = recall.films_in(recall.normalize_text('黑暗騎士崛起 The Dark Knight Rises'))
        self.assertEqual(names, {('黑暗骑士崛起','the dark knight rises')})

    def test_exact_id_and_budget_still_hold(self):
        result = recall.recall('QA12-D01', mode='experience', budget=1000, root=SKILL, backend='json')
        self.assertEqual(result['cards'][0]['id'], 'QA12-D01')
        self.assertLessEqual(len(recall.encoded(result)),1000)

    def test_experience_stays_attributed(self):
        result = self.search('Zimmer 配乐协作', 'experience')
        self.assertTrue(all(c.get('kind')=='experience' and c.get('speaker')=='Christopher Nolan'
                            for c in result['cards'] if not c.get('truncated')))

    def test_long_query_metadata_respects_output_budget(self):
        result = recall.recall('演员排练。' * 1000, mode='experience', budget=1000,
                               root=SKILL, backend='json')
        self.assertLessEqual(len(recall.encoded(result)),1000)

    def test_science_exposition_retrieves_new_selection_experience(self):
        result=recall.recall('科幻开场 信息取舍 解释影响人物动作',mode='craft',limit=2,
                             root=SKILL,backend='json')
        self.assertIn('worldbuilding_selection',result['situations'])
        self.assertTrue({'EXP-AU01','EXP-SC01'} & {c['id'] for c in result['cards']})

    def test_scifi_genre_alone_does_not_force_science_selection(self):
        result=self.search('科幻片里的午餐戏，人物沉默看着门口。')
        self.assertNotIn('worldbuilding_selection',result['situations'])

    def test_declined_worldbuilding_is_not_current_problem(self):
        result=self.search('我不需要讨论世界设定取舍，现在只想处理一声门响。')
        self.assertNotIn('worldbuilding_selection',result['situations'])

    def test_period_performance_retrieves_current_action_approach(self):
        result=self.search('年代戏的表演很僵，演员像在模仿老电影的腔调。','experience')
        self.assertIn('period_performance',result['situations'])
        self.assertIn('EXP-PR02',{c['id'] for c in result['cards']})

    def test_first_reaction_retrieves_prepared_production_experience(self):
        result=self.search('我想保留演员第一次看到消息时的新鲜反应，剧组准备到什么程度再开机？','experience')
        self.assertIn('first_reaction',result['situations'])
        self.assertIn('EXP-AU02',{c['id'] for c in result['cards']})


if __name__ == '__main__':
    unittest.main()
