#!/usr/bin/env python3
"""Generate BookCore, cover plan, storyboard, narration, and publish draft."""

from __future__ import annotations

import argparse
from pathlib import Path

from book2video_common import (
    is_principles,
    is_pyramid_principle,
    load_input,
    normalize_input,
    project_name,
    slugify_book,
    style_bible,
    write_json,
)


def pyramid_book_core(book_title: str, book_author: str | None) -> dict:
    return {
        "bookTitle": book_title,
        "bookAuthor": book_author or "芭芭拉·明托",
        "coreProblem": "复杂信息很多，但汇报时听众抓不到结论、层级和证据关系。",
        "videoCoreQuestion": "怎样把杂乱材料变成一套听得懂、记得住、能执行的汇报结构？",
        "coreClaim": "先给结论，再用分组理由和证据层层支撑，表达才会清晰有力。",
        "coreConcepts": [
            {"name": "结论先行", "explanation": "先说答案，再展开说明。", "usage": "适合汇报、PPT、方案开头。"},
            {"name": "以上统下", "explanation": "上层概括下层，下层支撑上层。", "usage": "适合构建清晰的汇报层级。"},
            {"name": "归类分组", "explanation": "同类信息放在一起，避免交叉重复。", "usage": "适合整理材料、证据和分论点。"},
            {"name": "逻辑递进", "explanation": "组内按照时间顺序、结构顺序或重要性顺序展开。", "usage": "适合让表达更顺畅、更有说服力。"},
        ],
        "visualModel": {
            "name": "金字塔结构",
            "type": "pyramid",
            "description": "自上而下，层层支撑。",
            "layers": [
                {"name": "结论 / 核心观点", "explanation": "先说结论，再展开理由。"},
                {"name": "分论点 / 关键理由", "explanation": "上层统领下层，下层支撑上层。"},
                {"name": "事实 / 数据 / 案例", "explanation": "用证据让结论站得住脚。"},
            ],
        },
        "sop": [
            {"step": 1, "title": "先写一句话结论", "action": "用一句话说明你最想让对方记住的判断。", "output": "一句话结论"},
            {"step": 2, "title": "拆成 2-4 个关键理由", "action": "找出支撑结论的关键分论点。", "output": "分组理由"},
            {"step": 3, "title": "每组内容归类分组", "action": "把同类证据放在同一组，避免交叉重复。", "output": "分组结构"},
            {"step": 4, "title": "用事实、数据、案例支撑", "action": "在每个理由下面放证据。", "output": "证据清单"},
        ],
        "aiSkillCandidate": {
            "name": "AI汇报结构生成器",
            "goal": "把杂乱材料转成清晰的金字塔汇报结构。",
            "input": ["会议纪要", "项目材料", "客户需求", "调研记录", "原始PPT"],
            "output": ["一句话结论", "分组理由", "证据清单", "PPT大纲", "讲解稿"],
            "useCases": ["项目汇报", "售前方案", "复盘材料", "管理层简报"],
        },
    }


def principles_book_core(book_title: str, book_author: str | None) -> dict:
    return {
        "bookTitle": book_title,
        "bookAuthor": book_author or "瑞·达利欧",
        "coreProblem": "很多人会复盘问题，却没有把错误、分歧和经验沉淀成下一次可执行的原则。",
        "videoCoreQuestion": "怎样把失败、分歧和复杂决策转成个人或组织可以复用的原则系统？",
        "coreClaim": "《原则》的价值不是鸡汤，而是一套用极度求真、极度透明和可信度加权决策持续进化的操作系统。",
        "coreConcepts": [
            {"name": "极度求真", "explanation": "把现实看清楚，比维护面子更重要。", "usage": "适合复盘失败、识别根因、澄清事实。"},
            {"name": "极度透明", "explanation": "让关键事实和分歧被看见，减少组织里的黑箱。", "usage": "适合团队协作、项目复盘、管理沟通。"},
            {"name": "创意择优", "explanation": "不是谁声音大听谁，而是让最好想法胜出。", "usage": "适合重大决策、方案评审、战略讨论。"},
            {"name": "痛苦 + 反思 = 进步", "explanation": "把挫败感变成反思材料，再变成下一次行动规则。", "usage": "适合个人成长、管理迭代、能力训练。"},
            {"name": "可信度加权决策", "explanation": "更重视有经验、有记录、能解释判断的人。", "usage": "适合专家评审、招聘、投资和复杂项目决策。"},
        ],
        "visualModel": {
            "name": "原则操作系统反馈环",
            "type": "flywheel",
            "description": "从现实到原则，再从原则回到行动的持续进化循环。",
            "layers": [
                {"name": "目标与现实", "explanation": "先确认想要什么，再诚实面对当前事实。"},
                {"name": "问题与根因", "explanation": "不只修表面问题，要找到反复出现的底层原因。"},
                {"name": "原则与决策", "explanation": "把反思转成规则，用可信度加权处理分歧。"},
                {"name": "执行与复盘", "explanation": "把规则用于行动，再用结果继续修正原则。"},
            ],
        },
        "sop": [
            {"step": 1, "title": "写清目标", "action": "明确这次复盘或决策真正想达成的结果。", "output": "目标陈述"},
            {"step": 2, "title": "面对现实", "action": "列出事实、数据、失败信号和不同人的观察。", "output": "事实清单"},
            {"step": 3, "title": "诊断根因", "action": "区分表层事故和反复出现的能力、机制或判断问题。", "output": "根因判断"},
            {"step": 4, "title": "引入可信分歧", "action": "让有相关经验的人挑战判断，并记录分歧点。", "output": "分歧与权重"},
            {"step": 5, "title": "沉淀原则", "action": "把经验写成下次遇到同类情况时可执行的规则。", "output": "原则条目"},
            {"step": 6, "title": "执行并复盘", "action": "用原则指导下一次行动，再根据结果修正原则。", "output": "迭代记录"},
        ],
        "aiSkillCandidate": {
            "name": "AI原则复盘教练",
            "goal": "把失败记录、项目复盘或决策分歧转成可执行的个人/团队原则。",
            "input": ["失败记录", "项目复盘", "决策背景", "团队分歧", "会议纪要"],
            "output": ["事实清单", "根因判断", "可信分歧表", "原则条目", "下一步行动清单"],
            "useCases": ["项目复盘", "管理决策", "个人成长", "团队机制建设"],
        },
    }


def principles_book_research(book_title: str, book_author: str | None) -> dict:
    return {
        "bookTitle": book_title,
        "bookSubtitle": "Life & Work",
        "bookAuthor": book_author or "瑞·达利欧",
        "publishedYear": 2017,
        "publisher": "Simon & Schuster / Avid Reader Press",
        "researchSummary": [
            "《Principles: Life & Work》围绕 Ray Dalio 在生活、管理和组织建设中的原则展开。",
            "官方材料强调 idea meritocracy、radical transparency，以及把现实、目标和行动原则系统化。",
            "出版社/书商资料强调这本书把 life、management、economics、investing 视作可被规则化理解的系统。",
        ],
        "visualFacts": [
            "Ray Dalio 是 Bridgewater Associates 创始人，官方视觉常呈现成熟投资人、管理者和公开演讲语境；成片可用非可识别的成熟投资人剪影表达，不生成真实肖像。",
            "《Principles: Life & Work》常见书封视觉是深色商业精装书、白色标题区和红色/橙色重点；成片可用深色原则手册和办公桌阅读场景表达，不复刻真实封面设计。",
            "Principles 官方语境强调 idea meritocracy、radical transparency、goals/problems/diagnosis/design/doing 的系统循环；组织场景可用透明会议室、白板、反馈便签、决策矩阵和循环飞轮表达。",
        ],
        "sourceNotes": [
            {
                "label": "Principles official site",
                "url": "https://www.principles.com/",
                "note": "Official positioning: life and management principles, idea meritocracy, radical transparency.",
            },
            {
                "label": "Principles official Life & Work page",
                "url": "https://www.principles.com/principles-for-success",
                "note": "Official page presents Principles: Life & Work and related learning materials.",
            },
            {
                "label": "Google Books listing",
                "url": "https://books.google.com/books/about/Principles.html?id=okk1DwAAQBAJ",
                "note": "Describes the book as systemizing life, management, economics, and investing into rules and machines.",
            },
            {
                "label": "Wikipedia bibliographic cross-check",
                "url": "https://en.wikipedia.org/wiki/Principles_%28book%29",
                "note": "Cross-check for publication year, publisher, and book metadata.",
            },
        ],
    }


def generic_book_research(input_data: dict) -> dict:
    return {
        "bookTitle": input_data["bookTitle"],
        "bookAuthor": input_data.get("bookAuthor"),
        "researchSummary": ["未确认：请先补充书籍摘要、作者资料、出版社资料或联网调研结果。"],
        "visualFacts": ["未确认：请补充作者、书封、场景、历史语境或关键物件。"],
        "sourceNotes": [],
    }


def generic_book_core(input_data: dict) -> dict:
    book_title = input_data["bookTitle"]
    return {
        "bookTitle": book_title,
        "bookAuthor": input_data.get("bookAuthor"),
        "coreProblem": "未确认：需要从书籍资料中确认这本书解决的现实问题。",
        "videoCoreQuestion": "这本书最适合转成一个什么可执行方法？",
        "coreClaim": "未确认：需要基于书籍摘要或 Book2Skill 输出提炼一句话核心观点。",
        "coreConcepts": [
            {"name": "核心概念A", "explanation": "未确认：替换为书中的方法论结构。", "usage": "说明适用场景。"},
            {"name": "核心概念B", "explanation": "未确认：替换为书中的方法论结构。", "usage": "说明适用场景。"},
        ],
        "visualModel": {
            "name": "方法结构图",
            "type": "flow",
            "description": "未确认：根据书籍方法论选择 pyramid/tree/matrix/flow 等模型。",
            "layers": [],
        },
        "sop": [
            {"step": 1, "title": "定义输入", "action": "明确使用者要提供的材料。", "output": "输入清单"},
            {"step": 2, "title": "生成结构", "action": "把核心概念转成步骤。", "output": "方法步骤"},
            {"step": 3, "title": "形成产物", "action": "把步骤封装成可复用模板。", "output": "可执行模板"},
        ],
        "aiSkillCandidate": {
            "name": "AI方法执行器",
            "goal": "把书中的方法论转成可复用工作流。",
            "input": ["书籍摘要", "用户场景", "原始材料"],
            "output": ["结构化步骤", "执行模板", "结果检查表"],
            "useCases": ["学习转化", "工作提效", "团队培训"],
        },
    }


def cover_plan(input_data: dict, book_core: dict) -> dict:
    pyramid = is_pyramid_principle(input_data["bookTitle"])
    principles = is_principles(input_data["bookTitle"])
    modules = [
        {
            "id": "problem",
            "title": "这本书解决什么问题？",
            "body": book_core["coreProblem"],
            "icon": "target",
        },
        {
            "id": "core_concepts",
            "title": "核心内涵",
            "body": [f"{item['name']}：{item['explanation']}" for item in book_core["coreConcepts"]],
            "icon": "lightbulb",
        },
        {
            "id": "expression_formula",
            "title": "表达公式" if pyramid else "原则反馈步骤" if principles else "方法步骤",
            "body": [item["title"] for item in book_core["sop"]],
            "icon": "flow",
        },
        {
            "id": "ai_skill",
            "title": "可以变成什么AI Skill？",
            "body": f"{book_core['aiSkillCandidate']['name']}：{book_core['aiSkillCandidate']['goal']}",
            "icon": "robot",
        },
    ]
    diagram_layers = [
        {
            "label": layer["name"],
            "description": layer["explanation"],
            "colorRole": "primary" if index == 0 else "neutral",
        }
        for index, layer in enumerate(book_core["visualModel"].get("layers", []))
    ]
    return {
        "projectName": project_name(input_data["bookTitle"]),
        "aspectRatio": input_data.get("coverAspectRatio", "4:5"),
        "title": f"《{input_data['bookTitle']}》拆书",
        "headline": "为什么你总是讲不清？" if pyramid else "别只复盘问题，要沉淀原则" if principles else "把一本书变成一个AI Skill",
        "subtitle": "不是你没内容，而是你没结构" if pyramid else "把经验变成个人和组织的操作系统" if principles else "读书不是记住观点，而是把观点变成能力",
        "badgeText": "一本书，一个AI Skill",
        "footerText": "读书不是记住观点，而是把观点变成能力。",
        "theme": input_data["stylePreset"],
        "layout": {
            "header": "large_title_problem_hook",
            "leftModules": ["problem", "core_concepts"],
            "mainDiagram": "pyramid_plus_grouping_tree" if pyramid else "principles_flywheel" if principles else "methodology_flow",
            "bottomModules": ["expression_formula", "ai_skill"],
            "tags": ["职场表达", "汇报", "PPT", "方案", "AI提效"] if pyramid else ["管理", "复盘", "决策", "组织透明", "AI提效"] if principles else ["读书方法", "AI Skill", "知识视频"],
        },
        "mascot": {
            "enabled": True,
            "placement": "top-right",
            "style": {
                "type": "anthropomorphic_book",
                "originality": "required",
                "tone": "professional",
                "characterRules": ["原创书籍人格化形象", "直立书本轮廓", "克制的表情", "橙色书签", "少量绿色叶片点缀"],
                "forbiddenRules": ["不要夸张大眼睛", "不要儿童绘本风", "不要过度卡通", "不要抄袭已有吉祥物"],
            },
            "imagePrompt": "原创书籍人格化形象，直立书本轮廓，暖白书封，极简线条，克制表情，成熟友好，专业知识品牌风格，轻微教学手势，橙色书签，少量绿色叶片点缀，干净黑色线条，not childish, not kawaii, not overly cartoonish, no existing character reference, transparent background",
        },
        "modules": modules,
        "diagram": {
            "type": book_core["visualModel"]["type"],
            "title": f"{book_core['visualModel']['name']}：{book_core['visualModel']['description']}",
            "layers": diagram_layers,
            "annotations": [item["name"] for item in book_core["coreConcepts"]],
        },
        "tags": ["职场表达", "汇报", "PPT", "方案", "AI提效"] if pyramid else ["管理", "复盘", "决策", "组织透明", "AI提效"] if principles else ["读书方法", "AI Skill", "知识视频"],
    }


def principles_scenes(input_data: dict, book_core: dict) -> list[dict]:
    durations = [28, 36, 42, 38, 40, 38, 36, 40]
    target = input_data["targetDurationSec"]
    if sum(durations) > target:
        ratio = target / sum(durations)
        durations = [max(18, int(item * ratio)) for item in durations]
        durations[-1] += target - sum(durations)
    names = [
        ("S01", "现实痛点", "intro_card", "problem", "用复盘问题切入：为什么同类错误反复出现。", "一张项目复盘桌面，便签、红色问题标记、打开的笔记本和一杯咖啡，成年人职场知识视频风格"),
        ("S02", "书籍核心内涵", "book_author_context", "book_core", "说明《原则》不是观点合集，而是操作系统。", "一本深色精装商业书放在办公桌上，旁边有非可识别成熟投资人剪影照片、作者研究资料、金融图表和铅笔，参考《Principles》黑色商业书封气质，但不复刻真实封面，不出现可识别人物肖像"),
        ("S03", "原则反馈环", "flywheel_model", "core_model", "展示目标、现实、根因、原则、执行的循环。", "抽象反馈飞轮，目标、现实、根因、原则、执行五个节点用图形表达，商业信息图插画"),
        ("S04", "极度求真与透明", "transparent_meeting", "sop", "把事实和分歧摆到台面，减少组织黑箱。", "现代透明会议室，白板上有事实卡片和不同观点线索，团队讨论但人物不露脸"),
        ("S05", "创意择优决策", "decision_matrix", "sop", "说明可信度加权如何让最好想法胜出。", "决策桌面俯视图，方案卡片、评分矩阵、可信度权重刻度，理性商业插画"),
        ("S06", "AI Skill转化", "ai_workflow", "ai_skill", "把复盘材料转成可复用的原则条目。", "AI 工作流界面概念图，输入会议纪要和失败记录，输出原则卡片和行动清单，现代产品插画"),
        ("S07", "真实场景", "project_recovery", "use_cases", "展示项目失败如何沉淀成下一次行动规则。", "项目延期复盘场景，甘特图、风险看板、原则手册被打开，暖白办公室插画"),
        ("S08", "总结CTA", "principles_system", "summary", "用一句话收束，并引导收藏。", "一本原创原则手册、循环箭头和成长阶梯，收藏感强的小红书知识封面风格"),
    ]
    narrations = [
        "很多人复盘时只会问，这次哪里做错了。但如果没有沉淀成原则，同类错误下次还会回来。",
        "《原则》真正有价值的地方，不是几句管理金句，而是一套把现实、分歧和经验转成行动规则的操作系统。",
        "它的核心可以看成一个反馈环：写清目标，面对现实，诊断根因，沉淀原则，再用执行结果继续修正原则。",
        "第一层能力是极度求真和极度透明。看清现实比维护面子重要，让关键事实和分歧被看见，团队才不会在黑箱里决策。",
        "第二层能力是创意择优。不是谁职位高听谁，也不是谁声音大听谁，而是让更可信、更有经验、更能解释判断的人获得更高权重。",
        f"所以它可以变成一个{book_core['aiSkillCandidate']['name']}。输入失败记录、会议纪要和分歧点，输出事实清单、根因判断、原则条目和下一步行动。",
        "比如一次项目延期，不只写负责人是谁，而是追问目标是否清晰、信息是否透明、关键判断有没有可信反对意见，最后形成下次可执行的原则。",
        "总结一句：读《原则》，不是为了背原则，而是为了拥有一套持续进化的决策系统。收藏这条，下次复盘直接套用。",
    ]
    scenes: list[dict] = []
    for index, ((scene_id, title, visual_type, visual_role, goal, visual_seed), duration, narration) in enumerate(zip(names, durations, narrations)):
        scenes.append(
            {
                "sceneId": scene_id,
                "title": title,
                "durationSec": duration,
                "goal": goal,
                "visualType": visual_type,
                "visualRole": visual_role,
                "recommendedVisualMode": "motion_graphics" if visual_role in {"core_model", "sop"} else "style_frame_image_to_video",
                "visualDescription": f"暖白背景，橙色标题，深绿色辅助线，商业信息图风格。画面表达：{goal}",
                "imageSourceStrategy": {
                    "priority": ["imagegen", "component_renderer"],
                    "imageCount": 1,
                    "imagePrompt": (
                        "Use case: cinematic-book-analysis-scene\n"
                        "Asset type: vertical short-video scene illustration\n"
                        f"Primary request: {visual_seed}\n"
                        "Research anchors: Ray Dalio / Principles official visual context, black business book cover mood, mature investor/management context, Bridgewater-style transparent decision room, idea meritocracy, radical transparency\n"
                        "Style/medium: polished cinematic editorial business visual, realistic photo-illustration, Xiaohongshu knowledge-video frame\n"
                        "Composition/framing: 9:16 vertical, strong central visual area, foreground/midground/background depth, clean lower area for Chinese overlay text\n"
                        "Color palette: warm white background, orange primary accents, deep green secondary accents, black text-safe areas\n"
                        "Constraints: original illustration, no copyrighted book-cover imitation, no recognizable Ray Dalio portrait, no logos, no watermark, no long text in image"
                    ),
                    "fallbackPrompt": f"Component card for Principles scene: {title}",
                },
                "onscreenText": title,
                "subtitle": narration[:42],
                "narration": narration,
                "motion": "gentle structured reveal",
                "transitionIn": "fade" if index == 0 else "slide-left",
                "transitionOut": "soft-zoom" if index == len(names) - 1 else "fade",
                "musicCue": ["soft_intro", "main_steady", "main_steady", "main_steady", "main_steady", "slightly_uplifting", "slightly_uplifting", "gentle_ending"][index],
                "tts": {"voice": "default-zh-professional", "speed": 1.0, "emotion": "calm"},
            }
        )
    return scenes


def build_scenes(input_data: dict, book_core: dict) -> list[dict]:
    if is_principles(input_data["bookTitle"]):
        return principles_scenes(input_data, book_core)
    durations = [28, 36, 42, 42, 38, 38, 36]
    target = input_data["targetDurationSec"]
    if sum(durations) > target:
        ratio = target / sum(durations)
        durations = [max(18, int(item * ratio)) for item in durations]
        durations[-1] += target - sum(durations)
    names = [
        ("S01", "现实痛点", "intro_card", "hook", "抓住观众：为什么内容很多却讲不清。"),
        ("S02", "书籍核心内涵", "problem_diagram", "book_core", "提炼这本书真正解决的问题。"),
        ("S03", "结构模型", "pyramid_model", "core_model", "展示核心视觉模型。"),
        ("S04", "SOP方法", "sop_card", "sop", "把方法拆成可执行步骤。"),
        ("S05", "AI Skill转化", "workflow", "ai_skill", "说明如何把方法封装成 AI Skill。"),
        ("S06", "真实场景", "workflow", "use_cases", "展示职场材料如何被转成结构化汇报。"),
        ("S07", "总结CTA", "summary_card", "summary", "用一句话收束，并引导收藏。"),
    ]
    narrations = [
        "你有没有发现，材料越多，汇报反而越容易讲乱？问题常常不是信息不够，而是结构不清。",
        f"《{book_core['bookTitle']}》真正有价值的地方，是把复杂信息变成层级清楚的表达结构。",
        f"核心模型是{book_core['visualModel']['name']}。上面是结论，中间是理由，下面是事实和案例。",
        "把它变成动作，只要四步：先写结论，拆出理由，归类分组，再放入证据。",
        f"这就可以封装成一个{book_core['aiSkillCandidate']['name']}，输入原始材料，输出结论、理由、证据和大纲。",
        "比如一份杂乱会议纪要，先提炼判断，再按主题分组，最后补足每组证据，就能变成清晰汇报。",
        "所以，读书不是背观点，而是把观点变成能力。收藏这条，下次汇报前直接套用。",
    ]
    scenes: list[dict] = []
    for index, ((scene_id, title, visual_type, visual_role, goal), duration, narration) in enumerate(zip(names, durations, narrations)):
        scenes.append(
            {
                "sceneId": scene_id,
                "title": title,
                "durationSec": duration,
                "goal": goal,
                "visualType": visual_type,
                "visualRole": visual_role,
                "recommendedVisualMode": "motion_graphics" if visual_role in {"core_model", "sop"} else "style_frame_image_to_video",
                "visualDescription": f"暖白背景，橙色标题，绿色辅助线，商业信息图风格。画面表达：{goal}",
                "imageSourceStrategy": {
                    "priority": ["imagegen", "component_renderer"],
                    "imageCount": 1,
                    "imagePrompt": f"{title}，商业知识信息图，橙色主色，绿色辅助，暖白背景，中文文字由渲染器叠加",
                    "fallbackPrompt": f"SVG component card for {title}",
                },
                "onscreenText": title,
                "subtitle": narration[:42],
                "narration": narration,
                "motion": "gentle structured reveal",
                "transitionIn": "fade" if index == 0 else "slide-left",
                "transitionOut": "soft-zoom" if index == len(names) - 1 else "fade",
                "musicCue": ["soft_intro", "main_steady", "main_steady", "main_steady", "slightly_uplifting", "slightly_uplifting", "gentle_ending"][index],
                "tts": {"voice": "default-zh-professional", "speed": 1.0, "emotion": "calm"},
            }
        )
    return scenes


def write_markdown_outputs(output_dir: Path, input_data: dict, book_core: dict, storyboard: dict) -> None:
    output_dir.joinpath("video_brief.md").write_text(
        "\n".join(
            [
                f"# {storyboard['videoTitle']}",
                "",
                f"- 书名：{book_core['bookTitle']}",
                f"- 作者：{book_core.get('bookAuthor') or '未确认'}",
                f"- 核心问题：{book_core['videoCoreQuestion']}",
                f"- 核心观点：{book_core['coreClaim']}",
                f"- 平台：{input_data['targetPlatform']}",
                f"- 时长：{storyboard['targetDurationSec']} 秒以内",
                f"- 系列定位：一本书，一个AI Skill",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    narration_lines = [f"# {storyboard['videoTitle']} 讲解词", ""]
    for scene in storyboard["scenes"]:
        narration_lines.extend([f"## {scene['sceneId']} {scene['title']}", scene["narration"], ""])
    output_dir.joinpath("narration_script.md").write_text("\n".join(narration_lines), encoding="utf-8")
    if is_principles(book_core["bookTitle"]):
        publish_lines = [
            f"# {storyboard['videoTitle']}",
            "",
            "复盘不是写检讨，而是把错误、分歧和经验沉淀成下一次可执行的原则。",
            "",
            f"这条视频把《{book_core['bookTitle']}》拆成一个可执行的 AI Skill：{book_core['aiSkillCandidate']['name']}。",
            "",
            "适合用来处理项目复盘、决策分歧、会议纪要和团队机制建设。",
            "",
            "#原则 #RayDalio #读书方法 #管理复盘 #AI提效",
        ]
    else:
        publish_lines = [
            f"# {storyboard['videoTitle']}",
            "",
            "为什么你明明准备了很多材料，汇报时还是讲不清？",
            "",
            f"这条视频把《{book_core['bookTitle']}》拆成一个可执行的 AI Skill：{book_core['aiSkillCandidate']['name']}。",
            "",
            "你可以直接用它处理会议纪要、项目材料、客户需求和原始PPT。",
            "",
            "#职场表达 #读书方法 #AI提效 #PPT #汇报",
        ]
    output_dir.joinpath("xiaohongshu_publish.md").write_text("\n".join(publish_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Input JSON file")
    parser.add_argument("--book", help="Book title")
    parser.add_argument("--author", help="Book author")
    parser.add_argument("--output-dir", help="Project output directory")
    args = parser.parse_args()

    raw = load_input(args.input)
    if args.book:
        raw["bookTitle"] = args.book
    if args.author:
        raw["bookAuthor"] = args.author
    input_data = normalize_input(raw)

    output_dir = Path(args.output_dir or Path("output") / slugify_book(input_data["bookTitle"]))
    output_dir.mkdir(parents=True, exist_ok=True)

    if is_pyramid_principle(input_data["bookTitle"]):
        book_core = pyramid_book_core(input_data["bookTitle"], input_data.get("bookAuthor"))
        book_research = generic_book_research(input_data)
    elif is_principles(input_data["bookTitle"]):
        book_core = principles_book_core(input_data["bookTitle"], input_data.get("bookAuthor"))
        book_research = principles_book_research(input_data["bookTitle"], input_data.get("bookAuthor"))
    else:
        book_core = generic_book_core(input_data)
        book_research = generic_book_research(input_data)
    bible = style_bible(input_data, output_dir)
    poster_plan = cover_plan(input_data, book_core)
    scenes = build_scenes(input_data, book_core)
    storyboard = {
        "projectName": project_name(input_data["bookTitle"]),
        "bookTitle": input_data["bookTitle"],
        "videoTitle": f"5分钟把《{input_data['bookTitle']}》变成一个AI Skill",
        "coreProblem": book_core["coreProblem"],
        "coreClaim": book_core["coreClaim"],
        "targetAudience": input_data["targetAudience"],
        "targetDurationSec": sum(scene["durationSec"] for scene in scenes),
        "durationLimitSec": input_data["durationLimitSec"],
        "scenes": scenes,
    }

    write_json(output_dir / "input.normalized.json", input_data)
    write_json(output_dir / "book_research.json", book_research)
    write_json(output_dir / "book_core.json", book_core)
    write_json(output_dir / "style_bible.json", bible)
    write_json(output_dir / "cover_poster_plan.json", poster_plan)
    write_json(output_dir / "storyboard.json", storyboard)
    write_markdown_outputs(output_dir, input_data, book_core, storyboard)

    print(f"storyboard_project: {output_dir}")
    print(f"scenes: {len(scenes)}")
    print(f"duration_sec: {storyboard['targetDurationSec']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
