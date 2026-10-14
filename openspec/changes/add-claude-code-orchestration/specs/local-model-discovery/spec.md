## ADDED Requirements

### Requirement: Tolerant metadata handshake
Discovery SHALL skip CLI startup notifications that precede the metadata response, within the existing deadline and output budget, and SHALL still reject a response with the wrong type, identifier, or shape.

#### Scenario: Notification before metadata
- **WHEN** the Claude CLI emits a startup system notification before its initialize response
- **THEN** discovery returns the reported models and efforts instead of a malformed-metadata failure

#### Scenario: Unexpected response
- **WHEN** the first non-notification message is not the expected metadata response
- **THEN** discovery reports a sanitized provider failure

### Requirement: Host-aware model choices
Model selectors SHALL offer the provider catalog matching each route's provider under the selected host: Claude models for Claude-host native routes and Codex models for its external review, and the reverse for the Codex host. Discovery SHALL remain catalog evidence only and SHALL NOT satisfy native or launcher capability gates.

#### Scenario: Claude-host implementation selector
- **WHEN** the Claude host is selected and the implementation route is edited
- **THEN** the model choices come from the Claude CLI catalog and Codex models are not offered for that route
