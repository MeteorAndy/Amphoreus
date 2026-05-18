## 1. LLM Error Classification

- [ ] 1.1 Add typed `LLMError` exception class with error codes (QUOTA_EXHAUSTED, RATE_LIMITED, NETWORK_ERROR, UNKNOWN)
- [ ] 1.2 Update `LLMClient.chat()` to catch and classify API errors, retry only transient errors
- [ ] 1.3 Update all pipeline stages to catch `LLMError` and save progress before propagating

## 2. Scene Streaming in CLI

- [ ] 2.1 Replace `run_scene()` with `run_scene_stream()` in `_scene_execution_pipeline`
- [ ] 2.2 Print each round's dialogue/action/emotion in real-time as stream events arrive
- [ ] 2.3 Save session after each scene completes

## 3. Granular Save Points

- [ ] 3.1 Extend `CliSession.last_step` with fine-grained step values
- [ ] 3.2 Save after: world build each round, character generation, relationship inference, plot generation, each completed scene, writing completion
- [ ] 3.3 Save scene archives to OpenViking after each scene for resume capability

## 4. Resume Logic

- [ ] 4.1 Implement `_resume_session()` that reads `last_step` and skips completed stages
- [ ] 4.2 Re-load world state, characters, plot outline, and completed scene archives from storage
- [ ] 4.3 Display resume summary: what's done, what remains

## 5. Error Display

- [ ] 5.1 Show distinct error messages for QUOTA_EXHAUSTED vs NETWORK_ERROR in CLI
- [ ] 5.2 On quota exhausted: display recharge URL, save progress, graceful exit
- [ ] 5.3 On network error: show retry countdown, allow user to cancel
