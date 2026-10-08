import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from writing_policy import assess_chapters, normalize_settings, resolve_policy, visible_characters
import test_writing_workspace as workspace_fixtures
import test_writing_batch as batch_fixtures


class WritingPolicyTest(unittest.TestCase):
    def setUp(self):
        self.section = dict(id='SEC-1', parent_id=None, title='工单管理与事件闭环',
                            task='平台工单分派、处置和复核', requirement_ids=['R-1'],
                            scoring_ids=['S-1'], visuals_needed=[])
        self.requirements = [dict(id='R-1', text='系统提供工单查询、分派、复核功能')]
        self.scoring = [dict(id='S-1', node_type='scored', title='技术方案', max_score=25,
                            rule_text='依据方案完整性、实施可行性及异常处置评分')]

    def policy(self, settings=None):
        return resolve_policy(self.section, [self.section], self.scoring,
                              self.requirements, settings or {})

    def test_scheme_scoring_recommends_expansion_with_original_basis(self):
        p = self.policy()
        self.assertEqual((p['target_words'], p['detail_level']), (2000, 'detailed'))
        self.assertEqual(p['scoring_basis'][0]['rule_text'], self.scoring[0]['rule_text'])
        self.assertTrue(p['expansion_requirements'])

    def test_proof_and_price_scores_do_not_inflate_prose(self):
        for title, rule in [('企业业绩', '每提供一份合同得5分，最高25分'),
                            ('投标报价', '价格分按报价公式计算，最低报价得满分')]:
            self.scoring[0].update(title=title, rule_text=rule, max_score=50)
            p = self.policy()
            self.assertNotEqual(p['detail_level'], 'detailed')
            self.assertIn(p['scoring_types'][0], ['evidence', 'price'])

    def test_scoring_group_is_not_counted_as_leaf(self):
        self.scoring[0]['node_type'] = 'rollup'
        p = self.policy()
        self.assertEqual(p['scoring_ids'], [])
        self.assertEqual(p['target_words'], 1000)

    def test_inherited_scoring_and_complex_requirements(self):
        parent = dict(id='P', parent_id=None, title='技术方案', scoring_ids=['S-1'])
        self.section.update(parent_id='P', scoring_ids=[])
        p = resolve_policy(self.section, [parent, self.section], self.scoring, self.requirements, {})
        self.assertTrue(p['scoring_basis'][0]['inherited'])
        self.section.update(parent_id=None, scoring_ids=[], requirement_ids=[f'R-{i}' for i in range(12)])
        p = self.policy()
        self.assertEqual(p['detail_level'], 'detailed')

    def test_explicit_targets_override_recommendations(self):
        for target in (500, 1000, 2000):
            p = self.policy({'chapter_overrides': {'SEC-1': {'target_words': target}}})
            self.assertEqual(p['target_words'], target)
            self.assertTrue(p['length_required'])
        self.assertEqual(self.policy({'length_mode': 'fixed', 'target_words': 750})['target_words'], 750)

    def test_fixed_form_has_no_automatic_filler_target(self):
        self.section['title'] = '投标函'
        self.assertIsNone(self.policy()['target_words'])
        self.assertEqual(self.policy({'chapter_overrides': {'SEC-1': {'target_words': 500}}})['target_words'], 500)

    def test_detail_override_and_visible_count_exclude_markup(self):
        p = self.policy({'chapter_overrides': {'SEC-1': {'detail_level': 'brief'}}})
        self.assertEqual(p['target_words'], 500)
        self.assertEqual(visible_characters('# 标题\n\n**正文** [链接](https://hidden)\n![不计图片](assets/a.png)\n```json\n内部配置\n```\n'), 6)

    def test_system_function_policy_and_user_exemption(self):
        settings = {'visuals': {'system_ui_policy': 'all_system_sections'}}
        self.assertTrue(self.policy(settings)['ui_required'])
        self.section['title'] = '项目管理与培训服务'
        self.section['task'] = '项目进度及培训安排'
        self.section['requirement_ids'] = []
        self.assertFalse(self.policy(settings)['system_section'])
        self.section['title'] = '工单管理'
        settings['chapter_overrides'] = {'SEC-1': {'ui_required': False}}
        self.assertFalse(self.policy(settings)['ui_required'])

    def test_task_card_ui_requirement_cannot_be_disabled_by_preference(self):
        self.section['visuals_needed'] = ['工单界面截图']
        self.assertTrue(self.policy({'visuals': {'system_ui_policy': 'off'},
                                     'chapter_overrides': {'SEC-1': {'ui_required': False}}})['ui_required'])

    def test_low_absolute_scheme_scores_use_project_relative_priority(self):
        self.scoring[0]['max_score'] = 8
        self.assertEqual(self.policy()['target_words'], 2000)
        self.scoring.append(dict(id='S-2', node_type='scored', max_score=30,
                                 title='总体方案', rule_text='方案完整性'))
        self.assertEqual(self.policy()['target_words'], 1500)

    def test_scheme_conditions_with_each_item_scores_are_not_proof_counting(self):
        self.scoring[0].update(max_score=10, rule_text='总体设计、实施计划、异常处置每项内容完整得2分，方案可操作性得4分')
        self.assertEqual(self.policy()['scoring_types'], ['scheme'])
        self.assertEqual(self.policy()['target_words'], 2000)

    def test_user_permission_function_is_identified_without_generic_system_word(self):
        self.section.update(title='用户与权限管理', task='账号新增、停用、角色授权和权限查询')
        self.requirements[0]['text'] = '账号新增、停用、角色授权和权限查询'
        self.assertTrue(self.policy({'visuals': {'system_ui_policy': 'all_system_sections'}})['ui_required'])

    def test_unknown_fields_invalid_numbers_and_unknown_sections_rejected(self):
        for value in [{'length_mode': 'invented'}, {'length_tolerance': float('nan')},
                      {'chapter_overrides': {'SEC-1': {'target_words': True}}},
                      {'chapter_overrides': {'SEC-1': {'invented': 1}}},
                      {'visuals': {'min_ui_images': 0}}]:
            with self.assertRaises(ValueError):
                normalize_settings(value, ['SEC-1'])
        with self.assertRaises(ValueError):
            normalize_settings({'chapter_overrides': {'UNKNOWN': {'target_words': 1000}}}, ['SEC-1'])

    def test_length_deficit_and_missing_ui_are_not_semantic_acceptance(self):
        with TemporaryDirectory() as td:
            settings = {'chapter_overrides': {'SEC-1': {'target_words': 500, 'ui_required': True}}}
            result = assess_chapters(Path(td), [self.section],
                                     [dict(section_id='SEC-1', body_markdown='不足')],
                                     self.scoring, self.requirements, [], settings)
            self.assertFalse(result['passed'])
            self.assertEqual(result['chapters'][0]['length_status'], 'too_short')
            self.assertEqual(result['chapters'][0]['ui_status'], 'missing')
            self.assertEqual(result['semantic_acceptance'], 'NOT_TESTED')

    def test_raster_must_exist_decode_be_inserted_and_be_an_interface(self):
        # Use a real tiny PNG fixture without introducing an imaging dependency.
        import base64
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
        with TemporaryDirectory() as td:
            root = Path(td); (root / 'assets').mkdir()
            image = root / 'assets/ui.png'; image.write_bytes(png)
            body = '说明' * 250 + '\n![工单界面](assets/ui.png)'
            figure = dict(id='FIG-1', section_id='SEC-1', kind='interface', state='rendered',
                          rendered_path='assets/ui.png', caption='界面设计示意，非实际系统截图')
            settings = {'chapter_overrides': {'SEC-1': {'target_words': 500, 'ui_required': True}}}
            def check():
                return assess_chapters(root, [self.section], [dict(section_id='SEC-1', body_markdown=body)],
                                       self.scoring, self.requirements, [figure], settings)
            self.assertTrue(check()['passed'], check())
            figure['kind'] = 'architecture'
            self.assertFalse(check()['passed'])
            figure['kind'] = 'interface'; body = '说明' * 250
            self.assertFalse(check()['passed'])
            body += '\n![工单界面](assets/ui.png)'; image.write_bytes(b'broken')
            self.assertFalse(check()['passed'])


class WritingPolicyIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.fixture = workspace_fixtures.WritingWorkspaceTest('test_settings_are_validated_and_persisted')
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.project = self.fixture.project

    def test_settings_cas_and_selected_policy_reopen(self):
        ws = self.fixture._workspace(); before = ws.settings()
        overrides = {'SEC-1': {'target_words': 500, 'ui_required': True},
                     'SEC-2': {'target_words': 2000}}
        ws.save_settings({'chapter_overrides': overrides, 'expected_revision': before['revision'],
                          'expected_sha256': before['sha256']})
        self.assertEqual(self.fixture._workspace().state('CH-1')['chapter_policy']['target_words'], 500)
        with self.assertRaises(ValueError):
            ws.save_settings({'chapter_overrides': overrides, 'expected_revision': before['revision'],
                              'expected_sha256': before['sha256']})

    def test_real_batch_context_contains_resolved_policy(self):
        f = batch_fixtures.WritingBatchTest('test_prepare_context_and_slots_honor_parallel_limit')
        f.setUp(); self.addCleanup(f.tearDown)
        settings = json.loads((f.project / 'work/writing-settings.json').read_text())
        settings['chapter_overrides'] = {'SEC-1': {'target_words': 2000, 'ui_required': True}}
        f._write('work/writing-settings.json', settings)
        batch = f._batch(); batch.prepare(['SEC-1']); claimed = batch.claim('SEC-1')
        context = json.loads((f.project / claimed['context_path']).read_text())
        self.assertEqual(context['resolved_policy']['target_words'], 2000)
        self.assertTrue(context['resolved_policy']['ui_required'])

    def test_settings_change_invalidates_frozen_snapshot(self):
        import bidkit
        before = self.fixture._workspace().settings()
        bidkit.snapshot(self.project, 'work/frozen.json')
        self.fixture._workspace().save_settings({'chapter_overrides': {'SEC-1': {'target_words': 500}},
                                                 'expected_revision': before['revision'],
                                                 'expected_sha256': before['sha256']})
        status = bidkit.verify_snapshot(self.project, self.project / 'work/frozen.json')
        self.assertFalse(status['current'])
        self.assertIn('work/writing-settings.json', status['changed'])

    def test_core_review_blocks_missing_configured_chapter_outputs(self):
        import bidkit
        import review_checks
        import core_review_fixture
        with TemporaryDirectory() as td:
            p = Path(td) / 'review'; bidkit.init_project(p, 'CORE-POLICY')
            matrix = core_review_fixture.populate(p)
            (p / 'work/writing-settings.json').write_text(json.dumps({'length_mode': 'fixed', 'target_words': 1000}))
            snap = bidkit.snapshot(p, 'reviews/snapshot.json')
            review = core_review_fixture.review(p, matrix, snap)
            result = review_checks.check(p, review, p / 'reviews/snapshot.json')
            self.assertFalse(result['formal_release_ready'])
            self.assertTrue(result['writing_policy']['blocking_issues'])


if __name__ == '__main__':
    unittest.main()
