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
    def test_active_catalog_and_retired_ids_are_strict(self):
        retired = ("clanker-ux-designer", "clanker-documentation-writer", "clanker-product-engineer")
        bundle = policy.load_bundle()
        self.assertEqual({role["id"] for role in bundle["roles"]}, policy.NATIVE_ROLES)
        self.assertEqual(len(bundle["roles"]), 10)
        for role in retired:
            with self.subTest(role=role):
                for document, field in (
                    ({"schema_version": 1, "agents": {role: {"model": "gpt-5.6-sol"}}}, "agents." + role),
                    ({"schema_version": 1, "interactions": {"planning": {"specialists": {role: {"model": "gpt-5.6-sol"}}}}}, "specialists." + role),
                ):
                    original = copy.deepcopy(document)
                    with self.assertRaisesRegex(policy.RoutingError, field):
                        policy.snapshot_from_documents(document)
                    self.assertEqual(document, original)
                with self.assertRaisesRegex(policy.RoutingError, "request.role"):
                    policy.resolve(policy.snapshot_from_documents(EMPTY), request(role=role))
                altered = copy.deepcopy(bundle)
                altered["roles"][0]["id"] = role
                with self.assertRaisesRegex(policy.RoutingError, "10 active native roles"):
                    policy._validate_bundle_document(altered)

    def test_retained_roles_preserve_interaction_defaults(self):
        snapshot = policy.snapshot_from_documents(EMPTY)
        for interaction in policy.NATIVE_INTERACTIONS:
            baseline = policy.resolve(snapshot, request(interaction=interaction))
            for role in policy.NATIVE_ROLES:
                resolved = policy.resolve(snapshot, request(interaction=interaction, role=role))
                self.assertEqual((resolved["model"], resolved["effort"], resolved["provenance"]),
                                 (baseline["model"], baseline["effort"], baseline["provenance"]))

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
        current = {"schema_version": 1, "adaptive_profiles": {"codex:custom": {"tiers": {"straightforward": "medium", "involved": "high", "demanding": "xhigh"}}}}
        self.assertEqual(policy.validate_preferences(current), current)
        incomplete = {"schema_version": 1, "adaptive_profiles": {"codex:custom": {"tiers": {"straightforward": "medium", "involved": "high"}}}}
        with self.assertRaisesRegex(policy.RoutingError, "straightforward, involved, demanding"):
            policy.validate_preferences(incomplete)
        mixed = {"schema_version": 1, "adaptive_profiles": {"codex:custom": {"tiers": {"routine": "medium", "involved": "high", "demanding": "xhigh"}}}}
        with self.assertRaisesRegex(policy.RoutingError, "tiers"):
            policy.validate_preferences(mixed)
        invalid_retired_effort = {"schema_version": 1, "adaptive_profiles": {"codex:custom": {"tiers": {"mechanical": None, "routine": "medium", "complex": "high", "exceptional": "xhigh"}}}}
        with self.assertRaisesRegex(policy.RoutingError, "tiers.mechanical"):
            policy.validate_preferences(invalid_retired_effort)
        mismatch = {"schema_version": 1, "adaptive_profiles": {"codex:claude-opus-5": {"tiers": {tier: "high" for tier in policy.TIERS}}}}
        with self.assertRaisesRegex(policy.RoutingError, "belongs to claude"):
            policy.validate_preferences(mismatch)

    def test_policy_three_bundle_rejects_legacy_profile_vocabulary(self):
        bundle = policy.load_bundle()
        bundle["hosts"]["codex"]["defaults"]["adaptive_profiles"]["codex:gpt-5.6-terra"]["tiers"] = {
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
                "codex:custom-codex-v9": {"tiers": {"mechanical": "low", "routine": "medium", "complex": "max", "exceptional": "ultra"}},
                "claude:custom-claude-v9": {"tiers": {"mechanical": "low", "routine": "medium", "complex": "high", "exceptional": "max"}},
            },
        }
        original = copy.deepcopy(legacy)
        self.assertTrue(policy.needs_profile_migration(legacy))
        normalized = policy.validate_preferences(legacy)
        self.assertEqual(legacy, original)
        self.assertEqual(normalized["interactions"], original["interactions"])
        self.assertEqual(normalized["agents"], original["agents"])
        self.assertEqual(normalized["adaptive_profiles"], {
            "codex:custom-codex-v9": {"tiers": {"straightforward": "medium", "involved": "max", "demanding": "ultra"}},
            "claude:custom-claude-v9": {"tiers": {"straightforward": "medium", "involved": "high", "demanding": "max"}},
        })
        self.assertFalse(policy.needs_profile_migration(normalized))
        with self.assertRaisesRegex(policy.RoutingError, "tiers"):
            policy.needs_profile_migration({"schema_version": 1, "adaptive_profiles": {"codex:broken": {"tiers": {"routine": "medium", "involved": "high"}}}})

    def test_snapshot_normalizes_global_profiles_and_ignores_malformed_project_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            global_path, project_path = root / "global.json", root / "project.json"
            global_document = {"schema_version": 1, "adaptive_profiles": {"codex:custom-global": {"tiers": {"mechanical": "low", "routine": "medium", "complex": "high", "exceptional": "max"}}}}
            global_bytes = json.dumps(global_document).encode()
            global_path.write_bytes(global_bytes)
            project_path.write_text("not-json", encoding="utf-8")
            project_bytes = project_path.read_bytes()
            snapshot = policy.create_snapshot(global_path)
            self.assertEqual(snapshot["documents"]["global"]["adaptive_profiles"]["codex:custom-global"]["tiers"], {"straightforward": "medium", "involved": "high", "demanding": "max"})
            self.assertEqual(snapshot["hashes"]["global"], policy._sha256(global_bytes))
            self.assertEqual(snapshot["policy_version"], "7")
            self.assertEqual(snapshot["host"], "codex")
            self.assertEqual(set(snapshot["documents"]), {"global"})
            self.assertEqual(set(snapshot["sources"]), {"global"})
            self.assertEqual(set(snapshot["hashes"]), {"bundle", "global"})
            self.assertEqual(global_path.read_bytes(), global_bytes)
            self.assertEqual(project_path.read_bytes(), project_bytes)


class ResolutionTests(unittest.TestCase):
    def test_effective_display_has_no_ceiling_fields(self):
        for mode in ("adaptive", "fixed"):
            reasoning = {"mode": mode, **({"effort": "high"} if mode == "fixed" else {})}
            prefs = {"schema_version": 1, "interactions": {"implementation": {"reasoning": reasoning}}}
            snapshot = policy.snapshot_from_documents(prefs)
            effective = policy.effective_configuration(snapshot)
            route = effective["interactions"]["implementation"]
            self.assertEqual(route["route"]["reasoning"], reasoning)
            for entry in [route, *route["specialists"].values()]:
                self.assertNotIn("ceiling", entry)
                self.assertNotIn("ceiling_source", entry)
            decision = policy.resolve(snapshot, request())
            self.assertEqual(decision["effort"], decision["proposed_effort"])
            self.assertNotIn("ceiling", decision)
            self.assertNotIn("ceiling_source", decision)

    def snapshot(self, global_document=None):
        return policy.snapshot_from_documents(global_document or EMPTY, sources={"global": "global.json"})

    def test_astra_planning_adaptive_uses_bundled_profile_without_user_profile(self):
        prefs = {"schema_version": 1, "interactions": {"planning": {"model": "gpt-6-astra"}}}
        snapshot = self.snapshot(prefs)
        effective = policy.effective_configuration(snapshot)["interactions"]["planning"]
        self.assertEqual(effective["route"]["model"], "gpt-6-astra")
        for tier, effort in {"straightforward": "medium", "involved": "high", "demanding": "xhigh"}.items():
            with self.subTest(tier=tier):
                result = policy.resolve(snapshot, request(interaction="planning", tier=tier))
                self.assertEqual(result["effort"], effort)
                self.assertEqual(result["provenance"]["profile"], "bundle.defaults.adaptive_profiles.codex:gpt-6-astra")
                self.assertFalse(result["dispatch_allowed"])

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
        global_document = {"schema_version": 1, "interactions": {"implementation": {"reasoning": {"mode": "adaptive"}}}}
        global_document["agents"] = {"clanker-backend-developer": {"model": "gpt-5.6-luna"}}
        decision = policy.resolve(self.snapshot(global_document), request(role="clanker-backend-developer", tier="demanding", capabilities=NATIVE_CAPABILITIES))
        self.assertEqual((decision["model"], decision["effort"]), ("gpt-5.6-luna", "max"))
        self.assertEqual(decision["provenance"]["reasoning"], "global.interactions.implementation.reasoning")

    def test_retired_fields_are_rejected_at_every_input_location(self):
        bad = {"mode": "adaptive", "max_effort": "high"}
        documents = [
            {"schema_version": 1, "interactions": {"implementation": {"reasoning": bad}}},
            {"schema_version": 1, "agents": {"clanker-backend-developer": {"reasoning": bad}}},
            {"schema_version": 1, "interactions": {"implementation": {"specialists": {"clanker-backend-developer": {"reasoning": bad}}}}},
        ]
        for document in documents:
            with self.subTest(document=document), self.assertRaisesRegex(policy.RoutingError, "max_effort: is not supported"):
                self.snapshot(document)
        with self.assertRaisesRegex(policy.RoutingError, "request.session_override.reasoning.max_effort"):
            policy.resolve(self.snapshot(), request(session_override={"reasoning": bad}))
        for tiers in ({"straightforward": "medium", "involved": "high", "demanding": "max"},
                      {"mechanical": "low", "routine": "medium", "complex": "high", "exceptional": "max"}):
            document = {"schema_version": 1, "adaptive_profiles": {"codex:custom": {"tiers": tiers, "default_ceiling": "high"}}}
            with self.subTest(tiers=tiers), self.assertRaisesRegex(policy.RoutingError, "default_ceiling: is not supported"):
                self.snapshot(document)

    def test_custom_tiers_are_requested_exactly_without_an_implicit_cap(self):
        tiers = {"straightforward": "max", "involved": "medium", "demanding": "high"}
        document = {"schema_version": 1, "interactions": {"implementation": {"model": "custom-model"}},
                    "adaptive_profiles": {"codex:custom-model": {"tiers": tiers}}}
        snapshot = self.snapshot(document)
        for tier, effort in tiers.items():
            capabilities = {"provider": "codex", "source": "fixture", "models": {"custom-model": [effort]}}
            decision = policy.resolve(snapshot, request(tier=tier, capabilities=capabilities))
            self.assertEqual((decision["effort"], decision["proposed_effort"]), (effort, effort))
            self.assertTrue(decision["dispatch_allowed"])
        unsupported = policy.resolve(snapshot, request(tier="straightforward", capabilities={"provider": "codex", "source": "fixture", "models": {"custom-model": ["high"]}}))
        self.assertEqual((unsupported["effort"], unsupported["capability_status"], unsupported["dispatch_allowed"]), ("max", "unsupported", False))

    def test_adaptive_tier_maps_risks_and_fixed_limitations(self):
        luna = {"schema_version": 1, "interactions": {"implementation": {"model": "gpt-5.6-luna"}}}
        for tier, expected in (("straightforward", "high"), ("involved", "xhigh"), ("demanding", "max")):
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
    def test_policy_five_catalog_replay_preserves_the_snapshot(self):
        snapshot = policy.snapshot_from_documents(EMPTY)
        snapshot["policy_version"] = snapshot["bundle"]["policy_version"] = "5"
        snapshot["bundle"]["roles"].extend([
            {"id": "clanker-documentation-writer", "label": "Documentation writer"},
            {"id": "clanker-product-engineer", "label": "Product engineer"},
            {"id": "clanker-ux-designer", "label": "UX designer"},
        ])
        snapshot["bundle"]["roles"].sort(key=lambda role: role["id"])
        snapshot["hashes"]["bundle"] = policy._sha256(policy._canonical_json(snapshot["bundle"]))
        snapshot["fingerprint"] = policy._sha256(policy._canonical_json(policy._snapshot_payload(snapshot)))
        original = copy.deepcopy(snapshot)
        for operation in (policy.validate_snapshot, policy.effective_configuration,
                          lambda value: policy.resolve(value, request())):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(policy.RoutingError, "Start a new run"):
                    operation(snapshot)
                self.assertEqual(snapshot, original)

    def test_old_and_unknown_snapshots_require_a_new_run(self):
        for version in ("1", "2", "3", "4", "5", "6", "8", []):
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
        for unsupported in ([], "6", "8"):
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
            "codex:custom": {"tiers": {"mechanical": "low", "routine": "medium", "complex": "high", "exceptional": "xhigh"}}
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


CLAUDE_CAPABILITIES = {
    "provider": "claude",
    "source": "active Agent tool model list, transcribed by the parent",
    "models": {"sonnet": ["low", "medium", "high", "xhigh", "max"], "haiku": ["low", "medium", "high", "xhigh", "max"]},
}


def claude_snapshot(document=None):
    return policy.snapshot_from_documents(document or EMPTY, sources={"global": "claude.json"}, host="claude")


def policy_six_snapshot():
    """Rebuild the policy-6 snapshot shape: no host, flat interactions and defaults."""
    snapshot = policy.snapshot_from_documents(EMPTY)
    codex_host = snapshot["bundle"].pop("hosts")["codex"]
    snapshot["bundle"]["interactions"] = [
        {"id": item["id"], "label": item["label"], "provider": "claude" if item["execution"] == "external" else "codex",
         "default_model": item["default_model"]} for item in codex_host["interactions"]]
    snapshot["bundle"]["defaults"] = codex_host["defaults"]
    snapshot["bundle"]["policy_version"] = snapshot["policy_version"] = "6"
    del snapshot["host"]
    snapshot["hashes"]["bundle"] = policy._sha256(policy._canonical_json(snapshot["bundle"]))
    snapshot["fingerprint"] = policy._sha256(policy._canonical_json(policy._snapshot_payload(snapshot)))
    return snapshot


class HostIdentityTests(unittest.TestCase):
    def test_bundle_defines_both_host_catalogs(self):
        bundle = policy.load_bundle()
        self.assertEqual(bundle["policy_version"], "7")
        self.assertEqual(set(bundle["hosts"]), {"codex", "claude"})
        self.assertEqual([item["id"] for item in bundle["hosts"]["codex"]["interactions"]],
                         ["planning", "implementation", "native-review", "visual-review", "claude-review"])
        self.assertEqual([item["id"] for item in bundle["hosts"]["claude"]["interactions"]],
                         ["planning", "implementation", "native-review", "visual-review", "codex-review"])
        self.assertEqual([item["execution"] for item in bundle["hosts"]["claude"]["interactions"]], ["native"] * 4 + ["external"])
        models = {item["id"]: item["provider"] for item in bundle["models"]}
        self.assertEqual((models["sonnet"], models["haiku"], models["gpt-6.1-sol"]), ("claude", "claude", "codex"))

    def test_malformed_host_catalogs_are_rejected(self):
        for mutate, fragment in (
            (lambda bundle: bundle["hosts"].pop("claude"), "hosts"),
            (lambda bundle: bundle["hosts"]["claude"]["interactions"].reverse(), "interactions"),
            (lambda bundle: bundle["hosts"]["claude"]["interactions"][4].update(execution="native"), "execution"),
            (lambda bundle: bundle["hosts"]["codex"]["defaults"]["interactions"].pop("claude-review"), "claude-review"),
            (lambda bundle: bundle["hosts"]["claude"]["defaults"]["interactions"].update({"claude-review": {"model": "opus"}}), "claude-review"),
            (lambda bundle: bundle.update(interactions=[]), "interactions"),
        ):
            bundle = policy.load_bundle()
            mutate(bundle)
            with self.subTest(fragment=fragment), self.assertRaisesRegex(policy.RoutingError, fragment):
                policy._validate_bundle_document(bundle)

    def test_claude_host_defaults_are_adaptive_and_unverified(self):
        snapshot = claude_snapshot()
        expected = {"planning": "sonnet", "implementation": "haiku", "native-review": "sonnet", "visual-review": "sonnet", "codex-review": "gpt-6.1-sol"}
        for interaction, model in expected.items():
            for tier, effort in {"straightforward": "medium", "involved": "high", "demanding": "high" if model != "gpt-6.1-sol" else "xhigh"}.items():
                with self.subTest(interaction=interaction, tier=tier):
                    decision = policy.resolve(snapshot, request(interaction=interaction, tier=tier))
                    self.assertEqual((decision["model"], decision["effort"], decision["reasoning"]), (model, effort, {"mode": "adaptive"}))
                    self.assertEqual(decision["provenance"]["model"], "bundle.defaults")
                    self.assertFalse(decision["dispatch_allowed"])
                    self.assertEqual(decision["capability_status"], "requires_launcher_preflight" if interaction == "codex-review" else "unverified")
        self.assertEqual(policy.resolve(snapshot, request(interaction="codex-review"))["provenance"]["profile"],
                         "bundle.defaults.adaptive_profiles.codex:gpt-6.1-sol")

    def test_decisions_and_effective_configuration_report_identity(self):
        codex = policy.snapshot_from_documents(EMPTY)
        self.assertEqual(codex["host"], "codex")
        native = policy.resolve(codex, request())
        external = policy.resolve(codex, request(interaction="claude-review"))
        self.assertEqual([(item["host"], item["provider"], item["execution"]) for item in (native, external)],
                         [("codex", "codex", "native"), ("codex", "claude", "external")])
        claude = claude_snapshot()
        native = policy.resolve(claude, request())
        external = policy.resolve(claude, request(interaction="codex-review"))
        self.assertEqual([(item["host"], item["provider"], item["execution"]) for item in (native, external)],
                         [("claude", "claude", "native"), ("claude", "codex", "external")])
        effective = policy.effective_configuration(claude)
        self.assertEqual(effective["host"], "claude")
        self.assertEqual(list(effective["interactions"]), ["planning", "implementation", "native-review", "visual-review", "codex-review"])
        self.assertEqual([(entry["provider"], entry["execution"]) for entry in effective["interactions"].values()],
                         [("claude", "native")] * 4 + [("codex", "external")])
        self.assertEqual(set(effective["profiles"]), {"claude:sonnet", "claude:haiku", "claude:opus", "codex:gpt-6.1-sol"})
        self.assertEqual(effective["interactions"]["implementation"]["specialists"]["clanker-backend-developer"]["route"]["model"], "haiku")

    def test_codex_host_profiles_are_not_widened_by_claude_host_profiles(self):
        codex = policy.snapshot_from_documents({"schema_version": 1, "interactions": {"planning": {"model": "gpt-6.1-sol"}}})
        with self.assertRaisesRegex(policy.RoutingError, "requires a complete profile"):
            policy.resolve(codex, request(interaction="planning"))
        self.assertNotIn("codex:gpt-6.1-sol", policy.effective_configuration(policy.snapshot_from_documents(EMPTY))["profiles"])
        fixed = {"schema_version": 1, "interactions": {"planning": {"model": "gpt-6.1-sol", "reasoning": {"mode": "fixed", "effort": "low"}}}}
        decision = policy.resolve(policy.snapshot_from_documents(fixed), request(interaction="planning", tier="demanding"))
        self.assertEqual((decision["effort"], decision["provenance"]["profile"], decision["limitations"][:1]),
                         ("low", None, ["No native runtime capability metadata was supplied"]))

    def test_wrong_provider_models_are_rejected_at_their_field(self):
        cases = [
            ("claude", {"schema_version": 1, "interactions": {"implementation": {"model": "gpt-5.6-luna"}}}, "interactions.implementation.model: belongs to codex, not claude"),
            ("claude", {"schema_version": 1, "agents": {"clanker-backend-developer": {"model": "gpt-5.6-terra"}}}, "agents.clanker-backend-developer.model: belongs to codex, not claude"),
            ("claude", {"schema_version": 1, "interactions": {"codex-review": {"model": "opus"}}}, "interactions.codex-review.model: belongs to claude, not codex"),
            ("codex", {"schema_version": 1, "interactions": {"implementation": {"model": "haiku"}}}, "interactions.implementation.model: belongs to claude, not codex"),
        ]
        for host, document, fragment in cases:
            with self.subTest(fragment=fragment), self.assertRaisesRegex(policy.RoutingError, fragment):
                policy.snapshot_from_documents(document, host=host)

    def test_cross_host_interaction_keys_are_rejected(self):
        with self.assertRaisesRegex(policy.RoutingError, r"global\.interactions\.claude-review: is not supported by the claude host"):
            policy.snapshot_from_documents({"schema_version": 1, "interactions": {"claude-review": {"model": "opus"}}}, host="claude")
        with self.assertRaisesRegex(policy.RoutingError, r"global\.interactions\.codex-review: is not supported by the codex host"):
            policy.snapshot_from_documents({"schema_version": 1, "interactions": {"codex-review": {"model": "gpt-6.1-sol"}}}, host="codex")
        with self.assertRaisesRegex(policy.RoutingError, "request.interaction"):
            policy.resolve(claude_snapshot(), request(interaction="claude-review"))
        with self.assertRaisesRegex(policy.RoutingError, "request.interaction"):
            policy.resolve(policy.snapshot_from_documents(EMPTY), request(interaction="codex-review"))
        with self.assertRaisesRegex(policy.RoutingError, "request.role: is not allowed for codex-review"):
            policy.resolve(claude_snapshot(), request(interaction="codex-review", role="clanker-architect"))

    def test_claude_native_agent_default_resolves_with_provenance(self):
        document = {"schema_version": 1, "agents": {"clanker-backend-developer": {"model": "haiku", "reasoning": {"mode": "adaptive"}}},
                    "interactions": {"planning": {"model": "opus"}}}
        snapshot = claude_snapshot(document)
        for interaction in ("planning", "implementation", "native-review", "visual-review"):
            decision = policy.resolve(snapshot, request(interaction=interaction, role="clanker-backend-developer"))
            self.assertEqual(decision["model"], "haiku")
            self.assertEqual(decision["provenance"]["model"], "global.agents.clanker-backend-developer.model")
        self.assertEqual(policy.resolve(snapshot, request(interaction="planning"))["model"], "opus")

    def test_host_is_validated_and_covered_by_the_fingerprint(self):
        with self.assertRaisesRegex(policy.RoutingError, "host"):
            policy.snapshot_from_documents(EMPTY, host="windsurf")
        codex, claude = policy.snapshot_from_documents(EMPTY), claude_snapshot()
        self.assertNotEqual(codex["fingerprint"], claude["fingerprint"])
        tampered = copy.deepcopy(codex)
        tampered["host"] = "claude"
        with self.assertRaisesRegex(policy.RoutingError, "fingerprint"):
            policy.validate_snapshot(tampered)
        tampered["host"] = "other"
        tampered["fingerprint"] = policy._sha256(policy._canonical_json(policy._snapshot_payload(tampered)))
        with self.assertRaisesRegex(policy.RoutingError, "snapshot.host"):
            policy.validate_snapshot(tampered)

    def test_policy_six_snapshot_requires_a_new_run(self):
        snapshot = policy_six_snapshot()
        original = copy.deepcopy(snapshot)
        for operation in (policy.validate_snapshot, policy.effective_configuration, lambda value: policy.resolve(value, request())):
            with self.subTest(operation=operation), self.assertRaisesRegex(policy.RoutingError, "Start a new run"):
                operation(snapshot)
            self.assertEqual(snapshot, original)


class HostPreferenceSourceTests(unittest.TestCase):
    def write(self, path, document):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = (json.dumps(document) + "\n").encode()
        path.write_bytes(data)
        return data

    def test_each_host_reads_only_its_own_file(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / ".clanker"
            codex_path, claude_path = home / "orchestration-routing.json", home / "orchestration-routing-claude.json"
            codex_bytes = self.write(codex_path, {"schema_version": 1, "interactions": {"planning": {"model": "gpt-6.1-sol", "reasoning": {"mode": "fixed", "effort": "high"}}}})
            claude_bytes = self.write(claude_path, {"schema_version": 1, "interactions": {"implementation": {"model": "sonnet"}}})
            claude = policy.create_snapshot(claude_path, host="claude")
            codex = policy.create_snapshot(codex_path)
            self.assertEqual((claude["host"], claude["sources"]["global"], codex["host"], codex["sources"]["global"]),
                             ("claude", str(claude_path), "codex", str(codex_path)))
            self.assertEqual(policy.resolve(claude, request(interaction="implementation"))["model"], "sonnet")
            self.assertEqual(policy.resolve(claude, request(interaction="planning"))["model"], "sonnet")
            self.assertEqual(policy.resolve(codex, request(interaction="planning"))["model"], "gpt-6.1-sol")
            self.assertEqual((codex_path.read_bytes(), claude_path.read_bytes()), (codex_bytes, claude_bytes))

    def test_missing_claude_file_uses_bundled_defaults_without_touching_codex_file(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / ".clanker"
            codex_bytes = self.write(home / "orchestration-routing.json", {"schema_version": 1, "interactions": {"implementation": {"model": "gpt-5.6-luna"}}})
            snapshot = policy.create_snapshot(home / "orchestration-routing-claude.json", host="claude")
            self.assertEqual((snapshot["documents"]["global"], snapshot["hashes"]["global"]), (None, None))
            self.assertEqual(policy.resolve(snapshot, request())["model"], "haiku")
            self.assertEqual((home / "orchestration-routing.json").read_bytes(), codex_bytes)
            self.assertFalse((home / "orchestration-routing-claude.json").exists())

    def test_existing_codex_preferences_resolve_identically_after_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".clanker" / "orchestration-routing.json"
            data = self.write(path, {"schema_version": 1, "interactions": {"implementation": {"model": "gpt-6-luna", "reasoning": {"mode": "adaptive"}}},
                                      "adaptive_profiles": {"codex:gpt-6-luna": {"tiers": {"straightforward": "medium", "involved": "xhigh", "demanding": "max"}}}})
            snapshot = policy.create_snapshot(path)
            decision = policy.resolve(snapshot, request(tier="involved"))
            self.assertEqual((decision["model"], decision["effort"], decision["host"]), ("gpt-6-luna", "xhigh", "codex"))
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(sorted(path.parent.iterdir()), [path])


class InstalledHostConfigTests(unittest.TestCase):
    CODEX = {"schema_version": 1, "host": "codex", "preferences_file": "orchestration-routing.json",
             "external_review": {"interaction": "claude-review", "launcher": "scripts/claude_cross_review.py"}}
    CLAUDE = {"schema_version": 1, "host": "claude", "preferences_file": "orchestration-routing-claude.json",
              "external_review": {"interaction": "codex-review", "launcher": "scripts/codex_cross_review.py"}}

    def install(self, config):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "routing" / "host.json"
        path.parent.mkdir()
        if config is not None:
            path.write_text(json.dumps(config), encoding="utf-8")
        original = policy._host_config_path
        policy._host_config_path = lambda: path
        self.addCleanup(setattr, policy, "_host_config_path", original)
        return Path(directory.name)

    def test_shipped_host_configurations_validate(self):
        for host in ("codex", "claude"):
            config = policy.load_host_config(ROOT / "subagents" / "hosts" / host / "host.json")
            self.assertEqual(config, {"codex": self.CODEX, "claude": self.CLAUDE}[host])

    def test_absent_configuration_defaults_to_codex_and_honors_explicit_host(self):
        root = self.install(None)
        self.assertIsNone(policy.load_host_config())
        self.assertEqual(policy.create_snapshot(root / "anything.json")["host"], "codex")
        self.assertEqual(policy.create_snapshot(root / "anything.json", host="claude")["host"], "claude")

    def test_installed_host_is_the_snapshot_default_and_names_its_source(self):
        for config, other in ((self.CODEX, "claude"), (self.CLAUDE, "codex")):
            root = self.install(config)
            path = root / ".clanker" / config["preferences_file"]
            snapshot = policy.create_snapshot(path)
            self.assertEqual((snapshot["host"], snapshot["sources"]["global"]), (config["host"], str(path)))
            self.assertEqual(policy.create_snapshot(path, host=config["host"])["host"], config["host"])
            with self.assertRaisesRegex(policy.RoutingError, "contradicts the installed host configuration"):
                policy.create_snapshot(path, host=other)

    def test_contradictory_host_fails_before_reading_either_file(self):
        root = self.install(self.CODEX)
        broken = root / ".clanker" / "orchestration-routing-claude.json"
        broken.parent.mkdir()
        broken.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(policy.RoutingError, "contradicts the installed host configuration"):
            policy.create_snapshot(broken, host="claude")
        with self.assertRaisesRegex(policy.RoutingError, "installed host's preference file orchestration-routing.json"):
            policy.create_snapshot(broken)

    def test_invalid_configurations_are_rejected_strictly(self):
        def variant(**changes):
            config = copy.deepcopy(self.CLAUDE)
            for key, value in changes.items():
                if key.startswith("review_"):
                    config["external_review"][key[7:]] = value
                else:
                    config[key] = value
            return config
        cases = [
            (variant(host="windsurf"), "host_config.host"),
            (variant(preferences_file="orchestration-routing.json"), "preferences_file"),
            (variant(preferences_file="../orchestration-routing-claude.json"), "preferences_file"),
            (variant(review_interaction="claude-review"), "external_review.interaction"),
            (variant(review_launcher="../scripts/codex_cross_review.py"), "launcher"),
            (variant(review_launcher="/abs/codex_cross_review.py"), "launcher"),
            (variant(review_launcher="scripts/codex_cross_review.sh"), "launcher"),
            (variant(schema_version=2), "schema_version"),
            (variant(extra=True), "extra"),
            ({key: value for key, value in self.CLAUDE.items() if key != "host"}, "missing required fields"),
        ]
        for config, fragment in cases:
            root = self.install(config)
            with self.subTest(fragment=fragment, config=config), self.assertRaisesRegex(policy.RoutingError, fragment):
                policy.create_snapshot(root / "orchestration-routing-claude.json")
        root = self.install(self.CLAUDE)
        (root / "routing" / "host.json").write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(policy.RoutingError, "host_config"):
            policy.create_snapshot(root / "orchestration-routing-claude.json")

    def test_cli_snapshot_accepts_explicit_host_and_rejects_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "orchestration-routing-claude.json"
            path.write_text(json.dumps(EMPTY), encoding="utf-8")
            command = [sys.executable, "-B", str(ROOT / "subagents" / "scripts" / "routing_policy.py")]
            made = subprocess.run(command + ["snapshot", "--global", str(path), "--host", "claude", "--output", str(root / "run" / "claude-1.json")],
                                  text=True, capture_output=True, check=True)
            snapshot = json.loads(made.stdout)
            self.assertEqual((snapshot["host"], snapshot["sources"]["global"]), ("claude", str(path)))
            resolved = subprocess.run(command + ["resolve", "--snapshot", str(root / "run" / "claude-1.json")],
                                      input=json.dumps(request(interaction="codex-review")), text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(resolved.stdout)["provider"], "codex")
            rejected = subprocess.run(command + ["snapshot", "--global", str(path), "--host", "windsurf"], text=True, capture_output=True)
            self.assertEqual(rejected.returncode, 2)


class ClaudeNativeGateTests(unittest.TestCase):
    def test_advertised_alias_pair_is_dispatchable(self):
        decision = policy.resolve(claude_snapshot(), request(role="clanker-backend-developer", capabilities=CLAUDE_CAPABILITIES))
        self.assertEqual((decision["model"], decision["effort"], decision["capability_status"], decision["dispatch_allowed"]),
                         ("haiku", "medium", "supported", True))
        self.assertEqual(decision["limitations"], [])
        self.assertNotIn("launcher_allowed", decision)

    def test_exact_model_id_is_blocked_without_alias_substitution(self):
        document = {"schema_version": 1, "interactions": {"implementation": {"model": "claude-sonnet-5-5", "reasoning": {"mode": "fixed", "effort": "high"}}}}
        decision = policy.resolve(claude_snapshot(document), request(capabilities=CLAUDE_CAPABILITIES))
        self.assertEqual((decision["model"], decision["effort"], decision["capability_status"], decision["dispatch_allowed"]),
                         ("claude-sonnet-5-5", "high", "unsupported", False))
        self.assertEqual(decision["limitations"], ["Native runtime does not advertise claude-sonnet-5-5/high"])

    def test_unadvertised_effort_and_missing_metadata_block_dispatch(self):
        narrow = {**CLAUDE_CAPABILITIES, "models": {"haiku": ["low", "medium"]}}
        blocked = policy.resolve(claude_snapshot(), request(tier="demanding", capabilities=narrow))
        self.assertEqual((blocked["effort"], blocked["capability_status"], blocked["dispatch_allowed"]), ("high", "unsupported", False))
        unlisted = policy.resolve(claude_snapshot(), request(capabilities={"provider": "claude", "source": "fixture"}))
        self.assertEqual((unlisted["capability_status"], unlisted["dispatch_allowed"]), ("unverified", False))
        with self.assertRaisesRegex(policy.RoutingError, "does not match claude route"):
            policy.resolve(claude_snapshot(), request(capabilities=NATIVE_CAPABILITIES))

    def test_reported_overrides_block_dispatch_and_name_the_setting(self):
        for overrides in (["CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1"], ["CLAUDE_CODE_EFFORT_LEVEL", "agent.spawn hook"]):
            for capabilities in (CLAUDE_CAPABILITIES, None):
                with self.subTest(overrides=overrides, capabilities=capabilities is not None):
                    decision = policy.resolve(claude_snapshot(), request(overrides=overrides, **({"capabilities": capabilities} if capabilities else {})))
                    self.assertEqual((decision["model"], decision["effort"]), ("haiku", "medium"))
                    self.assertEqual((decision["capability_status"], decision["dispatch_allowed"]), ("blocked_by_override", False))
                    self.assertEqual(decision["overrides"], overrides)
                    self.assertTrue(any(all(name in item for name in overrides) for item in decision["limitations"]), decision["limitations"])
        clean = policy.resolve(claude_snapshot(), request(overrides=[], capabilities=CLAUDE_CAPABILITIES))
        self.assertTrue(clean["dispatch_allowed"])
        self.assertNotIn("overrides", clean)

    def test_overrides_must_be_unique_setting_names(self):
        for bad in ("CLAUDE_CODE_EFFORT_LEVEL", [""], [1], ["A", "A"], ["x" * 201]):
            with self.subTest(bad=bad), self.assertRaisesRegex(policy.RoutingError, "request.overrides"):
                policy.resolve(claude_snapshot(), request(overrides=bad))

    def test_codex_review_needs_launcher_preflight_not_native_capabilities(self):
        snapshot = claude_snapshot()
        pending = policy.resolve(snapshot, request(interaction="codex-review", tier="involved", reason="Independent plan review"))
        self.assertEqual((pending["capability_status"], pending["launcher_allowed"], pending["dispatch_allowed"]), ("requires_launcher_preflight", True, False))
        self.assertEqual(pending["limitations"], ["Codex route requires the guarded launcher preflight before any model call"])
        validated = policy.resolve(snapshot, request(interaction="codex-review", tier="involved", reason="Independent plan review",
                                                     capabilities={"provider": "codex", "source": "launcher", "preflight_valid": True}))
        self.assertEqual((validated["capability_status"], validated["account_status"], validated["dispatch_allowed"]), ("preflight_valid", "unverified", True))
        unsupported = policy.resolve(snapshot, request(interaction="codex-review", tier="involved", reason="Independent plan review",
                                                       capabilities={"provider": "codex", "source": "launcher", "models": {"gpt-6.1-sol": ["low"]}, "preflight_valid": True}))
        self.assertEqual((unsupported["capability_status"], unsupported["dispatch_allowed"]), ("unsupported", False))
        with self.assertRaisesRegex(policy.RoutingError, "does not match codex route"):
            policy.resolve(snapshot, request(interaction="codex-review", capabilities={"provider": "claude", "source": "native tools", "models": {"sonnet": ["high"]}}))

    def test_overrides_block_codex_host_routes_too(self):
        decision = policy.resolve(policy.snapshot_from_documents(EMPTY), request(overrides=["example-setting"], capabilities=NATIVE_CAPABILITIES))
        self.assertEqual((decision["capability_status"], decision["dispatch_allowed"]), ("blocked_by_override", False))


class FixRoundPolicyTests(unittest.TestCase):
    def test_other_host_preference_file_is_rejected_without_installed_host_config(self):
        original = policy._host_config_path
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy._host_config_path = lambda: root / "missing-host.json"
            try:
                codex, claude = root / "orchestration-routing.json", root / "orchestration-routing-claude.json"
                for path in (codex, claude):
                    path.write_text(json.dumps(EMPTY), encoding="utf-8")
                for host, wrong, right in (("codex", claude, codex), ("claude", codex, claude), (None, claude, codex)):
                    with self.subTest(host=host, file=wrong.name):
                        with self.assertRaisesRegex(policy.RoutingError, "preference file, not the"):
                            policy.create_snapshot(wrong, host=host)
                        self.assertEqual(policy.create_snapshot(right, host=host)["host"], host or "codex")
                self.assertEqual(policy.create_snapshot(root / "any-name.json", host="claude")["host"], "claude")
                self.assertEqual(policy.create_snapshot(root / "any-name.json")["host"], "codex")
                command = [sys.executable, "-B", str(ROOT / "subagents" / "scripts" / "routing_policy.py"), "snapshot"]
                cli = subprocess.run([*command, "--host", "codex", "--global", str(claude)], text=True, capture_output=True)
                self.assertEqual(cli.returncode, 2)
                self.assertIn("claude host's preference file", cli.stderr)
            finally:
                policy._host_config_path = original

    def test_host_config_launcher_must_match_the_host(self):
        for host, wrong in (("codex", "scripts/codex_cross_review.py"), ("claude", "scripts/claude_cross_review.py")):
            config = copy.deepcopy(InstalledHostConfigTests.CODEX if host == "codex" else InstalledHostConfigTests.CLAUDE)
            config["external_review"]["launcher"] = wrong
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "host.json"
                path.write_text(json.dumps(config), encoding="utf-8")
                with self.subTest(host=host), self.assertRaisesRegex(policy.RoutingError, "launcher: must be scripts/"):
                    policy.load_host_config(path)

    def test_overrides_are_rejected_for_external_interactions_only(self):
        for snapshot, interaction in ((policy.snapshot_from_documents(EMPTY), "claude-review"), (claude_snapshot(), "codex-review")):
            with self.subTest(interaction=interaction):
                with self.assertRaisesRegex(policy.RoutingError, "request.overrides"):
                    policy.resolve(snapshot, request(interaction=interaction, overrides=["CLAUDE_CODE_EFFORT_LEVEL"]))
                clean = policy.resolve(snapshot, request(interaction=interaction, overrides=[]))
                self.assertNotIn("overrides", clean)
        native = policy.resolve(claude_snapshot(), request(overrides=["CLAUDE_CODE_EFFORT_LEVEL"]))
        self.assertEqual(native["capability_status"], "blocked_by_override")

    def test_bundle_default_model_must_match_host_defaults(self):
        for host, interaction in (("codex", 1), ("claude", 4)):
            bundle = policy.load_bundle()
            bundle["hosts"][host]["interactions"][interaction]["default_model"] = "drifted-model"
            with self.subTest(host=host), self.assertRaisesRegex(policy.RoutingError, r"interactions\[%d\]\.default_model: must equal the host default model" % interaction):
                policy._validate_bundle_document(bundle)

    def test_wrong_provider_models_are_rejected_in_specialists_and_profile_keys(self):
        cases = (
            ("claude", {"schema_version": 1, "interactions": {"planning": {"specialists": {"clanker-architect": {"model": "gpt-5.6-sol"}}}}}, "specialists.clanker-architect.model: belongs to codex, not claude"),
            ("codex", {"schema_version": 1, "interactions": {"planning": {"specialists": {"clanker-architect": {"model": "haiku"}}}}}, "specialists.clanker-architect.model: belongs to claude, not codex"),
            ("claude", {"schema_version": 1, "adaptive_profiles": {"claude:gpt-6.1-sol": {"tiers": {tier: "high" for tier in policy.TIERS}}}}, "adaptive_profiles.claude:gpt-6.1-sol: model belongs to codex"),
            ("claude", {"schema_version": 1, "adaptive_profiles": {"codex:haiku": {"tiers": {tier: "high" for tier in policy.TIERS}}}}, "adaptive_profiles.codex:haiku: model belongs to claude"),
            ("codex", {"schema_version": 1, "adaptive_profiles": {"codex:haiku": {"tiers": {tier: "high" for tier in policy.TIERS}}}}, "adaptive_profiles.codex:haiku: model belongs to claude"),
        )
        for host, document, fragment in cases:
            with self.subTest(fragment=fragment), self.assertRaisesRegex(policy.RoutingError, fragment):
                policy.snapshot_from_documents(document, host=host)


if __name__ == "__main__":
    unittest.main()
