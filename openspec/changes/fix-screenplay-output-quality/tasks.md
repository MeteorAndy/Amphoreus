## 1. Screenplay System Prompt

- [ ] 1.1 Rebuild screenplay system prompt with playwright role — LLM acts as professional screenwriter, first conceives character motivations/backstory/dialogue, then crafts suspenseful plot with twists
- [ ] 1.2 Implement ZH/EN dual prompts — ZH uses user's reference structure (先构思角色→再创作情节), EN equivalent
- [ ] 1.3 Add format constraints to prompt: scene heading format, character name preservation, scene numbering rules

## 2. Scene Numbering & Act Structure

- [ ] 2.1 Implement scene numbering — ZH "第X场", EN "Scene X" — applied during assembly, not by LLM
- [ ] 2.2 Implement act grouping using ChapterPlanner approach — group scenes into 3-4 acts with act titles
- [ ] 2.3 Single-act fallback for < 4 scenes

## 3. Format Standardization

- [ ] 3.1 Add scene heading normalization to PostProcessor — detect and unify `EXT.`/`内景.`/`[INT.]` variants
- [ ] 3.2 Add character name normalization — detect known character names converted to ALL CAPS English, restore original
- [ ] 3.3 ZH scene heading: `[内景]`/`[外景]` + 地点 + 时间, EN: `[INT.]`/`[EXT.]` + Location + Time

## 4. Assembly & i18n

- [ ] 4.1 Rewrite `_assemble_screenplay()` — use generated title, scene numbers, act headers
- [ ] 4.2 Remove hardcoded "剧本"/"SCREENPLAY" title
- [ ] 4.3 Add i18n entries for screenplay UI text
- [ ] 4.4 Export filename uses generated title

## 5. NarrativeWriter Facade

- [ ] 5.1 Update `_convert_screenplay()` to use new ScreenplayWriter with act structure
- [ ] 5.2 Ensure title candidates flow through screenplay path (reuse TitleGenerator)

## 6. CLI Integration

- [ ] 6.1 Update CLI screenplay path to show title candidates and act structure
- [ ] 6.2 Display scene-by-scene progress during screenplay generation

## 7. Verification

- [ ] 7.1 Run Chinese screenplay test — verify: Chinese title, `[内景]`/`[外景]` headings, scene numbers, no English labels, no ALL CAPS names
- [ ] 7.2 Run English screenplay test — verify: English title, `[INT.]`/`[EXT.]` headings, scene numbers
- [ ] 7.3 Verify format normalization works on mixed-format LLM output
