## ADDED Requirements

### Requirement: LLM Error Classification
LLMClient SHALL classify API errors into structured codes and handle retry logic per error type.

#### Scenario: Quota exhausted
- **WHEN** DeepSeek API returns 402 or `insufficient_quota` error
- **THEN** LLMClient SHALL raise a typed exception with code `QUOTA_EXHAUSTED`
- **AND** the pipeline SHALL save all current progress before exiting
- **AND** the user SHALL see a clear message suggesting to recharge

#### Scenario: Transient error with retry
- **WHEN** API returns timeout or network error
- **THEN** LLMClient SHALL retry up to 3 times with exponential backoff
- **AND** the user SHALL see "Retrying..." feedback

### Requirement: Scene Streaming in CLI
CLI SHALL display scene rounds in real-time as they complete.

#### Scenario: Streaming round display
- **WHEN** a scene is executing
- **THEN** each round's dialogue and action SHALL appear immediately as generated
- **AND** the total round count SHALL be updated after scene completion

### Requirement: Granular Progress Save
Pipeline SHALL save progress after every successful API step.

#### Scenario: Progress persisted after each pipeline step
- **WHEN** world building completes a conversation round
- **THEN** the CLI session state SHALL be written to disk
- **AND** the `last_step` field SHALL reflect the current pipeline position

### Requirement: Resume from Breakpoint
CLI SHALL allow resuming a session from any pipeline stage.

#### Scenario: Resume from scene execution after quota exhausted
- **WHEN** user restarts CLI and selects "continue existing project"
- **THEN** the system SHALL detect completed scenes from `completed_scene_ids`
- **AND** SHALL skip already-completed stages
- **AND** SHALL resume from the next incomplete stage
