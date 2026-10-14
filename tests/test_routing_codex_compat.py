"""Codex-led routing regression frozen against the policy-6 resolver.

The expected file was recorded from the unchanged policy-6 helper (run this module with
``--record-policy6`` only against policy 6). Later policy versions must reproduce every
decision and effective configuration for the Codex host exactly, apart from the added
identity fields and the version/fingerprint values that necessarily change.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "subagents" / "scripts"))
import routing_policy as policy

EXPECTED_PATH = Path(__file__).resolve().parent / "fixtures" / "routing_codex_policy6_expected.json"
ADDED_DECISION_FIELDS = ("host", "provider", "execution", "policy_version", "snapshot_fingerprint")
ADDED_EFFECTIVE_FIELDS = ("host", "provider", "execution")

# Representative of a saved Codex preference file: exact model IDs absent from the bundled
# catalog, custom Adaptive profiles, an agent default and a specialist exception.
USER_PREFERENCES = {
    "schema_version": 1,
    "interactions": {
        "planning": {"model": "gpt-6.1-sol", "reasoning": {"mode": "adaptive"}},
        "implementation": {
            "model": "gpt-6-luna",
            "reasoning": {"mode": "adaptive"},
            "specialists": {"clanker-ui-ux-reviewer": {"reasoning": {"mode": "fixed", "effort": "high"}}},
        },
        "native-review": {"model": "gpt-6.1-sol"},
        "visual-review": {"model": "gpt-6.1-sol", "reasoning": {"mode": "fixed", "effort": "xhigh"}},
        "claude-review": {"model": "opus", "reasoning": {"mode": "fixed", "effort": "high"}},
    },
    "agents": {"clanker-backend-developer": {"model": "gpt-5.6-terra"}},
    "adaptive_profiles": {
        "codex:gpt-6.1-sol": {"tiers": {"straightforward": "low", "involved": "high", "demanding": "ultra"}},
        "codex:gpt-6-luna": {"tiers": {"straightforward": "medium", "involved": "xhigh", "demanding": "max"}},
        "claude:opus": {"tiers": {"straightforward": "low", "involved": "medium", "demanding": "max"}},
    },
}
# Fixed-effort exact-ID routes with no custom profile: guards bundled-profile scoping.
FIXED_EXACT_PREFERENCES = {
    "schema_version": 1,
    "interactions": {
        "planning": {"model": "gpt-6.1-sol", "reasoning": {"mode": "fixed", "effort": "low"}},
        "implementation": {"model": "gpt-6.1-sol", "reasoning": {"mode": "fixed", "effort": "medium"}},
        "native-review": {"model": "gpt-6.1-sol"},
    },
}
# Adaptive on an exact ID with no profile at all: resolution must keep raising.
UNPROFILED_ADAPTIVE_PREFERENCES = {
    "schema_version": 1,
    "interactions": {"implementation": {"model": "gpt-6.1-sol"}},
}
PREFERENCE_SETS = {
    "bundled": {"schema_version": 1},
    "user": USER_PREFERENCES,
    "fixed-exact": FIXED_EXACT_PREFERENCES,
    "unprofiled-adaptive": UNPROFILED_ADAPTIVE_PREFERENCES,
}

ALL_NATIVE_MODELS = ("gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6.1-sol", "gpt-6-luna")
CAPABILITIES = {
    "none": None,
    "native-full": {"provider": "codex", "source": "fixture", "models": {
        model: ["low", "medium", "high", "xhigh", "max", "ultra"] for model in ALL_NATIVE_MODELS}},
    "native-partial": {"provider": "codex", "source": "fixture", "models": {
        model: ["low", "medium", "xhigh"] for model in ALL_NATIVE_MODELS}},
    "claude-preflight": {"provider": "claude", "source": "fixture", "preflight_valid": True},
    "claude-models-partial": {"provider": "claude", "source": "fixture", "models": {"opus": ["high"]}, "preflight_valid": True},
}
NATIVE_CAPABILITY_NAMES = ("none", "native-full", "native-partial")
CLAUDE_CAPABILITY_NAMES = ("none", "claude-preflight", "claude-models-partial")
NATIVE_INTERACTIONS = ("planning", "implementation", "native-review", "visual-review")
ROLES = (None, "clanker-architect", "clanker-backend-developer", "clanker-ui-ux-reviewer")
TIER_NAMES = ("straightforward", "involved", "demanding")
FLAG_SETS = ((), ("security",))


def cases():
    for interaction in NATIVE_INTERACTIONS:
        for role in ROLES:
            # Risk flags and the capability gate do not depend on the role, so only the role-free
            # route covers every combination.
            for tier in TIER_NAMES:
                for flags in (FLAG_SETS if role is None else FLAG_SETS[:1]):
                    for capability in (NATIVE_CAPABILITY_NAMES if role is None else NATIVE_CAPABILITY_NAMES[:2]):
                        yield interaction, role, tier, flags, capability
    for tier in TIER_NAMES:
        for flags in FLAG_SETS:
            for capability in CLAUDE_CAPABILITY_NAMES:
                yield "claude-review", None, tier, flags, capability


def case_key(interaction, role, tier, flags, capability):
    return "|".join((interaction, role or "-", tier, ",".join(flags) or "-", capability))


def build_request(interaction, role, tier, flags, capability):
    request = {"interaction": interaction, "tier": tier, "reason": "Regression fixture", "risk_flags": list(flags)}
    if role is not None:
        request["role"] = role
    if CAPABILITIES[capability] is not None:
        request["capabilities"] = CAPABILITIES[capability]
    return request


ECHOED_DECISION_FIELDS = ("schema_version", "reason", "interaction", "role")


def normalize_decision(decision, interaction, role):
    """Drop added identity fields and request echoes (verified here, then omitted to keep the file small)."""
    assert (decision["schema_version"], decision["reason"], decision["interaction"], decision["role"]) == (1, "Regression fixture", interaction, role)
    return {key: value for key, value in decision.items() if key not in ADDED_DECISION_FIELDS + ECHOED_DECISION_FIELDS}


def normalize_effective(effective):
    result = {key: value for key, value in effective.items() if key not in ADDED_EFFECTIVE_FIELDS}
    result["interactions"] = {
        name: {key: value for key, value in entry.items() if key not in ADDED_EFFECTIVE_FIELDS}
        for name, entry in effective["interactions"].items()
    }
    return result


def compute():
    """Resolve the whole fixture matrix with the helper currently on the import path."""
    outputs = {}
    for name, preferences in PREFERENCE_SETS.items():
        snapshot = policy.snapshot_from_documents(preferences, sources={"global": "fixture.json"})
        entry = {"decisions": {}, "errors": {}}
        for case in cases():
            key = case_key(*case)
            try:
                entry["decisions"][key] = normalize_decision(policy.resolve(snapshot, build_request(*case)), case[0], case[1])
            except policy.RoutingError as exc:
                entry["errors"][key] = str(exc)
        try:
            entry["effective"] = normalize_effective(policy.effective_configuration(snapshot))
        except policy.RoutingError as exc:
            entry["effective_error"] = str(exc)
        outputs[name] = entry
    return outputs


def record_policy6():
    if policy.POLICY_VERSION != "6":
        raise SystemExit("The frozen expectation may only be recorded from the unchanged policy-6 helper")
    EXPECTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ['{"recorded_policy_version": "6", "outputs": {']
    outputs = compute()
    for index, (name, entry) in enumerate(outputs.items()):
        lines.append(f"{json.dumps(name)}: {{")
        lines.append('"decisions": {')
        decisions = [f"{json.dumps(key)}: {json.dumps(value, sort_keys=True)}" for key, value in entry["decisions"].items()]
        lines.append(",\n".join(decisions))
        lines.append("},")
        rest = {key: value for key, value in entry.items() if key != "decisions"}
        lines.append(json.dumps(rest, sort_keys=True)[1:-1])
        lines.append("}" + ("," if index < len(outputs) - 1 else ""))
    lines.append("}}")
    EXPECTED_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


class CodexCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
        cls.actual = compute()

    def test_recording_is_from_policy_six(self):
        self.assertEqual(self.expected["recorded_policy_version"], "6")

    def test_matrix_is_nontrivial(self):
        decisions = sum(len(entry["decisions"]) for entry in self.expected["outputs"].values())
        self.assertGreater(decisions, 500)
        statuses = {decision["capability_status"] for entry in self.expected["outputs"].values() for decision in entry["decisions"].values()}
        self.assertEqual(statuses, {"unverified", "supported", "unsupported", "requires_launcher_preflight", "preflight_valid"})
        self.assertTrue(self.expected["outputs"]["unprofiled-adaptive"]["errors"])

    def test_decisions_match_policy_six_for_every_preference_set(self):
        for name, expected in self.expected["outputs"].items():
            with self.subTest(preferences=name):
                actual = self.actual[name]
                self.assertEqual(sorted(actual["decisions"]), sorted(expected["decisions"]))
                self.assertEqual(actual["errors"], expected["errors"])
                for key, decision in expected["decisions"].items():
                    self.assertEqual(json.loads(json.dumps(actual["decisions"][key])), decision, key)

    def test_effective_configuration_matches_policy_six(self):
        for name, expected in self.expected["outputs"].items():
            with self.subTest(preferences=name):
                self.assertEqual(self.actual[name].get("effective_error"), expected.get("effective_error"))
                self.assertEqual(json.loads(json.dumps(self.actual[name].get("effective"))), expected.get("effective"))

    def test_fixed_exact_id_routes_keep_profile_free_provenance(self):
        fixed = self.actual["fixed-exact"]["decisions"]
        decision = fixed[case_key("planning", None, "involved", (), "native-full")]
        self.assertEqual((decision["model"], decision["effort"], decision["provenance"]["profile"]), ("gpt-6.1-sol", "low", None))
        self.assertEqual(decision["limitations"], [])


if __name__ == "__main__":
    if sys.argv[1:] == ["--record-policy6"]:
        record_policy6()
    else:
        unittest.main()
