import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { orangePrimaryGreenSecondaryPreset } from '../config/stylePresets.js';
import { ensureDir, writeJson } from '../utils/file.js';
import { sumSceneDuration } from '../utils/duration.js';

export function isPyramidPrinciple(title) {
  return title.includes('金字塔原理') || title.toLowerCase().includes('pyramid principle');
}

export function slugifyBook(title) {
  if (isPyramidPrinciple(title)) return 'pyramid-principle';
  const ascii = title.trim().toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-|-$/g, '');
  if (ascii) return ascii;
  return `book-${Buffer.from(title).toString('hex').slice(0, 8)}`;
}

export function projectName(title) {
  return isPyramidPrinciple(title) ? 'Book2Video_ThePyramidPrinciple' : `Book2Video_${slugifyBook(title).replace(/-/g, '_')}`;
}

export class Book2StoryboardTool {
  async run(input, projectDir) {
    await ensureDir(projectDir);
    const bookCore = this.#buildBookCore(input);
    const styleBible = this.#buildStyleBible(input, projectDir);
    const coverPosterPlan = this.#buildCoverPosterPlan(input, bookCore);
    const scenes = this.#buildScenes(input, bookCore);
    const storyboard = {
      projectName: projectName(input.bookTitle),
      bookTitle: input.bookTitle,
      videoTitle: `5分钟把《${input.bookTitle}》变成一个AI Skill`,
      coreProblem: bookCore.coreProblem,
      coreClaim: bookCore.coreClaim,
      targetAudience: input.targetAudience,
      targetDurationSec: sumSceneDuration(scenes),
      durationLimitSec: input.durationLimitSec,
      scenes
    };

    await writeJson(path.join(projectDir, 'input.normalized.json'), input);
    await writeJson(path.join(projectDir, 'book_core.json'), bookCore);
    await writeJson(path.join(projectDir, 'style_bible.json'), styleBible);
    await writeJson(path.join(projectDir, 'cover_poster_plan.json'), coverPosterPlan);
    await writeJson(path.join(projectDir, 'storyboard.json'), storyboard);
    await this.#writeMarkdown(projectDir, input, bookCore, storyboard);

    return { bookCore, styleBible, coverPosterPlan, storyboard };
  }

  #buildBookCore(input) {
    if (!isPyramidPrinciple(input.bookTitle)) {
      return {
        bookTitle: input.bookTitle,
        bookAuthor: input.bookAuthor || null,
        coreProblem: '未确认：需要从书籍资料中确认这本书解决的现实问题。',
        videoCoreQuestion: '这本书最适合转成一个什么可执行方法？',
        coreClaim: '未确认：需要基于书籍摘要或 Book2Skill 输出提炼一句话核心观点。',
        coreConcepts: [
          { name: '核心概念A', explanation: '未确认：替换为书中的方法论结构。', usage: '说明适用场景。' },
          { name: '核心概念B', explanation: '未确认：替换为书中的方法论结构。', usage: '说明适用场景。' }
        ],
        visualModel: { name: '方法结构图', type: 'flow', description: '未确认：根据书籍方法论选择模型。', layers: [] },
        sop: [
          { step: 1, title: '定义输入', action: '明确使用者要提供的材料。', output: '输入清单' },
          { step: 2, title: '生成结构', action: '把核心概念转成步骤。', output: '方法步骤' },
          { step: 3, title: '形成产物', action: '把步骤封装成可复用模板。', output: '可执行模板' }
        ],
        aiSkillCandidate: {
          name: 'AI方法执行器',
          goal: '把书中的方法论转成可复用工作流。',
          input: ['书籍摘要', '用户场景', '原始材料'],
          output: ['结构化步骤', '执行模板', '结果检查表'],
          useCases: ['学习转化', '工作提效', '团队培训']
        }
      };
    }
    return {
      bookTitle: input.bookTitle,
      bookAuthor: input.bookAuthor || '芭芭拉·明托',
      coreProblem: '复杂信息很多，但汇报时听众抓不到结论、层级和证据关系。',
      videoCoreQuestion: '怎样把杂乱材料变成一套听得懂、记得住、能执行的汇报结构？',
      coreClaim: '先给结论，再用分组理由和证据层层支撑，表达才会清晰有力。',
      coreConcepts: [
        { name: '结论先行', explanation: '先说答案，再展开说明。', usage: '适合汇报、PPT、方案开头。' },
        { name: '以上统下', explanation: '上层概括下层，下层支撑上层。', usage: '适合构建清晰的汇报层级。' },
        { name: '归类分组', explanation: '同类信息放在一起，避免交叉重复。', usage: '适合整理材料、证据和分论点。' },
        { name: '逻辑递进', explanation: '组内按照时间顺序、结构顺序或重要性顺序展开。', usage: '适合让表达更顺畅、更有说服力。' }
      ],
      visualModel: {
        name: '金字塔结构',
        type: 'pyramid',
        description: '自上而下，层层支撑。',
        layers: [
          { name: '结论 / 核心观点', explanation: '先说结论，再展开理由。' },
          { name: '分论点 / 关键理由', explanation: '上层统领下层，下层支撑上层。' },
          { name: '事实 / 数据 / 案例', explanation: '用证据让结论站得住脚。' }
        ]
      },
      sop: [
        { step: 1, title: '先写一句话结论', action: '用一句话说明你最想让对方记住的判断。', output: '一句话结论' },
        { step: 2, title: '拆成 2-4 个关键理由', action: '找出支撑结论的关键分论点。', output: '分组理由' },
        { step: 3, title: '每组内容归类分组', action: '把同类证据放在同一组，避免交叉重复。', output: '分组结构' },
        { step: 4, title: '用事实、数据、案例支撑', action: '在每个理由下面放证据。', output: '证据清单' }
      ],
      aiSkillCandidate: {
        name: 'AI汇报结构生成器',
        goal: '把杂乱材料转成清晰的金字塔汇报结构。',
        input: ['会议纪要', '项目材料', '客户需求', '调研记录', '原始PPT'],
        output: ['一句话结论', '分组理由', '证据清单', 'PPT大纲', '讲解稿'],
        useCases: ['项目汇报', '售前方案', '复盘材料', '管理层简报']
      }
    };
  }

  #buildStyleBible(input, projectDir) {
    return {
      projectName: projectName(input.bookTitle),
      aspectRatio: input.aspectRatio,
      coverAspectRatio: input.coverAspectRatio,
      width: input.aspectRatio === '9:16' ? 1080 : 1920,
      height: input.aspectRatio === '9:16' ? 1920 : 1080,
      coverWidth: 1080,
      coverHeight: 1350,
      fps: 30,
      durationLimitSec: input.durationLimitSec,
      targetDurationSec: input.targetDurationSec,
      platform: input.targetPlatform,
      seriesLabel: '一本书，一个AI Skill',
      visualStyle: orangePrimaryGreenSecondaryPreset,
      audioStyle: {
        tts: { voice: 'default-zh-professional', speed: 1.0, emotion: 'calm' },
        bgm: { style: 'calm structured knowledge explainer', volume: 0.18, ducking: true }
      },
      ctaStyle: '收藏这条，把一本书变成一个可执行的AI Skill。',
      projectDir
    };
  }

  #buildCoverPosterPlan(input, bookCore) {
    return {
      projectName: projectName(input.bookTitle),
      aspectRatio: input.coverAspectRatio,
      title: `《${input.bookTitle}》拆书`,
      headline: isPyramidPrinciple(input.bookTitle) ? '为什么你总是讲不清？' : '把一本书变成一个AI Skill',
      subtitle: isPyramidPrinciple(input.bookTitle) ? '不是你没内容，而是你没结构' : '读书不是记住观点，而是把观点变成能力',
      badgeText: '一本书，一个AI Skill',
      footerText: '读书不是记住观点，而是把观点变成能力。',
      theme: input.stylePreset,
      layout: {
        header: 'large_title_problem_hook',
        leftModules: ['problem', 'core_concepts'],
        mainDiagram: isPyramidPrinciple(input.bookTitle) ? 'pyramid_plus_grouping_tree' : 'methodology_flow',
        bottomModules: ['expression_formula', 'ai_skill'],
        tags: ['职场表达', '汇报', 'PPT', '方案', 'AI提效']
      },
      mascot: {
        enabled: true,
        placement: 'top-right',
        style: {
          type: 'anthropomorphic_book',
          originality: 'required',
          tone: 'professional',
          characterRules: ['原创书籍人格化形象', '直立书本轮廓', '克制的表情', '橙色书签', '少量绿色叶片点缀'],
          forbiddenRules: ['不要夸张大眼睛', '不要儿童绘本风', '不要过度卡通', '不要抄袭已有吉祥物']
        },
        imagePrompt: '原创书籍人格化形象，直立书本轮廓，暖白书封，极简线条，克制表情，成熟友好，专业知识品牌风格，轻微教学手势，橙色书签，少量绿色叶片点缀，干净黑色线条，transparent background'
      },
      modules: [
        { id: 'problem', title: '这本书解决什么问题？', body: bookCore.coreProblem, icon: 'target' },
        { id: 'core_concepts', title: '核心内涵', body: bookCore.coreConcepts.map((item) => `${item.name}：${item.explanation}`), icon: 'lightbulb' },
        { id: 'expression_formula', title: '表达公式', body: bookCore.sop.map((item) => item.title), icon: 'flow' },
        { id: 'ai_skill', title: '可以变成什么AI Skill？', body: `${bookCore.aiSkillCandidate.name}：${bookCore.aiSkillCandidate.goal}`, icon: 'robot' }
      ],
      diagram: {
        type: bookCore.visualModel.type,
        title: `${bookCore.visualModel.name}：${bookCore.visualModel.description}`,
        layers: (bookCore.visualModel.layers || []).map((layer, index) => ({
          label: layer.name,
          description: layer.explanation,
          colorRole: index === 0 ? 'primary' : 'neutral'
        })),
        annotations: bookCore.coreConcepts.map((item) => item.name)
      },
      tags: ['职场表达', '汇报', 'PPT', '方案', 'AI提效']
    };
  }

  #buildScenes(input, bookCore) {
    const durations = [28, 36, 42, 42, 38, 38, 36];
    const names = [
      ['S01', '现实痛点', 'intro_card', '抓住观众：为什么内容很多却讲不清。'],
      ['S02', '书籍核心内涵', 'problem_diagram', '提炼这本书真正解决的问题。'],
      ['S03', '结构模型', 'pyramid_model', '展示核心视觉模型。'],
      ['S04', 'SOP方法', 'sop_card', '把方法拆成可执行步骤。'],
      ['S05', 'AI Skill转化', 'workflow', '说明如何把方法封装成 AI Skill。'],
      ['S06', '真实场景', 'workflow', '展示职场材料如何被转成结构化汇报。'],
      ['S07', '总结CTA', 'summary_card', '用一句话收束，并引导收藏。']
    ];
    const narrations = [
      '你有没有发现，材料越多，汇报反而越容易讲乱？问题常常不是信息不够，而是结构不清。',
      `《${bookCore.bookTitle}》真正有价值的地方，是把复杂信息变成层级清楚的表达结构。`,
      `核心模型是${bookCore.visualModel.name}。上面是结论，中间是理由，下面是事实和案例。`,
      '把它变成动作，只要四步：先写结论，拆出理由，归类分组，再放入证据。',
      `这就可以封装成一个${bookCore.aiSkillCandidate.name}，输入原始材料，输出结论、理由、证据和大纲。`,
      '比如一份杂乱会议纪要，先提炼判断，再按主题分组，最后补足每组证据，就能变成清晰汇报。',
      '所以，读书不是背观点，而是把观点变成能力。收藏这条，下次汇报前直接套用。'
    ];
    return names.map(([sceneId, title, visualType, goal], index) => ({
      sceneId,
      title,
      durationSec: durations[index],
      goal,
      visualType,
      visualDescription: `暖白背景，橙色标题，绿色辅助线，商业信息图风格。画面表达：${goal}`,
      imageSourceStrategy: {
        priority: ['codex_image_plugin', 'imagegen', 'none'],
        imageCount: 1,
        imagePrompt: `${title}，商业知识信息图，橙色主色，绿色辅助，暖白背景，中文文字由渲染器叠加`,
        fallbackPrompt: `SVG component card for ${title}`
      },
      onscreenText: title,
      subtitle: narrations[index].slice(0, 42),
      narration: narrations[index],
      motion: 'gentle structured reveal',
      transitionIn: index === 0 ? 'fade' : 'slide-left',
      transitionOut: index === names.length - 1 ? 'soft-zoom' : 'fade',
      musicCue: ['soft_intro', 'main_steady', 'main_steady', 'main_steady', 'slightly_uplifting', 'slightly_uplifting', 'gentle_ending'][index],
      tts: { voice: 'default-zh-professional', speed: 1.0, emotion: 'calm' }
    }));
  }

  async #writeMarkdown(projectDir, input, bookCore, storyboard) {
    await writeFile(
      path.join(projectDir, 'video_brief.md'),
      [
        `# ${storyboard.videoTitle}`,
        '',
        `- 书名：${bookCore.bookTitle}`,
        `- 作者：${bookCore.bookAuthor || '未确认'}`,
        `- 核心问题：${bookCore.videoCoreQuestion}`,
        `- 核心观点：${bookCore.coreClaim}`,
        `- 平台：${input.targetPlatform}`,
        `- 时长：${storyboard.targetDurationSec} 秒以内`,
        '- 系列定位：一本书，一个AI Skill',
        ''
      ].join('\n'),
      'utf8'
    );
    await writeFile(
      path.join(projectDir, 'narration_script.md'),
      [`# ${storyboard.videoTitle} 讲解词`, '', ...storyboard.scenes.flatMap((scene) => [`## ${scene.sceneId} ${scene.title}`, scene.narration, ''])].join('\n'),
      'utf8'
    );
    await writeFile(
      path.join(projectDir, 'xiaohongshu_publish.md'),
      [
        `# ${storyboard.videoTitle}`,
        '',
        '为什么你明明准备了很多材料，汇报时还是讲不清？',
        '',
        `这条视频把《${bookCore.bookTitle}》拆成一个可执行的 AI Skill：${bookCore.aiSkillCandidate.name}。`,
        '',
        '你可以直接用它处理会议纪要、项目材料、客户需求和原始PPT。',
        '',
        '#职场表达 #读书方法 #AI提效 #PPT #汇报',
        ''
      ].join('\n'),
      'utf8'
    );
  }
}
