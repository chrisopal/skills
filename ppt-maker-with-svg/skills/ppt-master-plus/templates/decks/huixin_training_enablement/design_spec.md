---
deck_id: huixin_training_enablement
kind: deck
summary: 慧新企业培训、产品培训、销售赋能、实施交付培训、客户培训和内部学习材料模板；包含课程主线、章节、日程、课前准备、场景导入、界面讲解、对比矩阵、角色演练、SOP、测评结果和FAQ排查页.
canvas_format: ppt169
canvas_width: 1280
canvas_height: 720
canvas_viewbox: "0 0 1280 720"
native_structure_mode: legacy-flat
replication_mode: standard
page_count: 20
primary_color: "#0097BA"
keywords: [huixin, training, enablement, courseware, workshop]
---

# Huixin Training Enablement - Design Specification

## I. Template Overview

| Property | Description |
| --- | --- |
| **Template Name** | huixin_training_enablement |
| **Display Name** | 慧新培训赋能模板 |
| **Use Cases** | 企业内训、产品培训、销售赋能、实施交付培训、客户培训、新员工学习、专题工作坊 |
| **Design Tone** | Clear, guided, practical, interactive, enterprise-grade learning |
| **Theme Mode** | Light learning courseware theme based on Huixin logo colors |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| **Format** | Standard 16:9 |
| **Dimensions** | 1280 x 720 px |
| **viewBox** | `0 0 1280 720` |
| **Safe Margins** | 64px left/right, 44px top, 40px bottom |
| **Primary Content Area** | x: 72-1208, y: 128-642 |

## III. Color Scheme

| Role | Color Value | Usage |
| --- | --- | --- |
| **Logo Blue** | `#0097BA` | Course identity, module headers, learning path, key concept blocks |
| **Logo Green** | `#A4D968` | Practice tasks, checkpoints, completion markers, tips and calls to action |
| **Brand Chrome Green** | `#83C410` | Official lockup geometry, fixed double-bar cue, footer ribbon only |
| **Logo Gray** | `#D9D9D9` | Dividers, neutral cards, answer zones, timeline rails |
| **Deep Blue Gray** | `#111111` | Cover, titles, key summaries, contrast panels |
| **Industrial Blue** | `#0B1039` | Dark-page background and industry foundation |
| **Intelligent Blue** | `#044AAA` | Core modules and primary dark-page structure |
| **Bright Blue** | `#1AB6ED` | Dark-page section and content emphasis |
| **Pale Blue** | `#C0DCEF` | Dark-page strategy title, support copy, divider |
| **Text Gray** | `#4B5563` | Body text, captions, facilitator notes |
| **Light Blue Gray** | `#F5F6F7` | Page background, learning panels, content modules |
| **White** | `#FFFFFF` | Main canvas and card surfaces |
| **Wordmark Black** | `#000000` | Official Huixin wordmark on light backgrounds |

## IV. Typography System

| Level | Usage | Size | Weight |
| --- | --- | --- | --- |
| **H1** | Cover course title | 54-60px | Bold |
| **H2** | Page title | 34-40px | Bold |
| **H3** | Module / activity title | 20-26px | Bold |
| **Body** | Training explanation | 14-17px | Regular |
| **Caption** | Duration / role / hint | 11-13px | Regular |
| **Step Number** | Learning steps and tasks | 34-46px | Bold |

**Primary Font**: `"Microsoft YaHei, Arial, sans-serif"`

**SVG Font**: `"Microsoft YaHei, Arial, sans-serif"` — use Microsoft YaHei with Arial fallback.

### Huixin Visual Baseline 0826

This Deck follows the official `慧新全智PPT视觉设计规范0826.pptx`
(source SHA-256:
`44539c09286ac6b3fd87898afd0124851439c0817a07f40f3da7041f32a7ff06`).
Use `#0097BA` for the technology/system spine, `#A4D968` for semantic
value/improvement, `#4B5563` for body hierarchy, and `#D9D9D9` for fine
structure. Keep official logo-derived chrome green `#83C410` limited to the
lockup, double-bar header cue, and fixed ribbon geometry.

Primary typography is `Microsoft YaHei, Arial, sans-serif`; do not lead with
MiSans or PingFang. Light pages preserve at least 70% white/light-gray surface,
use the compact top-left double vertical rule, and keep page titles in the
20-28pt band with 12-18pt body copy and chart/table labels at or above 9pt when
content density permits. Covers and endings use the 0826 industrial mosaic.
Dark pages use `#0B1039`, `#044AAA`, `#1AB6ED`, and `#C0DCEF` with the white
Huixin lockup. The complete shared authority is
[`../huixin_visual_system_0826.md`](../huixin_visual_system_0826.md).


## V. Logo and Brand Mark

| Asset | Description |
| --- | --- |
| **Official Huixin Lockup** | Embedded from the official Huixin logo assets: use the light logo on white or light backgrounds and the dark-background logo with white wordmark on deep color fields. |

Usage rules:

1. Use the full lockup on cover and working pages.
2. Keep the mark compact on instructional pages so the learning content remains primary.
3. Use the logo's slanted geometry as a quiet learning path / module tab motif.

## VI. Page Structure

### Common Layout

| Area | Description |
| --- | --- |
| **Course Header** | Compact green/blue double vertical rule, module number, left-aligned title, top-right Huixin lockup |
| **Title Zone** | Page title plus one training objective or key message |
| **Learning Body** | Objectives, pathways, frameworks, explanations, exercises, quizzes, reflection and action plans |
| **Footer** | Course name, duration / facilitator placeholder, page number |

### Design DNA

1. Make every page teachable: one goal, one structure, one learner action.
2. Use blue for concepts and system structure; green for tips, practice, checks, and completion.
3. Use white and light blue-gray backgrounds for readability in classrooms and online training.
4. Use concise placeholders and modular blocks so instructors can swap course content quickly.
5. Avoid childish icons, excessive decoration, glow effects, and marketing slogans.

### Template Adaptation Rules

1. Prefer the reusable SVG page type / master when it matches the learning objective, content granularity, and classroom activity.
2. If the real course content needs a different instructional structure, derive a custom page rather than forcing the lesson into an unsuitable base page.
3. Custom pages must preserve Huixin's palette, white / light blue-gray background style, top-right logo discipline, slanted-bar brand geometry, and the training narrative of objective -> concept -> example -> practice -> check -> action.
4. Do not remove necessary learner context, practice instructions, quiz evidence, or action planning only to fit a predefined template layout.

## VII. Page Types

### 1. Cover Page (`01_cover.svg`)
- Course title, training audience, facilitator, date, and course promise.

### 2. Course Objectives (`02_course_objectives.svg`)
- Learning goals, expected outcomes, target audience, and session rules.

### 3. Learning Journey (`03_learning_journey.svg`)
- A guided path from introduction to practice, assessment, and follow-up action.

### 4. Knowledge Framework (`04_knowledge_framework.svg`)
- Structured concept map for the training topic.

### 5. Concept Explanation (`05_concept_explanation.svg`)
- One key concept with definition, example, caution, and takeaway.

### 6. Process Walkthrough (`06_process_walkthrough.svg`)
- Step-by-step workflow or product operation walkthrough.

### 7. Case Practice (`07_case_practice.svg`)
- Scenario, task, evidence, and discussion prompt for case-based learning.

### 8. Workshop Task (`08_workshop_task.svg`)
- Group exercise card with input, output, roles, and timebox.

### 9. Quiz and Review (`09_quiz_review.svg`)
- Quiz question set, answer zone, and knowledge recap.

### 10. Action Plan (`10_action_plan.svg`)
- Post-training action plan, commitment checklist, and next learning resources.

### 11. Module Divider (`11_module_divider.svg`)
- Chapter divider for multi-module courses, with module goal and rhythm preview.

### 12. Training Agenda Timebox (`12_training_agenda_timebox.svg`)
- Course agenda, time allocation, delivery format, and expected output table.

### 13. Prerequisite Check (`13_prerequisite_check.svg`)
- Learner persona, pre-class preparation checklist, and baseline readiness check.

### 14. Scenario Context (`14_scenario_context.svg`)
- Business scenario setup, role context, pain point, decision point, and practice goal.

### 15. UI Operation Annotation (`15_ui_operation_annotation.svg`)
- Product interface or system operation explanation with editable screenshot placeholder and numbered callouts.

### 16. Comparison Matrix (`16_comparison_matrix.svg`)
- Correct-versus-wrong, option A/B, or method comparison page with decision rule.

### 17. Roleplay Script (`17_roleplay_script.svg`)
- Sales enablement, customer communication, objection handling, and role-play practice script.

### 18. SOP Checklist (`18_sop_checklist.svg`)
- Implementation, delivery, operation, or service checklist with standards and completion markers.

### 19. Assessment Results (`19_assessment_results.svg`)
- Training assessment, score summary, pass level, capability breakdown, and improvement advice.

### 20. FAQ Troubleshooting (`20_faq_troubleshooting.svg`)
- Common questions, answers, troubleshooting path, and escalation rule.

## VIII. SVG Page Roster

| File | Role | Description |
|------|------|-------------|
| `01_cover.svg` | cover | Training course cover and audience framing |
| `02_course_objectives.svg` | objectives | Goals, outcomes, audience, and learning rules |
| `03_learning_journey.svg` | journey | Module path and learning sequence |
| `04_knowledge_framework.svg` | framework | Concept map and knowledge architecture |
| `05_concept_explanation.svg` | concept | Definition, example, caution, takeaway |
| `06_process_walkthrough.svg` | process | Step-by-step workflow walkthrough |
| `07_case_practice.svg` | case | Scenario practice and discussion |
| `08_workshop_task.svg` | workshop | Group task and output card |
| `09_quiz_review.svg` | quiz | Quiz, answer zone, and recap |
| `10_action_plan.svg` | action | Personal or team action plan after training |
| `11_module_divider.svg` | divider | Module divider and chapter learning rhythm |
| `12_training_agenda_timebox.svg` | agenda | Course agenda, timebox, delivery mode, and output |
| `13_prerequisite_check.svg` | prerequisite | Learner persona, preparation checklist, and readiness baseline |
| `14_scenario_context.svg` | scenario | Business scenario setup and practice framing |
| `15_ui_operation_annotation.svg` | ui_annotation | Product UI or operation screenshot annotation |
| `16_comparison_matrix.svg` | comparison | Correct/wrong or option comparison with decision rule |
| `17_roleplay_script.svg` | roleplay | Sales or customer communication role-play script |
| `18_sop_checklist.svg` | sop | SOP checklist and completion standards |
| `19_assessment_results.svg` | assessment | Assessment result, pass level, and capability breakdown |
| `20_faq_troubleshooting.svg` | faq | FAQ and troubleshooting path |

## IX. Layout Modes

| Mode | Recommendation |
| --- | --- |
| **Product Training** | Use framework, concept, process, UI annotation, comparison, quiz, FAQ, action pages |
| **Sales Enablement** | Use objectives, journey, scenario, concept, roleplay, case, workshop, action pages |
| **Implementation Training** | Use agenda, prerequisite, process, SOP checklist, assessment, FAQ, action pages |
| **Internal Workshop** | Use objectives, workshop, comparison, quiz, assessment, action pages with stronger green checkpoint blocks |
| **Customer Training** | Keep explanations concise and add UI annotation, process walkthrough, FAQ, and action pages |

## X. Spacing Specification

| Property | Value |
| --- | --- |
| **Base Unit** | 8px |
| **Module Gap** | 24px |
| **Card Gap** | 18px |
| **Title to Body** | 32px |
| **Footer Offset** | 32px from bottom |

## XI. SVG Technical Constraints

1. `viewBox` must stay `0 0 1280 720`.
2. Use plain hex colors with `fill-opacity` / `stroke-opacity`; do not use `rgba()`.
3. Do not use `<style>`, `class`, `foreignObject`, `textPath`, animation tags, or external scripts.
4. Keep all placeholder text in `{{PLACEHOLDER}}` form.
5. Use the official embedded Huixin logo asset; keep course titles, module path, and progress markers editable in SVG.

## XII. Placeholder Specification

| Placeholder | Description |
| --- | --- |
| `{{TITLE}}` | Cover or page main title |
| `{{SUBTITLE}}` | Cover subtitle or page key message |
| `{{COURSE_TAG}}` | Course category label |
| `{{AUDIENCE}}` | Learner audience |
| `{{FACILITATOR}}` | Facilitator / instructor |
| `{{DATE}}` | Training date |
| `{{MODULE_N}}` | Module or chapter label |
| `{{OBJECTIVE_N}}` | Learning objective |
| `{{OUTCOME_N}}` | Expected outcome |
| `{{STEP_N}}` | Process step name |
| `{{TASK_N}}` | Practice task |
| `{{QUESTION_N}}` | Quiz or reflection question |
| `{{ACTION_N}}` | Post-training action item |
| `{{MODULE_TITLE}}` | Module divider title |
| `{{MODULE_GOAL}}` | Module learning goal |
| `{{TIME_N}}` | Agenda time slot |
| `{{AGENDA_TOPIC_N}}` | Agenda topic |
| `{{AGENDA_MODE_N}}` | Agenda delivery format |
| `{{AGENDA_OUTPUT_N}}` | Agenda expected output |
| `{{LEARNER_PERSONA_N}}` | Target learner persona |
| `{{PREP_ITEM_N}}` | Pre-class preparation checklist item |
| `{{BASELINE_N}}` | Learner baseline skill item |
| `{{SCENARIO_BACKGROUND}}` | Scenario background |
| `{{PAIN_POINT}}` | Scenario pain point |
| `{{PRACTICE_GOAL}}` | Practice goal derived from the scenario |
| `{{SCREEN_NAME}}` | Product UI or operation screen name |
| `{{ANNOTATION_N}}` | UI callout explanation |
| `{{OPTION_A_TITLE}}` | Comparison left-side option title |
| `{{OPTION_B_TITLE}}` | Comparison right-side option title |
| `{{DECISION_RULE}}` | Comparison decision rule |
| `{{ROLE_A}}` | Role-play participant A |
| `{{ROLE_B}}` | Role-play participant B |
| `{{SCRIPT_LINE_N}}` | Role-play script line |
| `{{SOP_STEP_N}}` | SOP step name |
| `{{SOP_STANDARD_N}}` | SOP completion standard |
| `{{SCORE}}` | Assessment score |
| `{{PASS_LEVEL}}` | Assessment pass level |
| `{{FAQ_N}}` | FAQ question |
| `{{ANSWER_N}}` | FAQ answer |
| `{{TROUBLE_STEP_N}}` | Troubleshooting step |
| `{{PAGE_NUM}}` | Page number |

## XIII. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated enterprise training journey reference | Optional reference only. Do not paste it as fixed slide content; use it to guide future project-specific courseware visuals. Learning objectives, journey maps, frameworks, practice tasks, quizzes, and action plans remain editable SVG elements. |
| `images/huixin_logo_light.png` | Latest official Huixin Quanzhi horizontal lockup for light surfaces | Use on white and light-gray pages; preserve the complete lockup and do not recreate it. |
| `images/huixin_logo_dark.png` | Official white Huixin Quanzhi lockup for dark surfaces | Use directly on the 0826 industrial-blue background without a white backing card. |
| `images/huixin_light_cover_mosaic.png` | Official 0826 industrial mosaic | Use for covers and image-led endings while keeping titles editable in the quiet left region. |
| `images/huixin_light_content_bg.png` | Official subtle light geometric background | Use on agenda and knowledge overview pages. |
| `images/huixin_light_chapter_bg.png` | Legacy teal chapter background | Retained for compatibility only; new 0826 chapter pages use the industrial-blue background. |
| `images/huixin_dark_bg.png` | Official 0826 industrial-blue dark surface | Use for section dividers, dark strategy pages, and restrained executive emphasis. |
| `images/huixin_light_footer_ribbon.png` | Official blue-green footer ribbon | Use on standard instructional pages with the lower-left logo. |
