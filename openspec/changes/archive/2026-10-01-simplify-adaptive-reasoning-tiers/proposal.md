# Proposal

## Why

The four-tier assessment guidance tends to concentrate assignments in routine and complex, while mechanical and exceptional have less useful boundaries. Three clearly defined tiers will make assignment-level effort selection easier to explain without adding another classifier or scoring system.

## What Changes

- **BREAKING for new routing requests and saved three-tier profiles:** replace mechanical/routine/complex/exceptional with straightforward/involved/demanding in the current policy. Preserve resolution of frozen older-policy snapshots with their original tier vocabulary and behavior.
- Keep task assessment with the orchestrator: choose a tier for each worker's actual assignment and supply one concise reason. Document definitions, contrasting examples, and reassessment at handoffs; introduce no additional assessment fields, scores, escalation loops, or outcome tracking.
- Retain configurable per-model effort mappings, fixed effort, overrides, ceilings, precedence, and runtime capability gates. Translate the existing consequential-risk floor to involved and clarify that risk flags describe the assignment's actual responsibility.
- Adapt existing profiles using routine → straightforward, complex → involved, exceptional → demanding, preserving exact effort values and ceilings. Support legacy preferences without rewriting them on read; disclose retirement of the mechanical slot and preserve the original document before an explicit migration save.
- Update the existing Adaptive Profiles page to three labeled tier columns with short definitions; update Preview, validation messages, calculated examples, and compatibility metadata together.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `orchestration-routing-policy`: three-tier assessment, deterministic legacy profile conversion, and version-aware frozen snapshot replay.
- `orchestration-routing-editor`: three-tier profile editing and preview with visible, reversible migration on explicit save.

- `claude-cross-review`: Use the shared three-tier assessment and default effort mapping.

## Impact

Changes touch the existing Python routing policy, bundled policy data, editor service and React workspace/types, compatibility manifests, routing guidance/README, and focused policy/editor/installer tests. No new dependencies or services. Installers continue preserving preferences; live global/project files are not rewritten by planning, loading, previewing, or installing. Earlier skill cleanup and the completed review-readiness change remain separate.
