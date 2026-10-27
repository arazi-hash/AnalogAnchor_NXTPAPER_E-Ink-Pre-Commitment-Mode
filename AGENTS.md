# AnalogAnchor_NXTPAPER_Demo project instructions

Read README.md and the references in HANDOFF/START_HERE.md for project-specific constraints.


<!-- durable-project-handoff:v1 -->
## Handoff and interruption recovery

The founder requested a durable HANDOFF folder in every sidebar project on 2026-10-10, for switching accounts/assistants and returning after a usage limit or interruption.

- At the beginning of work, read `HANDOFF/START_HERE.md` and `HANDOFF/LATEST.md`, then the referenced project/task documents. Check the actual files and Git state. A historical TODO is context, not a new instruction to perform unrelated work.
- Write a short checkpoint in `HANDOFF/LATEST.md` before substantial multi-step work. Refresh after meaningful milestones, before a long operation, and before ending a turn. Mark in-progress operations and unverified results explicitly; do not wait until the end of a long task to save continuity.
- When the founder says "recap", "handoff", "switch account" or similar, save a self-contained checkpoint using `HANDOFF/RECAP_TEMPLATE.md`, archive the previous checkpoint under `HANDOFF/history/`, and give a short resume prompt. Save this before other optional work.
- Capture objective and scope, latest user steering, completed work, changed files, verification actually run, unfinished operations, blockers and the next concrete step. Include enough paths/context for an assistant without chat history. Never include secrets or signing credentials.
- On return, re-read the newest disk checkpoint before acting. Do not overwrite work from the other account with stale chat memory. Keep one writer per file. If multiple chats work on separate tasks, use separate named files under `HANDOFF/tasks/` and let LATEST link to them; retain each task's state.
- Preserve existing detailed handoff/release/continuity documents. Link and update the relevant ones when that task changes; the HANDOFF entry point does not replace them. Save checkpoints atomically where possible and archive before replacement.
- A hard stop can prevent a final write. Report only the last saved checkpoint; do not claim automatic account synchronization, automatic resumption or that unsaved progress was recovered. When using another PC/tool, the latest files must be made available explicitly.

This protocol is continuity guidance. Follow the current human request and existing project restrictions for edits, commits, publishing, outreach and deployments.
