"""Focused deterministic tests for the shared routing policy helper."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "subagents" / "scripts"))
import routing_policy as policy


EMPTY = {"schema_version": 1}
NATIVE_CAPABILITIES = {
    "provider": "codex",
    "source": "active collaboration tool catalog",
    "models": {"gpt-5.6-luna": ["medium", "high", "xhigh", "max"], "gpt-5.6-sol": ["low", "medium", "high", "xhigh"]},
}


def request(**overrides):
    result = {"interaction": "implementation", "tier": "straightforward", "reason": "Clear bounded implementation"}
    result.update(overrides)
    return result


class PreferenceTests(unittest.TestCase):
    def test_empty_and_sparse_preferences_normalize_without_defaults(self):
        self.assertEqual(policy.validate_preferences(EMPTY), EMPTY)
        sparse = policy.validate_preferences({"schema_version": 1, "interactions": {"planning": {"model": "gpt-5.6-luna"}}})
        self.assertEqual(sparse["interactions"]["planning"], {"model": "gpt-5.6-luna"})

    def test_invalid_shapes_are_field_specific(self):
        cases = [
            ({"schema_version": 2}, "schema_version"),
            ({"schema_version": 1, "unknown": True}, "unknown"),
            ({"schema_version": 1, "interactions": {"unknown": {"model": "x"}}}, "unknown"),
            ({"schema_version": 1, "interactions": {"claude-review": {"specialists": {}}}}, "specialists"),
            ({"schema_version": 1, "interactions": {"planning": {"reasoning": {"mode": "adaptive", "effort": "high"}}}}, "effort"),
        ]
        for document, fragment in cases:
            with self.subTest(fragment=fragment), self.assertRaisesRegex(policy.RoutingError, fragment):
                policy.validate_preferences(document)

    def test_known_provider_mismatch_is_rejected_and_unknown_fixed_is_allowed(self):
        with self.assertRaisesRegex(policy.RoutingError, "belongs to claude"):
            policy.validate_preferences({"schema_version": 1, "interactions": {"planning": {"model": "claude-opus-5"}}})
        custom = policy.validate_preferences({"schema_version": 1, "interactions": {"planning": {"model": "custom-model-v9", "reasoning": {"mode": "fixed", "effort": "high"}}}})
        self.assertEqual(custom["interactions"]["planning"]["model"], "custom-model-v9")

    def test_agents_are_sparse_native_routes(self):
        document = {"schema_version": 1, "agents": {"clanker-backend-developer": {"model": "gpt-5.6-terra", "reasoning": {"mode": "fixed", "effort": "high"}}}}
        self.assertEqual(policy.validate_preferences(document), document)
        cases = [
            ({"schema_version": 1, "agents": {"unknown": {"model": "gpt-5.6-terra"}}}, "unknown"),
            ({"schema_version": 1, "agents": {"clanker-backend-developer": {"model": "claude-opus-5"}}}, "belongs to claude"),
            ({"schema_version": 1, "agents": {"clanker-backend-developer": {"specialists": {}}}}, "specialists"),
            ({"schema_version": 1, "agents": {"clanker-backend-developer": {"reasoning": {"mode": "fixed"}}}}, "effort"),
        ]
        for invalid, fragment in cases:
            with self.subTest(fragment=fragment), self.assertRaisesRegex(policy.RoutingError, fragment):
                policy.validate_preferences(invalid)

    def test_profiles_are_complete_and_provider_scoped(self):
        current = {"schema_version": 1, "adaptive_profiles": {"codex:custom": {"tiers": {"straightforward": "medium", "involved": "high", "demanding": "xhigh"}, "default_ceiling": "high"}}}
        self.assertEqual(policy.validate_preferences(current), current)
        incomplete = {"schema_version": 1, "adaptive_profiles": {"codex:custom": {"tiers": {"straightforward": "medium", "involved": "high"}, "default_ceiling": "high"}}}
        with self.assertRaisesRegex(policy.RoutingError, "straightforward, involved, demanding"):
            policy.validate_preferences(incomplete)
        mixed = {"schema_version": 1, "adaptive_profiles": {"codex:custom": {"tiers": {"routine": "medium", "involved": "high", "demanding": "xhigh"}, "default_ceiling": "high"}}}
        with self.assertRaisesRegex(policy.RoutingError, "tiers"):
            policy.validate_preferences(mixed)
        invalid_retired_effort = {"schema_version": 1, "adaptive_profiles": {"codex:custom": {"tiers": {"mechanical": None, "routine": "medium", "complex": "high", "exceptional": "xhigh"}, "default_ceiling": "high"}}}
        with self.assertRaisesRegex(policy.RoutingError, "tiers.mechanical"):
            policy.validate_preferences(invalid_retired_effort)
        mismatch = {"schema_version": 1, "adaptive_profiles": {"codex:claude-opus-5": {"tiers": {tier: "high" for tier in policy.TIERS}, "default_ceiling": "high"}}}
        with self.assertRaisesRegex(policy.RoutingError, "belongs to claude"):
            policy.validate_preferences(mismatch)

    def test_policy_three_bundle_rejects_legacy_profile_vocabulary(self):
        bundle = policy.load_bundle()
        bundle["defaults"]["adaptive_profiles"]["codex:gpt-5.6-terra"]["tiers"] = {
            "mechanical": "low", "routine": "medium", "complex": "high", "exceptional": "xhigh"
        }
        with self.assertRaisesRegex(policy.RoutingError, "current tier vocabulary"):
            policy._validate_bundle_document(bundle)

    def test_complete_legacy_profiles_normalize_without_changing_unrelated_fields(self):
        legacy = {
            "schema_version": 1,
            "interactions": {"implementation": {"reasoning": {"mode": "fixed", "effort": "medium"}}},
            "agents": {"clanker-backend-developer": {"model": "custom-codex-v9"}},
            "adaptive_profiles": {
                "codex:custom-codex-v9": {"tiers": {"mechanical": "low", "routine": "medium", "complex": "max", "exceptional": "ultra"}, "default_ceiling": "ultra"},
                "claude:custom-claude-v9": {"tiers": {"mechanical": "low", "routine": "medium", "complex": "high", "exceptional": "max"}, "default_ceiling": "max"},
            },
        }
        original = copy.deepcopy(legacy)
        self.assertTrue(policy.needs_profile_migration(legacy))
        normalized = policy.validate_preferences(legacy)
        self.assertEqual(legacy, original)
        self.assertEqual(normalized["interactions"], original["interactions"])
        self.assertEqual(normalized["agents"], original["agents"])
        self.assertEqual(normalized["adaptive_profiles"], {
            "codex:custom-codex-v9": {"tiers": {"straightforward": "medium", "involved": "max", "demanding": "ultra"}, "default_ceiling": "ultra"},
            "claude:custom-claude-v9": {"tiers": {"straightforward": "medium", "involved": "high", "demanding": "max"}, "default_ceiling": "max"},
        })
        self.assertFalse(policy.needs_profile_migration(normalized))
        with self.assertRaisesRegex(policy.RoutingError, "tiers"):
            policy.needs_profile_migration({"schema_version": 1, "adaptive_profiles": {"codex:broken": {"tiers": {"routine": "medium", "involved": "high"}, "default_ceiling": "high"}}})

    def test_snapshot_normalizes_global_profiles_and_ignores_malformed_project_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            global_path, project_path = root / "global.json", root / "project.json"
            global_document = {"schema_version": 1, "adaptive_profiles": {"codex:custom-global": {"tiers": {"mechanical": "low", "routine": "medium", "complex": "high", "exceptional": "max"}, "default_ceiling": "max"}}}
            global_bytes = json.dumps(global_document).encode()
            global_path.write_bytes(global_bytes)
            project_path.write_text("not-json", encoding="utf-8")
            project_bytes = project_path.read_bytes()
            snapshot = policy.create_snapshot(global_path)
            self.assertEqual(snapshot["documents"]["global"]["adaptive_profiles"]["codex:custom-global"]["tiers"], {"straightforward": "medium", "involved": "high", "demanding": "max"})
            self.assertEqual(snapshot["hashes"]["global"], policy._sha256(global_bytes))
            self.assertEqual(snapshot["policy_version"], "4")
            self.assertEqual(set(snapshot["documents"]), {"global"})
            self.assertEqual(set(snapshot["sources"]), {"global"})
            self.assertEqual(set(snapshot["hashes"]), {"bundle", "global"})
            self.assertEqual(global_path.read_bytes(), global_bytes)
            self.assertEqual(project_path.read_bytes(), project_bytes)


class ResolutionTests(unittest.TestCase):
    def test_effective_display_distinguishes_profile_default_from_explicit_cap(self):
        snapshot = policy.snapshot_from_documents({"schema_version": 1})
        default = policy.effective_configuration(snapshot)["interactions"]["implementation"]
        self.assertEqual(default["route"]["reasoning"], {"mode": "adaptive"})
        self.assertEqual(default["ceiling"], "xhigh")
        self.assertEqual(default["ceiling_source"], "bundle.defaults.adaptive_profiles.codex:gpt-5.6-terra.default_ceiling")
        prefs = {"schema_version": 1, "interactions": {"implementation": {"reasoning": {"mode": "adaptive", "max_effort": "high"}}}}
        capped = policy.effective_configuration(policy.snapshot_from_documents(prefs))["interactions"]["implementation"]
        self.assertEqual(capped["route"]["reasoning"]["max_effort"], "high")
        self.assertEqual(capped["ceiling_source"], "global.interactions.implementation.reasoning.max_effort")
        specialist = capped["specialists"]["clanker-backend-developer"]
        self.assertEqual(specialist["ceiling"], "high")
        self.assertEqual(specialist["ceiling_source"], capped["ceiling_source"])


    def snapshot(self, global_document=None):
        return policy.snapshot_from_documents(global_document or EMPTY, sources={"global": "global.json"})

    def test_astra_planning_adaptive_uses_bundled_profile_without_user_profile(self):
        prefs = {"schema_version": 1, "interactions": {"planning": {"model": "gpt-6-astra"}}}
        snapshot = self.snapshot(prefs)
        effective = policy.effective_configuration(snapshot)["interactions"]["planning"]
        self.assertEqual(effective["route"]["model"], "gpt-6-astra")
        self.assertEqual(effective["ceiling"], "xhigh")
        for tier, effort in {"straightforward": "medium", "involved": "high", "demanding": "xhigh"}.items():
            with self.subTest(tier=tier):
                result = policy.resolve(snapshot, request(interaction="planning", tier=tier))
                self.assertEqual(result["effort"], effort)
                self.assertEqual(result["provenance"]["profile"], "bundle.defaults.adaptive_profiles.codex:gpt-6-astra")
                self.assertFalse(result["dispatch_allowed"])
        capped = {"schema_version": 1, "interactions": {"planning": {"reasoning": {"mode": "adaptive", "max_effort": "high"}}}}
        result = policy.resolve(self.snapshot({"schema_version": 1, "interactions": {"planning": {"model": "gpt-6-astra", "reasoning": {"mode": "adaptive", "max_effort": "high"}}}}), request(interaction="planning", tier="demanding"))
        self.assertEqual(result["effort"], "high")

    def test_claude_cli_ids_have_review_profiles_without_rewriting_aliases(self):
        for model in ("default", "opus[1m]", "claude-fable-5-1[1m]", "sonnet"):
            with self.subTest(model=model):
                prefs = {"schema_version": 1, "interactions": {"claude-review": {"model": model}}}
                snapshot = self.snapshot(prefs)
                effective = policy.effective_configuration(snapshot)["interactions"]["claude-review"]
                self.assertEqual(effective["route"]["model"], model)
                for tier, effort in {"straightforward": "medium", "involved": "high", "demanding": "high"}.items():
                    result = policy.resolve(snapshot, request(interaction="claude-review", tier=tier))
                    self.assertEqual((result["model"], result["effort"]), (model, effort))
                    self.assertEqual(result["capability_status"], "requires_launcher_preflight")
                    self.assertFalse(result["dispatch_allowed"])

    def test_defaults_and_native_evidence(self):
        decision = policy.resolve(self.snapshot(), request(capabilities={"provider": "codex", "source": "catalog", "models": {"gpt-5.6-terra": ["medium"]}}))
        self.assertEqual((decision["model"], decision["effort"]), ("gpt-5.6-terra", "medium"))
        self.assertEqual(decision["capability_status"], "supported")
        self.assertTrue(decision["dispatch_allowed"])

    def test_global_specialist_precedence_and_session_beats_all(self):
        global_document = {"schema_version": 1, "interactions": {"planning": {"model": "gpt-5.6-sol", "specialists": {"clanker-architect": {"model": "gpt-5.6-luna"}}}}}
        base = request(interaction="planning", role="clanker-architect", capabilities={"provider": "codex", "source": "catalog", "models": {"gpt-5.6-sol": ["medium"], "gpt-5.6-luna": ["high"]}})
        specialist = policy.resolve(self.snapshot(global_document), base)
        self.assertEqual(specialist["model"], "gpt-5.6-luna")
        self.assertEqual(specialist["provenance"]["model"], "global.interactions.planning.specialists.clanker-architect.model")
        session = policy.resolve(self.snapshot(global_document), request(**{**base, "session_override": {"model": "gpt-5.6-sol"}}))
        self.assertEqual(session["model"], "gpt-5.6-sol")
        self.assertEqual(session["provenance"]["model"], "session_override.model")

    def test_agent_precedence_boundaries_and_non_native_routes(self):
        global_interaction = {"schema_version": 1, "interactions": {"planning": {"model": "gpt-5.6-sol"}}}
        global_agent = {"schema_version": 1, "interactions": {"planning": {"model": "gpt-5.6-sol"}}, "agents": {"clanker-backend-developer": {"model": "gpt-5.6-terra"}}}
        global_specialist = {"schema_version": 1, "interactions": {"planning": {"model": "gpt-5.6-sol", "specialists": {"clanker-backend-developer": {"model": "gpt-5.6-luna"}}}}, "agents": {"clanker-backend-developer": {"model": "gpt-5.6-terra"}}}
        cases = [
            (global_interaction, None, "gpt-5.6-sol"),
            (global_agent, None, "gpt-5.6-terra"),
            (global_specialist, None, "gpt-5.6-luna"),
            (global_specialist, {"model": "gpt-5.6-sol"}, "gpt-5.6-sol"),
        ]
        for global_document, session_override, expected_model in cases:
            with self.subTest(expected_model=expected_model, session_override=session_override):
                overrides = {"session_override": session_override} if session_override is not None else {}
                decision = policy.resolve(self.snapshot(global_document), request(interaction="planning", role="clanker-backend-developer", **overrides))
                self.assertEqual(decision["model"], expected_model)
        no_role = policy.resolve(self.snapshot(global_specialist), request(interaction="planning"))
        self.assertEqual(no_role["model"], "gpt-5.6-sol")
        claude = policy.resolve(self.snapshot({"schema_version": 1, "agents": {"clanker-backend-developer": {"model": "gpt-5.6-terra"}}}), request(interaction="claude-review", tier="involved", reason="Independent review"))
        self.assertEqual(claude["model"], "opus")

    def test_agent_precedence_and_effective_baseline_are_field_specific(self):
        global_document = {
            "schema_version": 1,
            "interactions": {"planning": {"model": "gpt-5.6-sol", "specialists": {"clanker-backend-developer": {"reasoning": {"mode": "fixed", "effort": "high"}}}}},
            "agents": {"clanker-backend-developer": {"model": "gpt-5.6-terra", "reasoning": {"mode": "fixed", "effort": "medium"}}},
        }
        snapshot = self.snapshot(global_document)
        decision = policy.resolve(snapshot, request(interaction="planning", role="clanker-backend-developer", capabilities={"provider": "codex", "source": "catalog", "models": {"gpt-5.6-sol": ["high"]}}))
        self.assertEqual((decision["model"], decision["effort"]), ("gpt-5.6-terra", "high"))
        self.assertEqual(decision["provenance"]["model"], "global.agents.clanker-backend-developer.model")
        self.assertEqual(decision["provenance"]["reasoning"], "global.interactions.planning.specialists.clanker-backend-developer.reasoning")
        effective = policy.effective_configuration(snapshot)
        baseline = effective["agents"]["clanker-backend-developer"]
        self.assertEqual(baseline["route"], {"model": "gpt-5.6-terra", "reasoning": {"mode": "fixed", "effort": "medium"}})
        self.assertEqual(baseline["provenance"], {"model": "global.agents.clanker-backend-developer.model", "reasoning": "global.agents.clanker-backend-developer.reasoning"})
        specialist = effective["interactions"]["planning"]["specialists"]["clanker-backend-developer"]
        self.assertEqual(specialist["route"], {"model": "gpt-5.6-terra", "reasoning": {"mode": "fixed", "effort": "high"}})

    def test_agent_model_only_override_retains_interaction_reasoning(self):
        global_document = {"schema_version": 1, "interactions": {"implementation": {"reasoning": {"mode": "adaptive", "max_effort": "high"}}}}
        global_document["agents"] = {"clanker-backend-developer": {"model": "gpt-5.6-luna"}}
        decision = policy.resolve(self.snapshot(global_document), request(role="clanker-backend-developer", tier="demanding", capabilities=NATIVE_CAPABILITIES))
        self.assertEqual((decision["model"], decision["effort"], decision["ceiling"]), ("gpt-5.6-luna", "high", "high"))
        self.assertEqual(decision["provenance"]["reasoning"], "global.interactions.implementation.reasoning")

    def test_atomic_reasoning_and_inherited_cap_survive_model_only_override(self):
        global_document = {"schema_version": 1, "interactions": {"implementation": {"reasoning": {"mode": "adaptive", "max_effort": "high"}}}}
        global_document["agents"] = {"clanker-backend-developer": {"model": "gpt-5.6-luna"}}
        decision = policy.resolve(self.snapshot(global_document), request(role="clanker-backend-developer", tier="demanding", capabilities=NATIVE_CAPABILITIES))
        self.assertEqual((decision["proposed_effort"], decision["effort"], decision["ceiling"]), ("max", "high", "high"))
        self.assertEqual(decision["ceiling_source"], "global.interactions.implementation.reasoning.max_effort")
        reset_document = {"schema_version": 1, "interactions": {"implementation": {"reasoning": {"mode": "adaptive"}}}, "agents": {"clanker-backend-developer": {"model": "gpt-5.6-luna"}}}
        reset = policy.resolve(self.snapshot(reset_document), request(role="clanker-backend-developer", tier="demanding", capabilities=NATIVE_CAPABILITIES))
        self.assertEqual((reset["effort"], reset["ceiling"]), ("xhigh", "xhigh"))

    def test_adaptive_tier_maps_risks_and_fixed_limitations(self):
        luna = {"schema_version": 1, "interactions": {"implementation": {"model": "gpt-5.6-luna"}}}
        for tier, expected in (("straightforward", "high"), ("involved", "xhigh"), ("demanding", "xhigh")):
            with self.subTest(tier=tier):
                decision = policy.resolve(self.snapshot(luna), request(tier=tier, capabilities=NATIVE_CAPABILITIES))
                self.assertEqual(decision["effort"], expected)
        risk = policy.resolve(self.snapshot(luna), request(tier="straightforward", risk_flags=["security"], capabilities=NATIVE_CAPABILITIES))
        self.assertEqual((risk["tier"], risk["effort"]), ("involved", "xhigh"))
        fixed = {"schema_version": 1, "interactions": {"implementation": {"model": "gpt-5.6-luna", "reasoning": {"mode": "fixed", "effort": "low"}}}}
        decision = policy.resolve(self.snapshot(fixed), request(tier="involved", capabilities=NATIVE_CAPABILITIES))
        self.assertEqual(decision["effort"], "low")
        self.assertTrue(any("below" in item for item in decision["limitations"]))

    def test_unknown_adaptive_model_requires_profile(self):
        document = {"schema_version": 1, "interactions": {"planning": {"model": "custom-model-v9"}}}
        with self.assertRaisesRegex(policy.RoutingError, "requires a complete profile"):
            policy.resolve(self.snapshot(document), request(interaction="planning"))

    def test_capability_statuses_do_not_fallback(self):
        snap = self.snapshot()
        unverified = policy.resolve(snap, request())
        self.assertEqual((unverified["capability_status"], unverified["dispatch_allowed"]), ("unverified", False))
        unsupported = policy.resolve(snap, request(capabilities={"provider": "codex", "source": "catalog", "models": {"gpt-5.6-terra": ["low"]}}))
        self.assertEqual((unsupported["capability_status"], unsupported["dispatch_allowed"]), ("unsupported", False))
        claude = policy.resolve(snap, request(interaction="claude-review", tier="involved", reason="Independent contract review"))
        self.assertEqual(claude["capability_status"], "requires_launcher_preflight")
        self.assertTrue(claude["launcher_allowed"])
        self.assertFalse(claude["dispatch_allowed"])
        preflight = policy.resolve(snap, request(interaction="claude-review", tier="involved", reason="Independent contract review", capabilities={"provider": "claude", "source": "launcher", "preflight_valid": True}))
        self.assertEqual((preflight["capability_status"], preflight["account_status"], preflight["dispatch_allowed"]), ("preflight_valid", "unverified", True))

    def test_provider_mismatch_and_bad_reason_are_rejected(self):
        with self.assertRaisesRegex(policy.RoutingError, "does not match"):
            policy.resolve(self.snapshot(), request(capabilities={"provider": "claude", "source": "wrong"}))
        with self.assertRaisesRegex(policy.RoutingError, "request.reason"):
            policy.resolve(self.snapshot(), request(reason="  "))


    def test_claude_supported_fixed_max_and_known_unsupported_metadata(self):
        preferences = {"schema_version": 1, "interactions": {"claude-review": {"reasoning": {"mode": "fixed", "effort": "max"}}}}
        snapshot = self.snapshot(preferences)
        decision = policy.resolve(snapshot, request(interaction="claude-review", tier="demanding", reason="Explicit high-complexity cross-review"))
        self.assertEqual((decision["effort"], decision["capability_status"]), ("max", "requires_launcher_preflight"))
        blocked = policy.resolve(snapshot, request(interaction="claude-review", tier="demanding", reason="Explicit high-complexity cross-review", capabilities={"provider": "claude", "source": "launcher", "models": {"opus": ["high"]}, "preflight_valid": True}))
        self.assertEqual((blocked["capability_status"], blocked["dispatch_allowed"]), ("unsupported", False))
        self.assertNotIn("launcher_allowed", blocked)

    def test_empty_session_override_is_a_noop(self):
        snapshot = self.snapshot()
        normal = policy.resolve(snapshot, request())
        empty = policy.resolve(snapshot, request(session_override={}))
        self.assertEqual(normal, empty)
class SnapshotAndCliTests(unittest.TestCase):
    def test_old_and_unknown_snapshots_require_a_new_run(self):
        for version in ("1", "2", "3", "5", []):
            snapshot = policy.snapshot_from_documents(EMPTY)
            snapshot["policy_version"] = version
            for operation in (policy.validate_snapshot, policy.effective_configuration,
                              lambda value: policy.resolve(value, request())):
                with self.subTest(version=version, operation=operation), self.assertRaisesRegex(policy.RoutingError, "Start a new run"):
                    operation(snapshot)

    def test_current_snapshot_api_has_no_project_input(self):
        with self.assertRaises(TypeError):
            policy.snapshot_from_documents(EMPTY, EMPTY)
        with self.assertRaises(TypeError):
            policy.snapshot_from_documents(EMPTY, project_document=EMPTY)

    def test_snapshot_rejects_policy_and_bundle_version_mismatch(self):
        snapshot = policy.snapshot_from_documents(EMPTY)
        snapshot["bundle"]["policy_version"] = "3"
        snapshot["fingerprint"] = policy._sha256(policy._canonical_json(policy._snapshot_payload(snapshot)))
        with self.assertRaisesRegex(policy.RoutingError, "policy_version"):
            policy.validate_snapshot(snapshot)
        for unsupported in ([], "5"):
            snapshot = policy.snapshot_from_documents(EMPTY)
            snapshot["policy_version"] = unsupported
            snapshot["bundle"]["policy_version"] = unsupported
            snapshot["hashes"]["bundle"] = policy._sha256(policy._canonical_json(snapshot["bundle"]))
            snapshot["fingerprint"] = policy._sha256(policy._canonical_json(policy._snapshot_payload(snapshot)))
            with self.subTest(version=unsupported), self.assertRaisesRegex(policy.RoutingError, "policy_version"):
                policy.validate_snapshot(snapshot)

    def test_current_requests_reject_legacy_tier_names_and_current_snapshots_require_current_profiles(self):
        current = policy.snapshot_from_documents(EMPTY)
        for legacy_tier in policy.LEGACY_TIERS:
            with self.subTest(tier=legacy_tier), self.assertRaisesRegex(policy.RoutingError, "request.tier"):
                policy.resolve(current, request(tier=legacy_tier))

        snapshot = policy.snapshot_from_documents(EMPTY)
        snapshot["documents"]["global"]["adaptive_profiles"] = {
            "codex:custom": {"tiers": {"mechanical": "low", "routine": "medium", "complex": "high", "exceptional": "xhigh"}, "default_ceiling": "xhigh"}
        }
        snapshot["hashes"]["global"] = policy._hash_document(snapshot["documents"]["global"])
        snapshot["fingerprint"] = policy._sha256(policy._canonical_json(policy._snapshot_payload(snapshot)))
        with self.assertRaisesRegex(policy.RoutingError, "already use"):
            policy.validate_snapshot(snapshot)

    def test_snapshot_is_stable_after_file_changes_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            global_path = root / "global.json"
            global_path.write_text(json.dumps({"schema_version": 1, "interactions": {"implementation": {"model": "gpt-5.6-luna"}}}), encoding="utf-8")
            snap = policy.create_snapshot(global_path)
            before = policy.resolve(snap, request())
            global_path.write_text(json.dumps(EMPTY), encoding="utf-8")
            after = policy.resolve(snap, request())
            self.assertEqual(before, after)
            snap["documents"]["global"]["interactions"]["implementation"]["model"] = "gpt-5.6-terra"
            with self.assertRaisesRegex(policy.RoutingError, "fingerprint"):
                policy.validate_snapshot(snap)

    def test_explicit_bypass_and_linked_config_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            broken = root / "broken.json"
            broken.write_text("not-json", encoding="utf-8")
            snapshot = policy.create_snapshot(broken, bypass=[str(broken)])
            self.assertEqual(snapshot["bypassed_sources"], [str(broken)])
            with self.assertRaisesRegex(policy.RoutingError, "invalid JSON"):
                policy.create_snapshot(broken)
            link = root / "linked.json"
            try:
                link.symlink_to(broken)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            with self.assertRaisesRegex(policy.RoutingError, "linked"):
                policy.create_snapshot(link)

    def test_strict_json_and_pinned_root_reject_duplicate_nonfinite_and_nested_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
            with self.assertRaisesRegex(policy.RoutingError, "invalid JSON"):
                policy.create_snapshot(duplicate)
            nonfinite = root / "nonfinite.json"
            nonfinite.write_text('{"schema_version": NaN}', encoding="utf-8")
            with self.assertRaisesRegex(policy.RoutingError, "invalid JSON"):
                policy.create_snapshot(nonfinite)
            project = root / "project"
            project.mkdir()
            outside = root / "outside"
            outside.mkdir()
            try:
                (project / ".clanker").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            with self.assertRaisesRegex(policy.RoutingError, "linked"):
                policy.create_snapshot(project / ".clanker" / "orchestration-routing.json")

    def test_snapshot_rejects_recomputed_malformed_bundle_and_boolean_version(self):
        snapshot = policy.snapshot_from_documents(EMPTY)
        snapshot["schema_version"] = True
        snapshot["fingerprint"] = policy._sha256(policy._canonical_json(policy._snapshot_payload(snapshot)))
        with self.assertRaisesRegex(policy.RoutingError, "schema_version"):
            policy.validate_snapshot(snapshot)
        snapshot = policy.snapshot_from_documents(EMPTY)
        snapshot["bundle"]["models"] = "not-an-array"
        snapshot["hashes"]["bundle"] = policy._sha256(policy._canonical_json(snapshot["bundle"]))
        snapshot["fingerprint"] = policy._sha256(policy._canonical_json(policy._snapshot_payload(snapshot)))
        with self.assertRaisesRegex(policy.RoutingError, "models"):
            policy.validate_snapshot(snapshot)
    def test_cli_snapshot_is_exclusive_and_resolve_reads_snapshot_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            global_path = root / "global.json"
            snapshot_path = root / "project" / ".clanker" / "routing-snapshots" / "run-1.json"
            global_path.write_text(json.dumps(EMPTY), encoding="utf-8")
            command = [sys.executable, "-B", str(ROOT / "subagents" / "scripts" / "routing_policy.py")]
            obsolete = subprocess.run(command + ["snapshot", "--global", str(global_path), "--project", str(global_path)], text=True, capture_output=True)
            self.assertEqual(obsolete.returncode, 2)
            made = subprocess.run(command + ["snapshot", "--global", str(global_path), "--output", str(snapshot_path)], text=True, capture_output=True, check=True)
            self.assertTrue(snapshot_path.exists(), made.stderr)
            again = subprocess.run(command + ["snapshot", "--global", str(global_path), "--output", str(snapshot_path)], text=True, capture_output=True)
            self.assertEqual(again.returncode, 2)
            global_path.write_text(json.dumps({"schema_version": 1, "interactions": {"implementation": {"model": "gpt-5.6-luna"}}}), encoding="utf-8")
            result = subprocess.run(command + ["resolve", "--snapshot", str(snapshot_path)], input=json.dumps(request()), text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout)["model"], "gpt-5.6-terra")


if __name__ == "__main__":
    unittest.main()
