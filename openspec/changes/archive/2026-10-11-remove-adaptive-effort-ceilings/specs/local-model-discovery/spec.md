# Spec Delta

## MODIFIED Requirements

### Requirement: Full model and effort selectors
All route and temporary-session model controls SHALL offer all CLI-reported provider choices without filtering them down to the prefilled value. Manual model entry and static bundled alternatives SHALL NOT be offered. Current saved or inherited choices absent from the CLI catalog SHALL remain visible as labeled disabled options without preference mutation. Adaptive profile creation SHALL choose from the provider's CLI catalog, while existing profiles remain editable and resettable. Known discovered effort levels SHALL guide model-specific controls, including dropdowns for the three Adaptive profile tiers and Fixed reasoning; no Adaptive ceiling selector SHALL be offered; existing unsupported effort values SHALL stay visible rather than being silently replaced. Unknown effort metadata SHALL remain distinguishable from reported support.

#### Scenario: Existing selection and newly discovered choices
- **WHEN** the selected model differs from newly discovered local models
- **THEN** the selector retains it and displays CLI-reported alternatives, with the absent current value labeled and disabled without changing preferences

#### Scenario: CLI-only profile creation
- **WHEN** a user chooses a model to customize its Adaptive profile
- **THEN** only models from that provider's CLI catalog are offered, no manual ID input exists, and existing profiles remain editable even when absent from discovery

#### Scenario: Model-specific three-tier effort controls
- **WHEN** a model's CLI catalog reports supported effort levels and its Adaptive profile is displayed
- **THEN** Straightforward, Involved, and Demanding offer the model-specific policy-supported choices, saved-unavailable efforts remain visible, and no default-ceiling selector appears
