---
deck_id: huixin_training_enablement
kind: deck
summary: 慧新企业培训、产品培训、销售赋能、实施交付培训、客户培训和内部学习材料模板.
canvas_format: ppt169
page_count: 10
primary_color: "#4295B6"
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
| **Logo Blue** | `#4295B6` | Course identity, module headers, learning path, key concept blocks |
| **Logo Green** | `#B0D776` | Practice tasks, checkpoints, completion markers, tips and calls to action |
| **Logo Gray** | `#D2D3D4` | Dividers, neutral cards, answer zones, timeline rails |
| **Deep Blue Gray** | `#0B2F3A` | Cover, titles, key summaries, contrast panels |
| **Text Gray** | `#4B5563` | Body text, captions, facilitator notes |
| **Light Blue Gray** | `#F3F7FA` | Page background, learning panels, content modules |
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

**Primary Font**: `"Microsoft YaHei"`

**SVG Font**: `"Microsoft YaHei"` — all SVG text uses Microsoft YaHei / 微软雅黑 as the single design font.

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
| **Course Header** | Thin blue top rule, module number, top-right Huixin lockup |
| **Title Zone** | Page title plus one training objective or key message |
| **Learning Body** | Objectives, pathways, frameworks, explanations, exercises, quizzes, reflection and action plans |
| **Footer** | Course name, duration / facilitator placeholder, page number |

### Design DNA

1. Make every page teachable: one goal, one structure, one learner action.
2. Use blue for concepts and system structure; green for tips, practice, checks, and completion.
3. Use white and light blue-gray backgrounds for readability in classrooms and online training.
4. Use concise placeholders and modular blocks so instructors can swap course content quickly.
5. Avoid childish icons, excessive decoration, glow effects, and marketing slogans.

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

## IX. Layout Modes

| Mode | Recommendation |
| --- | --- |
| **Product Training** | Use framework, concept, process, case, quiz, action pages |
| **Sales Enablement** | Use objectives, journey, concept, case, workshop, action pages |
| **Internal Workshop** | Use objectives, workshop, quiz, action pages with stronger green checkpoint blocks |
| **Customer Training** | Keep explanations concise and add process walkthrough pages for operation steps |

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
| `{{PAGE_NUM}}` | Page number |

## XIII. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated enterprise training journey reference | Optional reference only. Do not paste it as fixed slide content; use it to guide future project-specific courseware visuals. Learning objectives, journey maps, frameworks, practice tasks, quizzes, and action plans remain editable SVG elements. |
