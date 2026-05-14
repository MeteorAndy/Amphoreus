## 1. System Prompt — Forbidden Markers

- [ ] 1.1 Add forbidden-rules section to ZH/EN screenplay prompts: no `#` headings, no `---` separators, no scene-end markers
- [ ] 1.2 Add rule: "代码已自动添加幕标题和场次编号，你只需输出场景内容本身"
- [ ] 1.3 Add character name format rule: ZH no bold, EN ALL CAPS

## 2. Scene Log — Inner Thought Injection

- [ ] 2.1 Change `_format_scene_log()` to output `[内心] 角色名心想：xxx` instead of bare `Thinks: xxx`
- [ ] 2.2 Add prompt rule: "将 [内心] 标记转化为（旁白）、（OS）、画外音或括弧动作指示"

## 3. PostProcessor — Format Sanitization

- [ ] 3.1 Add `_sanitize_screenplay_content()` — remove leaked `#` headings, standalone `---` lines
- [ ] 3.2 Add scene-end marker removal — regex for `（第X幕·场景X完）` patterns
- [ ] 3.3 Add `**bold**` removal for character names in ZH mode
- [ ] 3.4 Apply sanitization in `normalize_screenplay()` before assembly

## 4. Assembly — Empty Act Fix

- [ ] 4.1 In `_assemble_screenplay()`, skip acts that have zero scene content

## 5. Verification

- [ ] 5.1 Run Chinese screenplay test — verify: no `#` headings in scene content, no `---`, no end markers, no `**bold**` names, no empty acts, inner thoughts visible as (OS) or 内心
- [ ] 5.2 Run English screenplay test — same checks in EN
