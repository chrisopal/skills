# 可替换的生成提示词

替换模板中的方括号字段，并删除不适用的句子后再提交。精确中文原文不翻译；可用英文描述画面与编辑意图。若用户提供自己的完整提示词，以其意图为准。

## 无文字插图

```text
Produce a standalone illustration for [TOPIC], aspect ratio [RATIO].
Reference roles: [IMAGE ROLE MANIFEST: style reference / subject reference / edit target].
Use warm beige antique Chinese book paper, simple ink-black contours and sparse engraving strokes, flat simplified faces and indigo clothing areas, restrained vermilion accents. Preserve the subject's period, recognizable characters and key props from the subject reference. Style-only references contribute paper, ink, texture and visual rhythm, not their text, characters or story objects.

Scene: [ONE CLEAR SCENE SENTENCE].
Composition: [SINGLE SCENE / LIFE SEQUENCE / TWO PARALLEL REGISTERS / OTHER].
Required figures and props: [EXPLICIT SUBJECT LIST AND COUNTS IF KNOWN].
Narrative relationships: [KEY RELATIONSHIP / SEQUENCE / INTERSECTION TO PRESERVE].
Keep complete crowns, heads, hands, important props and feet inside the frame, with generous paper margins.
[IF APPLICABLE: The repeated character depicts the same person's different ages, not unrelated people.]
[IF APPLICABLE: Muted red lacquer is confined to the inset screen panels.]
Convey correspondence through placement and depicted events; no lines, wires or antennae attached to a person's head.

No text, letters, numbers, readable seals, labels, logos or watermarks. No glossy 3D, modern anime, photorealistic costume-drama lighting or device/book mockups. [OPAQUE PAPER BACKGROUND / TRANSPARENT BACKGROUND IF REQUESTED]. Deliver the illustration itself.
```

## 带字封面

```text
Create a finished [RATIO] historical illustrated-book cover for [TOPIC].
Reference roles: [STYLE REFERENCE], [APPROVED SUBJECT ILLUSTRATION], [EDIT TARGET IF ANY].
Use pale warm ivory-beige paper matching the latest light-paper reference, very subtle grain, low brown/orange saturation, no dark mottling or vignette and a thin double ink-black border with approximately 5 percent safe inset. Ink-black Song/Ming editorial typography; one restrained vermilion seal. No dark full-page title plaque or gold headline. Style reference controls the shared editorial identity; the approved illustration supplies this story's characters and relationships.

Only the following EXACT Chinese text may appear:
Brand at upper left: '[BRAND]'
Small SQUARE seal immediately right of the upper-left brand: '[SEAL TEXT]'
Smaller subject line: '[SUBJECT LINE, OR OMIT]'
Dominant headline in [LINE COUNT] horizontal lines:
line 1 '[EXACT LINE 1]'
line 2 '[EXACT LINE 2, OR OMIT]'
[EXTRA LINE ONLY IF REQUIRED]
Bottom source attribution: '[SOURCE, OR OMIT IF NOT PROVIDED]'
Do not print quotation marks around those strings. No words omitted, duplicated, rewritten or added.

Reserve the upper-right corner (approximately 15 percent corner area) as empty paper; reserve the bottom-left 20 percent width by 10 percent height for platform overlays. Do not render platform UI.
The headline dominates the upper approximately 35–40 percent. Place the approved subject illustration large in the lower approximately 45–55 percent, with breathing room. Merge its surrounding beige paper with the page. Preserve [REQUIRED FIGURES, KEY PROPS, NARRATIVE RELATIONSHIPS], no crop of heads, crowns, hands, infants or feet. Do not redesign the characters or add head wires during cover composition. [THEME COLOR RULE IF APPLICABLE].
Use simplified flat figures with large indigo clothing areas, sparse fold lines and a clearly visible face for a single-person action scene. No photorealistic faces or dense etched shading. Keep walls, ground and paper margins light, with sparse background detail. Never add readable signage, calendar text or manuscript words outside the allowed strings.
No extra captions, unsupported dates, platform logo, watermark or device/book mockup. Output the cover itself.
```

## 局部修正

```text
Make one precise edit to the supplied image: [CHANGE ONLY THIS SPECIFIC DEFECT].
Keep [EXACT TEXT / SUBJECT IDENTITIES / COUNT / POSES / KEY PROPS / PAPER / PALETTE / FRAME / COMPOSITION] unchanged. Restore the background behind removed elements. Keep the same aspect ratio and complete image. No new words, objects or relationships.
```

文字错误时写出错误处与正确原文，并要求其他内容保持。插图异常时锁定已通过的其他人物与道具，避免整张重新解释。

## 仅背景调浅

```text
Edit only the paper and background tone of [EDIT TARGET]. Match [LATEST LIGHT-PAPER REFERENCE] for pale warm beige, even brightness and subtle grain. Reduce brown/orange saturation, mottling and dark vignette; also lighten background wall/ground fill. Keep black ink outlines, indigo clothing and vermilion accents crisp. Preserve every exact text string, font, position, figure, pose, prop and border. Do not import any text or platform UI from reference images. Keep the requested aspect ratio and export dimensions.
```
