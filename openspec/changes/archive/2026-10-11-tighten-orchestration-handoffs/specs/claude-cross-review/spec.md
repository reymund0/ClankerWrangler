## MODIFIED Requirements

### Requirement: Review scope is explicit and current
Every review SHALL identify its repository, phase, baseline where applicable, selected requirements, authorized paths, exclusions, and verification evidence. Implementation review SHALL cover selected committed changes, staged and unstaged changes, and selected untracked files; new file names alone SHALL NOT count as reviewed content. Relevant full files and callers SHALL be available for verification. Secrets, ignored files, and unrelated user work SHALL NOT be automatically included. Evidence and file state SHALL be fingerprinted before and after review; changes to the reviewed target SHALL invalidate its applicability. The parent SHALL trace static requirements to relevant guards, bindings and test contracts before dispatch. Preservation claims SHALL identify actual before/after evidence; mechanically ready packets SHALL NOT establish semantic completeness.

#### Scenario: Mixed working tree
- **WHEN** task work includes committed, staged, unstaged, and new files alongside unrelated edits
- **THEN** the manifest includes the authorized changes and full selected file contents, identifies exclusions, and makes no coverage claim for excluded work

#### Scenario: Review target changes
- **WHEN** a file or requirement used as review evidence changes during or after the review
- **THEN** the previous verdict is marked stale for the changed target and requires a new review or explicit user waiver before that checkpoint can be considered satisfied

#### Scenario: Harness safety depends on fixture guards
- **WHEN** a static isolation requirement depends on a neighboring fixture's configuration guards
- **THEN** that fixture is included as authorized read-only context or the checkpoint retains the explicit evidence gap

#### Scenario: Preservation baseline unavailable
- **WHEN** a refactor review lacks a prior source version or meaningful task diff
- **THEN** preservation comparison stays with an identified evidence owner and the external verdict is limited to supplied current-correctness evidence

#### Scenario: Supplied required context skipped
- **WHEN** a static reviewer does not read a host-designated required subject
- **THEN** coverage remains partial or unreviewed with a concrete reason and the checkpoint remains incomplete under the existing recheck budget

## ADDED Requirements

### Requirement: Native guidance path identity
Readiness SHALL recognize captured explicit guidance using the native path representation accepted by packet collection, including Windows slash differences. Original manifest subjects SHALL remain unchanged for coverage and mappings. Unavailable or filtered evidence SHALL still block; identity matching SHALL NOT substitute unrelated files or relax collection guards.

#### Scenario: Windows forward-slash guidance
- **WHEN** explicit readable guidance is supplied with forward slashes and captured with native Windows separators
- **THEN** local preparation recognizes the captured guidance and mapped requirements without invoking Claude or changing original coverage subject strings

#### Scenario: Missing or filtered mapped evidence
- **WHEN** a mapped source or guidance subject has no available captured evidence
- **THEN** readiness remains blocked with the original subject and reason, even if other guidance is successfully normalized
