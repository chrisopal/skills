import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from diagram_svg import SpecError, _overlap_segment, _wrap, render_svg  # noqa: E402


def base_spec(layout="layered"):
    row_values = [(0, 0), (0, 1), (1, 0), (1, 1)]
    if layout == "sequence":
        row_values = [(0, 0), (0, 1), (0, 2), (0, 3)]
    nodes = [
        {"id": f"n{i}", "title": f"节点 {i}", "description": "可审计处理", "row": row, "col": col, "role": "process"}
        for i, (row, col) in enumerate(row_values)
    ]
    return {
        "version": "1.0",
        "title": "测试图",
        "subtitle": "辅助说明",
        "layout": layout,
        "theme": "reference",
        "width": 1000,
        "nodes": nodes,
        "edges": [{"from": "n0", "to": "n1", "label": "前进"}, {"from": "n1", "to": "n2", "label": "下行"}, {"from": "n2", "to": "n0", "label": "反馈", "kind": "feedback", "route": "left"}],
    }


class DiagramSvgTests(unittest.TestCase):
    def test_all_layouts_render(self):
        for layout in ("layered", "flow", "pipeline", "swimlane", "network", "parallel", "sequence", "matrix"):
            with self.subTest(layout=layout):
                result = render_svg(base_spec(layout))
                self.assertTrue(result["svg"].startswith("<svg"))
                self.assertEqual(len(result["nodes"]), 4)
                self.assertTrue(all(edge["safe"] for edge in result["edges"]))

    def test_svg_is_parseable_and_escapes_text(self):
        spec = base_spec()
        spec["title"] = '<危险 & "标题">'
        spec["nodes"][0]["title"] = "a & b < c"
        result = render_svg(spec)
        ET.fromstring(result["svg"])
        self.assertNotIn("foreignObject", result["svg"])
        self.assertNotIn("<script", result["svg"])
        self.assertIn("a &amp; b &lt; c", result["svg"])

    def test_themes_change_colors_but_not_geometry(self):
        reference = render_svg(base_spec(), "reference")
        for theme in ("blue", "teal", "green", "slate", "monochrome"):
            candidate = render_svg(base_spec(), theme)
            self.assertEqual([(n["x"], n["y"], n["width"], n["height"]) for n in reference["nodes"]], [(n["x"], n["y"], n["width"], n["height"]) for n in candidate["nodes"]])
            self.assertEqual([e["points"] for e in reference["edges"]], [e["points"] for e in candidate["edges"]])
            self.assertNotEqual(reference["svg"], candidate["svg"])
        monochrome = render_svg(base_spec(), "monochrome")
        self.assertNotIn("#C0392B", monochrome["svg"])

    def test_long_text_is_retained_and_wrapped(self):
        spec = base_spec()
        text = "长文本" * 40 + " / ASCII details " * 12
        spec["nodes"][0]["description"] = text
        result = render_svg(spec)
        self.assertGreater(result["nodes"][0]["height"], result["nodes"][1]["height"])
        for part in ("长文本", "ASCII details"):
            self.assertIn(part, result["svg"])

    def test_validation_rejects_overlap_and_dangling_edge(self):
        spec = base_spec()
        spec["nodes"][1]["span"] = 2
        spec["nodes"][2]["col"] = 1
        with self.assertRaises(SpecError):
            render_svg(spec)

    def test_validation_rejects_unknown_fields_and_bad_container_values(self):
        spec = base_spec()
        spec["unexpected"] = True
        with self.assertRaises(SpecError):
            render_svg(spec)
        spec = base_spec()
        spec["nodes"][0]["unexpected"] = "x"
        with self.assertRaises(SpecError):
            render_svg(spec)
        spec = base_spec()
        spec["subtitle"] = 12
        with self.assertRaises(SpecError):
            render_svg(spec)
        with self.assertRaises(SpecError):
            render_svg([])
        spec = base_spec()
        spec["edges"][0]["to"] = "missing"
        with self.assertRaises(SpecError):
            render_svg(spec)

    def test_sequence_supports_self_message(self):
        spec = base_spec("sequence")
        spec["edges"] = [{"from": "n1", "to": "n1", "label": "内部校验"}]
        result = render_svg(spec)
        self.assertEqual(result["layout"], "sequence")
        self.assertGreater(result["height"], 300)
        self.assertTrue(result["edges"][0]["safe"])

    def test_sequence_messages_are_timestamp_lines_and_labels_do_not_overlap(self):
        spec = base_spec("sequence")
        spec["edges"] = [
            {"from": "n0", "to": "n2", "label": "横向消息"},
            {"from": "n1", "to": "n1", "label": "自消息"},
            {"from": "n2", "to": "n3", "label": "下一步"},
        ]
        result = render_svg(spec)
        self.assertEqual(len(result["edges"][0]["points"]), 2)
        self.assertEqual(result["edges"][0]["points"][0][1], result["edges"][0]["points"][1][1])
        self.assertEqual(len(result["edges"][1]["points"]), 4)
        boxes = [edge["label_box"] for edge in result["edges"] if edge["label_box"]]
        for first, second in zip(boxes, boxes[1:]):
            self.assertFalse(first["x"] < second["x"] + second["width"] and second["x"] < first["x"] + first["width"] and first["y"] < second["y"] + second["height"] and second["y"] < first["y"] + first["height"])

    def test_sequence_wrapped_self_label_keeps_next_message_clear(self):
        spec = base_spec("sequence")
        spec["edges"] = [
            {"from": "n1", "to": "n1", "label": "校验身份与去重"},
            {"from": "n1", "to": "n2", "label": "分派工单"},
            {"from": "n2", "to": "n1", "label": "反馈处置结果与审核状态"},
        ]
        result = render_svg(spec)
        for index, edge in enumerate(result["edges"]):
            box = edge["label_box"]
            self.assertGreaterEqual(result["height"], box["y"] + box["height"] + 20)
            for other in result["edges"][index + 1:]:
                self.assertGreaterEqual(other["points"][0][1], box["y"] + box["height"] + 12)
                for a, b in zip(other["points"], other["points"][1:]):
                    self.assertFalse(_overlap_segment(a, b, (box["x"], box["y"], box["x"] + box["width"], box["y"] + box["height"])))

    def test_diamond_wraps_inside_and_regular_self_loop_is_checked(self):
        spec = base_spec()
        spec["nodes"] = [{"id": "decision", "title": "这是一个非常长的决策标题" * 2, "description": "条件说明" * 8, "row": 0, "col": 0, "role": "decision", "shape": "diamond"}, {"id": "neighbor", "title": "相邻节点", "row": 0, "col": 1, "role": "neutral"}]
        spec["edges"] = [{"from": "decision", "to": "decision", "label": "复核"}]
        result = render_svg(spec)
        node = result["nodes"][0]
        self.assertGreater(node["height"], 100)
        self.assertTrue(all(sum(1.0 if ord(char) > 255 else 0.58 for char in line) <= node["width"] * 0.52 / 14 for line in node["title_lines"] + node["description_lines"]))
        lines = node["title_lines"] + node["description_lines"]
        for index, line in enumerate(lines):
            baseline = node["y"] + node["height"] / 2 - (len(lines) * 22) / 2 + 16 + index * 22
            distance = abs(baseline - (node["y"] + node["height"] / 2))
            available = node["width"] * (1 - 2 * (distance + 8) / node["height"])
            estimated = sum(1.0 if ord(char) > 255 else 0.72 for char in line) * 16 * 1.05
            self.assertLessEqual(estimated, available + 1)
        self.assertEqual(result["edges"][0]["points"][0], result["edges"][0]["points"][-1])
        self.assertTrue(result["edges"][0]["safe"])

    def test_adjacent_groups_are_disjoint_and_long_chrome_wraps(self):
        spec = base_spec()
        spec["title"] = "长标题" * 60
        spec["subtitle"] = "副标题" * 80
        spec["footer"] = "页脚" * 80
        spec["groups"] = [
            {"id": "left", "title": "左侧分组" * 20, "members": ["n0"], "kind": "zone"},
            {"id": "right", "title": "右侧分组" * 20, "members": ["n1"], "kind": "zone"},
        ]
        result = render_svg(spec)
        left, right = result["groups"]
        self.assertLessEqual(left["x"] + left["width"], right["x"])
        self.assertGreater(result["height"], 500)
        ET.fromstring(result["svg"])

    def test_routes_do_not_cross_node_interiors(self):
        result = render_svg(base_spec())
        by_id = {node["id"]: node for node in result["nodes"]}
        for edge in result["edges"]:
            for a, b in zip(edge["points"], edge["points"][1:]):
                for node in result["nodes"]:
                    if node["id"] in {edge["from"], edge["to"]}:
                        continue
                    rect = (node["x"], node["y"], node["x"] + node["width"], node["y"] + node["height"])
                    self.assertFalse(_overlap_segment(a, b, rect), (edge["id"], node["id"], a, b))
        label_boxes = [edge["label_box"] for edge in result["edges"] if edge["label_box"]]
        for box in label_boxes:
            self.assertTrue(all(not (box["x"] < node["x"] + node["width"] and box["x"] + box["width"] > node["x"] and box["y"] < node["y"] + node["height"] and box["y"] + box["height"] > node["y"]) for node in result["nodes"]))

    def test_routes_have_outward_source_and_inward_target_stubs(self):
        result = render_svg(base_spec())
        horizontal, vertical = result["edges"][0], result["edges"][1]
        self.assertEqual(horizontal["points"][1][0] - horizontal["points"][0][0], 16)
        self.assertEqual(horizontal["points"][-1][0] - horizontal["points"][-2][0], 16)
        self.assertEqual(vertical["points"][1][1] - vertical["points"][0][1], 16)
        self.assertEqual(vertical["points"][-1][1] - vertical["points"][-2][1], 16)

    def test_cli_writes_svg_and_small_metadata(self):
        root = Path(__file__).resolve().parents[1]
        source = root / "assets" / "examples" / "layered-platform.diagram.json"
        output = Path(self.id().replace(".", "_") + ".svg")
        try:
            completed = subprocess.run([sys.executable, str(SCRIPT_DIR / "diagram_svg.py"), "--source", str(source), "--out", str(output)], check=True, capture_output=True, text=True)
            metadata = json.loads(completed.stdout)
            self.assertNotIn("svg", metadata)
            self.assertTrue(output.exists())
            ET.parse(output)
        finally:
            output.unlink(missing_ok=True)

    def test_cli_refuses_overwrite_and_non_svg_output(self):
        root = Path(__file__).resolve().parents[1]
        source = root / "assets" / "examples" / "layered-platform.diagram.json"
        output = Path(self.id().replace(".", "_") + ".svg")
        output.write_text("keep", encoding="utf-8")
        try:
            completed = subprocess.run([sys.executable, str(SCRIPT_DIR / "diagram_svg.py"), "--source", str(source), "--out", str(output)], capture_output=True, text=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep")
            bad = output.with_suffix(".txt")
            completed = subprocess.run([sys.executable, str(SCRIPT_DIR / "diagram_svg.py"), "--source", str(source), "--out", str(bad)], capture_output=True, text=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse(bad.exists())
        finally:
            output.unlink(missing_ok=True)

    def test_default_width_and_a4_warnings_are_reported(self):
        spec = base_spec()
        spec.pop("width")
        spec["nodes"] = [{"id": f"n{i}", "title": f"层{i}", "row": i, "col": 0} for i in range(16)]
        spec["edges"] = []
        result = render_svg(spec)
        self.assertEqual(result["width"], 900)
        self.assertTrue(any("A4" in warning for warning in result["warnings"]))

    def test_branch_labels_use_local_slots_and_feedback_reserves_canvas(self):
        spec = base_spec("pipeline")
        spec["width"] = 900
        spec["nodes"] = [
            {"id": "a", "title": "入口", "row": 0, "col": 0, "role": "primary"},
            {"id": "b", "title": "决策", "row": 1, "col": 0, "role": "decision", "shape": "diamond"},
            {"id": "c", "title": "发布", "row": 2, "col": 0, "role": "success"},
        ]
        spec["edges"] = [
            {"from": "a", "to": "b", "label": "批准"},
            {"from": "b", "to": "c", "label": "是"},
            {"from": "c", "to": "a", "label": "材料不足，退回补充", "kind": "feedback", "route": "right"},
        ]
        result = render_svg(spec)
        self.assertGreater(result["width"], 900)
        self.assertEqual([edge["label"] for edge in result["edges"]], ["批准", "是", "材料不足，退回补充"])
        for edge in result["edges"]:
            box = edge["label_box"]
            self.assertIsNotNone(box)
            self.assertTrue(all(not (box["x"] < node["x"] + node["width"] and box["x"] + box["width"] > node["x"] and box["y"] < node["y"] + node["height"] and box["y"] + box["height"] > node["y"]) for node in result["nodes"]))

    def test_network_and_parallel_cross_column_edges_use_horizontal_ports(self):
        spec = {
            "version": "1.0",
            "title": "端口方向",
            "layout": "network",
            "nodes": [
                {"id": "gateway", "title": "网关", "row": 1, "col": 0, "role": "primary"},
                {"id": "app", "title": "应用", "row": 0, "col": 1, "role": "process"},
                {"id": "db", "title": "数据库", "row": 1, "col": 1, "role": "data"},
            ],
            "edges": [
                {"from": "gateway", "to": "app"},
                {"from": "app", "to": "db"},
            ],
        }
        for layout in ("network", "parallel"):
            spec["layout"] = layout
            result = render_svg(spec)
            cross, vertical = result["edges"]
            self.assertEqual(cross["points"][1][0] - cross["points"][0][0], 16)
            app = next(node for node in result["nodes"] if node["id"] == "app")
            self.assertEqual(cross["points"][-1][0], app["x"])
            self.assertEqual(cross["points"][-1][0] - cross["points"][-2][0], 16)
            self.assertEqual(vertical["points"][1][1] - vertical["points"][0][1], 16)
            self.assertEqual(vertical["points"][-1][1] - vertical["points"][-2][1], 16)

    def test_short_ascii_identifiers_wrap_as_whole_tokens(self):
        lines = _wrap("生产设备与PLC", 119, 16)
        self.assertIn("PLC", lines)
        self.assertNotIn("PL", lines)
        self.assertNotIn("C", lines)

    def test_far_label_has_checked_arrowless_leader(self):
        spec = {
            "version": "1.0",
            "title": "标签引导",
            "layout": "pipeline",
            "width": 900,
            "nodes": [
                {"id": "a", "title": "入口", "row": 0, "col": 0},
                {"id": "b", "title": "处理", "row": 1, "col": 0},
                {"id": "c", "title": "出口", "row": 2, "col": 0},
            ],
            "edges": [{"from": "a", "to": "b", "label": "raw_payload + 业务原文 + source_sha256"}, {"from": "b", "to": "c"}],
        }
        result = render_svg(spec)
        leader = result["edges"][0].get("leader_points")
        self.assertIsNotNone(leader)
        marker = 'data-edge-label-leader="edge-0"'
        start = result["svg"].index(marker)
        end = result["svg"].index("/>", start)
        self.assertNotIn("marker-end", result["svg"][start:end])

    def test_swimlane_lanes_share_full_process_bounds_and_title_clearance(self):
        spec = {
            "version": "1.0",
            "title": "责任泳道",
            "layout": "swimlane",
            "nodes": [
                {"id": "operator", "title": "登记", "row": 0, "col": 0},
                {"id": "platform", "title": "核验", "row": 1, "col": 1},
                {"id": "responder", "title": "处置", "row": 2, "col": 2},
            ],
            "edges": [{"from": "operator", "to": "platform"}, {"from": "platform", "to": "responder"}],
            "groups": [
                {"id": "g0", "title": "登记人员", "members": ["operator"], "kind": "lane"},
                {"id": "g1", "title": "业务平台", "members": ["platform"], "kind": "lane"},
                {"id": "g2", "title": "处置人员", "members": ["responder"], "kind": "lane"},
            ],
        }
        result = render_svg(spec)
        self.assertEqual({group["y"] for group in result["groups"]}, {result["groups"][0]["y"]})
        self.assertEqual({group["height"] for group in result["groups"]}, {result["groups"][0]["height"]})
        top = min(node["y"] for node in result["nodes"])
        bottom = max(node["y"] + node["height"] for node in result["nodes"])
        self.assertLessEqual(result["groups"][0]["y"], top - 30)
        self.assertGreaterEqual(result["groups"][0]["y"] + result["groups"][0]["height"], bottom + 20)
        title_boxes = [(group["x"] + 8, group["y"] + 8, group["x"] + group["width"] - 8, group["y"] + 26) for group in result["groups"]]
        for edge in result["edges"]:
            for a, b in zip(edge["points"], edge["points"][1:]):
                self.assertTrue(all(not _overlap_segment(a, b, box) for box in title_boxes))
            for a, b in zip(edge.get("leader_points", []), edge.get("leader_points", [])[1:]):
                self.assertTrue(all(not _overlap_segment(a, b, box) for box in title_boxes))

    def test_branch_labels_follow_unique_target_segments_independent_of_edge_order(self):
        spec = {
            "version": "1.0",
            "title": "分支标签",
            "layout": "flow",
            "nodes": [
                {"id": "risk", "title": "风险?", "row": 0, "col": 0, "span": 2, "role": "decision", "shape": "diamond"},
                {"id": "standard", "title": "标准", "row": 1, "col": 0},
                {"id": "expert", "title": "专家", "row": 1, "col": 1},
                {"id": "merge", "title": "汇聚", "row": 2, "col": 0, "span": 2},
            ],
            "edges": [
                {"from": "risk", "to": "standard", "label": "否"},
                {"from": "risk", "to": "expert", "label": "是"},
                {"from": "standard", "to": "merge", "label": "检查通过"},
                {"from": "expert", "to": "merge", "label": "会审通过"},
            ],
        }
        for order in (spec["edges"], list(reversed(spec["edges"]))):
            spec["edges"] = order
            result = render_svg(spec)
            centers = {edge["label"]: edge["label_box"]["x"] + edge["label_box"]["width"] / 2 for edge in result["edges"]}
            self.assertLess(centers["否"], centers["是"])
            self.assertLess(centers["检查通过"], centers["会审通过"])


if __name__ == "__main__":
    unittest.main()
