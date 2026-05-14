## 1. Title Generator

- [ ] 1.1 Implement `TitleGenerator` class — LLM generates 3-5 title candidates from world summary + character summaries + plot outline
- [ ] 1.2 Implement ZH/EN title generation prompts (ZH: 金庸/古龙/网络文学风格, EN: literary/suspense/direct)
- [ ] 1.3 Integrate title selection into the convert() flow (return candidates, accept user choice)

## 2. Chapter Planner

- [ ] 2.1 Implement `ChapterPlanner` class — LLM plans scene→chapter mapping from PlotOutline + scene list
- [ ] 2.2 Implement ZH/EN chapter planning prompts — ZH: "第X章 篇名"（不用"第X回"）, EN: "Chapter X: Title"
- [ ] 2.3 Implement word count targeting: ZH 2500-4000字/章, EN 2000-3500词/章, short story fallback 800-1500字
- [ ] 2.4 Implement single-scene/short-story fallback (short story mode — fewer words OK)

## 3. Per-Chapter Writing

- [ ] 3.1 Replace scene-by-scene conversion with chapter-by-chapter LLM calls
- [ ] 3.2 Implement chapter writing prompt following the provided reference structure:
  - Step 1: LLM reviews the chapter plan as a reader, identifies improvement areas (in `<思考>` tag)
  - Step 2: LLM writes full chapter prose (in `<story>` tag)
  - Requirements: vivid language, character depth, pacing control, scene transitions
- [ ] 3.3 Build chapter context assembler — per chapter: chapter title + summary + all scene logs + adjacent chapter summaries
- [ ] 3.4 Implement scene transition bridging (LLM writes transitional paragraphs between scenes within a chapter)

## 4. Post-Processing

- [ ] 4.1 Implement ZH text normalization: 中文引号标准化、省略号规范化(……)、破折号(——)、段落间距
- [ ] 4.2 Implement EN text normalization per English conventions
- [ ] 4.3 Apply post-processing after chapter prose generation and before assembly

## 5. Assembly & i18n

- [ ] 5.1 Rewrite `_assemble_novel()` — use LLM-generated title + chapter titles, remove all hardcoded English
- [ ] 5.2 Rewrite screenplay assembly — ZH: `[内景]/[外景]` scene headings, EN: `[INT.]/[EXT.]`
- [ ] 5.3 Add i18n entries for all residual static text (default title, screenplay header)
- [ ] 5.4 Ensure export filenames use generated title (not "Generated Narrative")

## 6. CLI Integration

- [ ] 6.1 Update CLI narrative writing step to show title candidates and accept user selection
- [ ] 6.2 Display chapter plan before writing
- [ ] 6.3 Show per-chapter writing progress

## 7. Verification

- [ ] 7.1 Run Chinese pipeline test — verify: Chinese title, Chinese chapter headings, no English labels, quality prose
- [ ] 7.2 Run English pipeline test — verify: English title, English chapter headings, no Chinese labels
- [ ] 7.3 Verify single-scene fallback (short story) works in both languages
