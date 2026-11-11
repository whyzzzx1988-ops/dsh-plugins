---
name: dx-ai-video-autopilot
description: >-
  一句话生成「即梦效果」的 AI 产品宣传片：HyperFrames 动效版 + 真实 AI 镜头（千问 happyhorse / 即梦 Seedance / 百炼 Wan）混排，本地 ffmpeg 合成，低成本自动化出片。用户说「做一个 XX 的 AI 产品宣传片」「即梦效果短视频」「一句话出产品片」时使用。
user-invocable: true
---

# AI 视频混排自动化

一句话产出一条「AI 智能体/产品」宣传片：先用 HyperFrames 出纯动效版（零成本、可复跑），再用真实 AI 视频模型生成 1–3 个核心镜头替换/叠加，ffmpeg 本地混排合成，全程导演纪律 + 确定性验收。

## 何时触发

- 用户一句话要求生成 AI 产品 / 智能体 / 工具的宣传片、功能预告片、展示视频
- 用户提到「即梦效果」「电影感」「低成本自动化短视频」
- 复用场景：换产品主题，改稿不改管线

## 阶段顺序（必须按序，每步过闸）

1. **分诊**：确定时长（默认 10s）、画幅（默认 16:9）、音频（无配音默认 music:none）、叙事弧线（产品片用 Future Pacing：想象→命名→消除痛点→机制→成果→收束）。
2. **四维检索**：产品事实 / 用户问题 / 同类表达 / 视觉线索，每个维度不同关键词，至少 8 个去重来源 + 官方来源。无证据的说法明确舍弃，绝不虚构。
3. **固化文档**：依次写 RESEARCH.md（查询记录+来源表+三项结论）、BRIEF.md（用户原话/明确项/推断项/唯一主张/视觉关键词/禁止项）、frame.md（六色角色/字体/12 列网格/三层视觉/动效节奏）、STORYBOARD.md（Video direction 不变量 + 每帧相对时间分镜，总时长精确对齐）。
4. **写 HyperFrames 源码**：每帧一个子组合（`<template>` 内 style+markup+script，host data-composition-id == 内部 id == timeline key），index.html 用 data-composition-src 按绝对时间组装。
5. **质检闸**：`hyperframes lint` 与 `hyperframes check` 必须全绿（0 error / 0 warning）；禁 CDN（gsap 本地 vendor 化）；禁止 t=0 全堆的 PPT 式硬切。
6. **渲染动效版**：`hyperframes render --quality high`，ffprobe 验收（时长/分辨率/帧率/全帧解码 0 错误）。
7. **生成 AI 真实镜头**：选核心镜头（钩子/机制/成果）用视频模型生成。**优先顺序**：千问 happyhorse-1.1-t2v（Token Plan 兼容、1080p 带音频、已验证）→ 百炼 Wan → 即梦 Seedance（**注意：即梦 CLI 非会员会被「仅限会员使用」拦截，会员前不依赖它**）。
8. **ffmpeg 混排**：AI 镜头剪入动效版对应段（fps/scale/pad 归一化，基础版无音轨时对 AI 镜头段保留原生音频、后段补 anullsrc 静音），输出混排成片。
9. **验收 + 交付**：ffprobe 完整核验 + 抽帧像素核验（dominant colors 确认风格一致）；列出全部资产路径与后续建议。

## 用户改过 / 默认纪律

- 即梦 CLI 默认被会员拦截 → **不要默认依赖即梦**，先走千问 happyhorse（已验证 1080p 带音频），积分留给已开通的通道。
- gsap 必须本地 vendor（禁 CDN 引用）；字体用本地 @font-face（src: local()）。
- 无配音片：基础版 music:none + 无 SCRIPT；AI 镜头带原生音频时保留前段氛围音。
- 出图出视频参数：happyhorse t2v 用扁平 JSON（prompt/size/duration），size 形如 "1280*720"，不要套 model/input 外壳。

## 风格 / 镜头锁

- 深空近黑底 canvas #0a0e1a + 青色 primary #22d3ee + 靛 secondary #6366f1 + 琥珀 signal #f5b23c + 近白 ink + 灰蓝 muted。
- 玻璃拟态面板、节点连线、粒子流、计数上跳；power3.out 长尾缓动；关键动作是「光标驱动 + 节点点亮 + 数字证据」。
- 每镜一主一辅，t=0 只上一件与节拍对应的事。

## 版权纪律

- 点名 IP / 品牌 / 真人：先 directorx_ip_scan → 写属性化改写（不保留专名）→ directorx_ip_rewrite 验收通过后才可生成。
- 无授权真实 UI 截图不入画面，统一原创 SVG/CSS 表达；不宣称无证据的能力。

## 输出

- 动效版 + 混排成片各一个 MP4（1920×1080 / 30fps / H.264，验收通过）
- 生产文档 RESEARCH/BRIEF/frame/STORYBOARD 全部留档，便于下次复用改稿
