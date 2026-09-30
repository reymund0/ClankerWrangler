#!/usr/bin/env python3
"""Deterministic routing-policy validation, snapshots, and resolution.

The module intentionally has no model, shell, or third-party-library integration.
It produces a requested route and an honest capability gate for its caller to act on.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping


SCHEMA_VERSION = 1
POLICY_VERSION = "2"
LEGACY_POLICY_VERSION = "1"
SUPPORTED_POLICY_VERSIONS = frozenset((LEGACY_POLICY_VERSION, POLICY_VERSION))
INTERACTIONS = ("planning", "implementation", "native-review", "visual-review", "claude-review")
NATIVE_INTERACTIONS = frozenset(INTERACTIONS[:-1])
TIERS = ("mechanical", "routine", "complex", "exceptional")
RISK_FLAGS = frozenset(("security", "data-integrity", "recovery", "cross-layer", "uncertainty", "performance"))
CONSEQUENTIAL_FLAGS = frozenset(("security", "data-integrity", "recovery"))
MAX_JSON_BYTES = 1_048_576


class RoutingError(ValueError):
    """A malformed policy input or an unresolved routing request."""


def _error(path: str, message: str) -> RoutingError:
    return RoutingError(f"{path}: {message}")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _policy_path() -> Path:
    return Path(__file__).resolve().parent.parent / "routing" / "policy.json"


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON values are not supported")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_json_bytes(raw: bytes, field: str) -> Any:
    if len(raw) > MAX_JSON_BYTES:
        raise _error(field, "JSON document is too large")
    try:
        return json.loads(raw.decode("utf-8-sig"), parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    except UnicodeDecodeError as exc:
        raise _error(field, "must be UTF-8 JSON") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        detail = f" at line {exc.lineno}, column {exc.colno}" if isinstance(exc, json.JSONDecodeError) else ""
        raise _error(field, f"invalid JSON{detail}") from exc


def _read_json(path: Path, field: str) -> Any:
    try:
        return _parse_json_bytes(path.read_bytes(), field)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise _error(field, "could not be read") from exc


def _is_link(path: Path) -> bool:
    try:
        value = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise _error(str(path), "could not inspect link status") from exc
    return stat.S_ISLNK(value.st_mode) or bool(getattr(value, "st_file_attributes", 0) & 0x400)


def _assert_no_link_components(path: Path) -> None:
    """Pin an explicit config root, allowing its canonical root but no links beneath it."""
    absolute = path.absolute()
    parts = absolute.parts
    try:
        clanker_index = next(index for index, part in enumerate(parts) if part == ".clanker")
    except StopIteration:
        lexical_root = absolute.parent
    else:
        lexical_root = Path(*parts[:clanker_index])
    try:
        pinned_root = lexical_root.resolve(strict=False)
        relative = absolute.relative_to(lexical_root)
    except (OSError, ValueError) as exc:
        raise _error(str(path), "is outside its pinned configuration root") from exc
    current = lexical_root
    for part in relative.parts:
        current /= part
        if _is_link(current):
            raise _error(str(path), f"linked path component is not allowed: {current}")
    try:
        if not absolute.resolve(strict=False).is_relative_to(pinned_root):
            raise _error(str(path), "escapes its pinned configuration root")
    except OSError as exc:
        raise _error(str(path), "could not validate pinned configuration root") from exc


def _require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(path, "must be an object")
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(path, "must be a non-empty string")
    return value


def _reject_unknown(document: Mapping[str, Any], allowed: set[str], path: str) -> None:
    for key in document:
        if key not in allowed:
            raise _error(f"{path}.{key}", "is not supported")


def _require_version(value: Any, path: str) -> None:
    if type(value) is not int or value != SCHEMA_VERSION:
        raise _error(path, f"must be integer {SCHEMA_VERSION}")


def _validate_bundle_document(document: Any, field: str = "bundle", *, expected_policy_version: str = POLICY_VERSION) -> dict[str, Any]:
    """Validate a bundled policy already held in memory."""
    bundle = _require_object(document, field)
    _reject_unknown(bundle, {"schema_version", "policy_version", "interactions", "roles", "models", "effort_orders", "defaults"}, field)
    if set(bundle) != {"schema_version", "policy_version", "interactions", "roles", "models", "effort_orders", "defaults"}:
        raise _error(field, "is missing required fields")
    _require_version(bundle.get("schema_version"), f"{field}.schema_version")
    if bundle.get("policy_version") != expected_policy_version:
        raise _error(f"{field}.policy_version", f"must be {expected_policy_version!r}")
    interactions, roles, models = bundle["interactions"], bundle["roles"], bundle["models"]
    if not isinstance(interactions, list) or not isinstance(roles, list) or not isinstance(models, list):
        raise _error(field, "interactions, roles, and models must be arrays")
    interaction_ids: list[str] = []
    for index, item in enumerate(interactions):
        item = _require_object(item, f"{field}.interactions[{index}]")
        _reject_unknown(item, {"id", "label", "provider", "default_model"}, f"{field}.interactions[{index}]")
        if set(item) != {"id", "label", "provider", "default_model"}:
            raise _error(f"{field}.interactions[{index}]", "is missing required fields")
        for key in ("id", "label", "provider", "default_model"):
            _require_string(item[key], f"{field}.interactions[{index}].{key}")
        if item["provider"] not in {"codex", "claude"}:
            raise _error(f"{field}.interactions[{index}].provider", "must be codex or claude")
        interaction_ids.append(item["id"])
    if tuple(interaction_ids) != INTERACTIONS:
        raise _error(f"{field}.interactions", "must contain the five stable interactions in policy order")
    role_ids: set[str] = set()
    for index, item in enumerate(roles):
        item = _require_object(item, f"{field}.roles[{index}]")
        _reject_unknown(item, {"id", "label"}, f"{field}.roles[{index}]")
        if set(item) != {"id", "label"}:
            raise _error(f"{field}.roles[{index}]", "is missing required fields")
        role_id = _require_string(item["id"], f"{field}.roles[{index}].id")
        _require_string(item["label"], f"{field}.roles[{index}].label")
        if role_id in role_ids:
            raise _error(f"{field}.roles[{index}].id", "must be unique")
        role_ids.add(role_id)
    if len(role_ids) != 13 or "clanker-code-review" not in role_ids:
        raise _error(f"{field}.roles", "must contain the 13 native roles including clanker-code-review")
    model_ids: set[str] = set()
    for index, item in enumerate(models):
        item = _require_object(item, f"{field}.models[{index}]")
        _reject_unknown(item, {"id", "label", "provider", "efforts"}, f"{field}.models[{index}]")
        if set(item) != {"id", "label", "provider", "efforts"}:
            raise _error(f"{field}.models[{index}]", "is missing required fields")
        model_id = _require_string(item["id"], f"{field}.models[{index}].id")
        _require_string(item["label"], f"{field}.models[{index}].label")
        if item["provider"] not in {"codex", "claude"}:
            raise _error(f"{field}.models[{index}].provider", "must be codex or claude")
        efforts = item["efforts"]
        if not isinstance(efforts, list) or not efforts or not all(isinstance(effort, str) and effort for effort in efforts):
            raise _error(f"{field}.models[{index}].efforts", "must be a non-empty string array")
        if model_id in model_ids:
            raise _error(f"{field}.models[{index}].id", "must be unique")
        model_ids.add(model_id)
    orders = _require_object(bundle["effort_orders"], f"{field}.effort_orders")
    if set(orders) != {"codex", "claude"}:
        raise _error(f"{field}.effort_orders", "must define codex and claude")
    for provider, values in orders.items():
        if not isinstance(values, list) or not values or not all(isinstance(item, str) and item for item in values) or len(set(values)) != len(values):
            raise _error(f"{field}.effort_orders.{provider}", "must be a unique non-empty string array")
    defaults = _require_object(bundle["defaults"], f"{field}.defaults")
    _require_version(defaults.get("schema_version"), f"{field}.defaults.schema_version")
    validate_preferences(defaults, bundle=bundle, field=f"{field}.defaults")
    return copy.deepcopy(bundle)


def load_bundle(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load and validate the bundled, versioned catalog without reading preferences."""
    candidate = Path(path) if path is not None else _policy_path()
    return _validate_bundle_document(_read_json(candidate, "bundle"), "bundle")

def _catalog(bundle: Mapping[str, Any]) -> tuple[dict[str, str], set[str]]:
    providers = {item["id"]: item["provider"] for item in bundle["models"]}
    roles = {item["id"] for item in bundle["roles"]}
    return providers, roles


def _provider_for_interaction(interaction: str) -> str:
    return "claude" if interaction == "claude-review" else "codex"


def _validate_reasoning(reasoning: Any, provider: str, path: str, bundle: Mapping[str, Any]) -> dict[str, Any]:
    value = _require_object(reasoning, path)
    mode = value.get("mode")
    if mode == "fixed":
        _reject_unknown(value, {"mode", "effort"}, path)
        effort = _require_string(value.get("effort"), f"{path}.effort")
        if effort not in bundle["effort_orders"][provider]:
            raise _error(f"{path}.effort", f"is not supported by {provider}")
        return {"mode": "fixed", "effort": effort}
    if mode == "adaptive":
        _reject_unknown(value, {"mode", "max_effort"}, path)
        result: dict[str, Any] = {"mode": "adaptive"}
        if "max_effort" in value:
            effort = _require_string(value["max_effort"], f"{path}.max_effort")
            if effort not in bundle["effort_orders"][provider]:
                raise _error(f"{path}.max_effort", f"is not supported by {provider}")
            result["max_effort"] = effort
        return result
    raise _error(f"{path}.mode", "must be fixed or adaptive")


def _validate_route(value: Any, interaction: str, path: str, bundle: Mapping[str, Any], allow_specialists: bool) -> dict[str, Any]:
    route = _require_object(value, path)
    allowed = {"model", "reasoning"}
    if allow_specialists:
        allowed.add("specialists")
    _reject_unknown(route, allowed, path)
    if not route:
        raise _error(path, "must contain at least one override")
    provider = _provider_for_interaction(interaction)
    model_providers, roles = _catalog(bundle)
    normalized: dict[str, Any] = {}
    if "model" in route:
        model = _require_string(route["model"], f"{path}.model")
        known_provider = model_providers.get(model)
        if known_provider is not None and known_provider != provider:
            raise _error(f"{path}.model", f"belongs to {known_provider}, not {provider}")
        normalized["model"] = model
    if "reasoning" in route:
        normalized["reasoning"] = _validate_reasoning(route["reasoning"], provider, f"{path}.reasoning", bundle)
    if "specialists" in route:
        specialists = _require_object(route["specialists"], f"{path}.specialists")
        if interaction not in NATIVE_INTERACTIONS:
            raise _error(f"{path}.specialists", "is not allowed for claude-review")
        normalized_specialists: dict[str, Any] = {}
        for role, specialist in specialists.items():
            if role not in roles:
                raise _error(f"{path}.specialists.{role}", "is not a known native role")
            normalized_specialists[role] = _validate_route(specialist, interaction, f"{path}.specialists.{role}", bundle, False)
        normalized["specialists"] = normalized_specialists
    return normalized


def _validate_agent_route(value: Any, path: str, bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a sparse native-agent default with no nested activity exceptions."""
    return _validate_route(value, "planning", path, bundle, False)


def _validate_profile(value: Any, provider: str, path: str, bundle: Mapping[str, Any]) -> dict[str, Any]:
    profile = _require_object(value, path)
    _reject_unknown(profile, {"tiers", "default_ceiling"}, path)
    tiers = _require_object(profile.get("tiers"), f"{path}.tiers")
    if set(tiers) != set(TIERS):
        raise _error(f"{path}.tiers", "must define mechanical, routine, complex, and exceptional")
    normalized_tiers: dict[str, str] = {}
    for tier in TIERS:
        effort = _require_string(tiers[tier], f"{path}.tiers.{tier}")
        if effort not in bundle["effort_orders"][provider]:
            raise _error(f"{path}.tiers.{tier}", f"is not supported by {provider}")
        normalized_tiers[tier] = effort
    ceiling = _require_string(profile.get("default_ceiling"), f"{path}.default_ceiling")
    if ceiling not in bundle["effort_orders"][provider]:
        raise _error(f"{path}.default_ceiling", f"is not supported by {provider}")
    return {"tiers": normalized_tiers, "default_ceiling": ceiling}


def validate_preferences(document: Any, *, bundle: Mapping[str, Any] | None = None, field: str = "preferences") -> dict[str, Any]:
    """Return a normalized sparse preference document or raise a field-specific error."""
    active_bundle = load_bundle() if bundle is None else bundle
    prefs = _require_object(document, field)
    policy_version = active_bundle.get("policy_version")
    if not isinstance(policy_version, str) or policy_version not in SUPPORTED_POLICY_VERSIONS:
        raise _error(f"{field}.policy_version", "is not supported by this routing helper")
    allows_agents = policy_version == POLICY_VERSION
    allowed = {"schema_version", "interactions", "adaptive_profiles"}
    if allows_agents:
        allowed.add("agents")
    _reject_unknown(prefs, allowed, field)
    _require_version(prefs.get("schema_version"), f"{field}.schema_version")
    normalized: dict[str, Any] = {"schema_version": SCHEMA_VERSION}
    if "interactions" in prefs:
        interactions = _require_object(prefs["interactions"], f"{field}.interactions")
        normalized_interactions: dict[str, Any] = {}
        for interaction, route in interactions.items():
            if interaction not in INTERACTIONS:
                raise _error(f"{field}.interactions.{interaction}", "is not a known interaction")
            normalized_interactions[interaction] = _validate_route(route, interaction, f"{field}.interactions.{interaction}", active_bundle, True)
        normalized["interactions"] = normalized_interactions
    if "agents" in prefs:
        agents = _require_object(prefs["agents"], f"{field}.agents")
        role_ids = _catalog(active_bundle)[1]
        normalized_agents: dict[str, Any] = {}
        for role, route in agents.items():
            if role not in role_ids:
                raise _error(f"{field}.agents.{role}", "is not a known native role")
            normalized_agents[role] = _validate_agent_route(route, f"{field}.agents.{role}", active_bundle)
        normalized["agents"] = normalized_agents
    if "adaptive_profiles" in prefs:
        profiles = _require_object(prefs["adaptive_profiles"], f"{field}.adaptive_profiles")
        normalized_profiles: dict[str, Any] = {}
        for key, profile in profiles.items():
            if not isinstance(key, str) or ":" not in key:
                raise _error(f"{field}.adaptive_profiles", "keys must be provider:exact-model-id")
            provider, model = key.split(":", 1)
            if provider not in {"codex", "claude"} or not model:
                raise _error(f"{field}.adaptive_profiles.{key}", "key must be provider:exact-model-id")
            known_provider = _catalog(active_bundle)[0].get(model)
            if known_provider is not None and known_provider != provider:
                raise _error(f"{field}.adaptive_profiles.{key}", f"model belongs to {known_provider}")
            normalized_profiles[key] = _validate_profile(profile, provider, f"{field}.adaptive_profiles.{key}", active_bundle)
        normalized["adaptive_profiles"] = normalized_profiles
    return normalized


def _empty_preferences() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION}


def _hash_document(document: Any) -> str | None:
    return None if document is None else _sha256(_canonical_json(document))


def _snapshot_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in snapshot.items() if key != "fingerprint"}


def snapshot_from_documents(global_document: Any = None, project_document: Any = None, sources: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Freeze already-read documents and the bundled policy for a reproducible run."""
    bundle = load_bundle()
    global_prefs = None if global_document is None else validate_preferences(global_document, bundle=bundle, field="global")
    project_prefs = None if project_document is None else validate_preferences(project_document, bundle=bundle, field="project")
    source_values = dict(sources or {})
    _reject_unknown(source_values, {"global", "project"}, "sources")
    normalized_sources = {name: source_values.get(name) for name in ("global", "project")}
    for name, value in normalized_sources.items():
        if value is not None and (not isinstance(value, str) or not value):
            raise _error(f"sources.{name}", "must be a non-empty display path")
    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "bundle": bundle,
        "documents": {"global": global_prefs, "project": project_prefs},
        "sources": normalized_sources,
        "hashes": {
            "bundle": _sha256(_canonical_json(bundle)),
            "global": _hash_document(global_prefs),
            "project": _hash_document(project_prefs),
        },
        "bypassed_sources": [],
    }
    snapshot["fingerprint"] = _sha256(_canonical_json(_snapshot_payload(snapshot)))
    return snapshot


def _read_preference_path(path: str | os.PathLike[str] | None, name: str, bypassed: set[str]) -> tuple[Any, str | None, str | None, bool]:
    if path is None:
        return None, None, None, False
    candidate = Path(path)
    display = str(candidate)
    try:
        resolved = str(candidate.absolute())
    except OSError as exc:
        raise _error(name, "could not resolve configured path") from exc
    if display in bypassed or resolved in bypassed:
        return None, display, None, True
    _assert_no_link_components(candidate)
    if not candidate.exists():
        return None, display, None, False
    if not candidate.is_file():
        raise _error(name, "must be a regular file")
    try:
        raw = candidate.read_bytes()
        document = _parse_json_bytes(raw, name)
    except OSError as exc:
        raise _error(name, "could not be read") from exc
    return document, display, _sha256(raw), False


def create_snapshot(global_path: str | os.PathLike[str], project_path: str | os.PathLike[str] | None = None, bypass: list[str] | tuple[str, ...] | set[str] | None = None) -> dict[str, Any]:
    """Read only explicitly named config files and create a deterministic snapshot."""
    if global_path is None:
        raise _error("global", "an explicit global configuration path is required")
    if bypass is not None and (not isinstance(bypass, (list, tuple, set)) or not all(isinstance(item, str) and item for item in bypass)):
        raise _error("bypass", "must name exact source paths")
    bypassed = set(bypass or ())
    global_doc, global_source, global_hash, global_bypassed = _read_preference_path(global_path, "global", bypassed)
    project_doc, project_source, project_hash, project_bypassed = _read_preference_path(project_path, "project", bypassed)
    snapshot = snapshot_from_documents(global_doc, project_doc, {"global": global_source, "project": project_source})
    snapshot["hashes"]["global"] = global_hash
    snapshot["hashes"]["project"] = project_hash
    snapshot["bypassed_sources"] = [source for source, bypassed_flag in ((global_source, global_bypassed), (project_source, project_bypassed)) if bypassed_flag and source is not None]
    snapshot["fingerprint"] = _sha256(_canonical_json(_snapshot_payload(snapshot)))
    return snapshot


def validate_snapshot(snapshot: Any) -> dict[str, Any]:
    """Validate an immutable snapshot without ever consulting live preference files."""
    value = _require_object(snapshot, "snapshot")
    required = {"schema_version", "policy_version", "bundle", "documents", "sources", "hashes", "bypassed_sources", "fingerprint"}
    _reject_unknown(value, required, "snapshot")
    if set(value) != required:
        raise _error("snapshot", "is missing required fields")
    _require_version(value["schema_version"], "snapshot.schema_version")
    policy_version = value["policy_version"]
    if not isinstance(policy_version, str) or policy_version not in SUPPORTED_POLICY_VERSIONS:
        raise _error("snapshot.policy_version", "has an unsupported policy version")
    bundle = _validate_bundle_document(value["bundle"], "snapshot.bundle", expected_policy_version=policy_version)
    documents = _require_object(value["documents"], "snapshot.documents")
    sources = _require_object(value["sources"], "snapshot.sources")
    hashes = _require_object(value["hashes"], "snapshot.hashes")
    if set(documents) != {"global", "project"} or set(sources) != {"global", "project"} or set(hashes) != {"bundle", "global", "project"}:
        raise _error("snapshot", "documents, sources, and hashes have an invalid shape")
    # The snapshot bundle was generated by load_bundle; validate preference data against it.
    for name in ("global", "project"):
        if documents[name] is not None:
            validate_preferences(documents[name], bundle=bundle, field=f"snapshot.documents.{name}")
        if sources[name] is not None and not isinstance(sources[name], str):
            raise _error(f"snapshot.sources.{name}", "must be a path string or null")
        expected_hash = _hash_document(documents[name])
        if hashes[name] is not None and not isinstance(hashes[name], str):
            raise _error(f"snapshot.hashes.{name}", "must be a SHA-256 string or null")
        # File hashes intentionally may differ from canonical parsed JSON hashes, but missing documents cannot have one.
        if documents[name] is None and hashes[name] is not None:
            raise _error(f"snapshot.hashes.{name}", "must be null when the document is absent")
    if hashes["bundle"] != _sha256(_canonical_json(bundle)):
        raise _error("snapshot.hashes.bundle", "does not match bundled policy")
    if not isinstance(value["bypassed_sources"], list) or not all(isinstance(item, str) for item in value["bypassed_sources"]):
        raise _error("snapshot.bypassed_sources", "must be a string array")
    if not isinstance(value["fingerprint"], str) or value["fingerprint"] != _sha256(_canonical_json(_snapshot_payload(value))):
        raise _error("snapshot.fingerprint", "does not match snapshot contents")
    return copy.deepcopy(value)


def _layers(snapshot: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    docs = snapshot["documents"]
    return docs["global"] or _empty_preferences(), docs["project"] or _empty_preferences()


def _route_for(snapshot: Mapping[str, Any], interaction: str, role: str | None, session_override: Any = None) -> tuple[dict[str, Any], dict[str, str]]:
    bundle = snapshot["bundle"]
    defaults = bundle["defaults"]
    global_prefs, project_prefs = _layers(snapshot)
    route = copy.deepcopy(defaults["interactions"][interaction])
    provenance = {"model": "bundle.defaults", "reasoning": "bundle.defaults"}

    def apply(value: Mapping[str, Any] | None, source: str) -> None:
        if not value:
            return
        for field in ("model", "reasoning"):
            if field in value:
                route[field] = copy.deepcopy(value[field])
                provenance[field] = source + "." + field

    for scope_name, document in (("global", global_prefs), ("project", project_prefs)):
        interaction_route = document.get("interactions", {}).get(interaction)
        apply(interaction_route, f"{scope_name}.interactions.{interaction}")
        if role is not None and snapshot["policy_version"] == POLICY_VERSION:
            apply(document.get("agents", {}).get(role), f"{scope_name}.agents.{role}")
        if role is not None and interaction_route:
            apply(interaction_route.get("specialists", {}).get(role), f"{scope_name}.interactions.{interaction}.specialists.{role}")
    if session_override not in (None, {}):
        normalized = _validate_route(session_override, interaction, "request.session_override", bundle, False)
        apply(normalized, "session_override")
    return route, provenance


def _profile_for(snapshot: Mapping[str, Any], provider: str, model: str) -> tuple[dict[str, Any] | None, str | None]:
    key = f"{provider}:{model}"
    profile = snapshot["bundle"]["defaults"].get("adaptive_profiles", {}).get(key)
    source = "bundle.defaults.adaptive_profiles." + key if profile is not None else None
    for scope_name, document in (("global", snapshot["documents"]["global"]), ("project", snapshot["documents"]["project"])):
        if document is not None and key in document.get("adaptive_profiles", {}):
            profile = document["adaptive_profiles"][key]
            source = f"{scope_name}.adaptive_profiles.{key}"
    return copy.deepcopy(profile) if profile is not None else None, source


def _validate_request(request: Any, bundle: Mapping[str, Any]) -> dict[str, Any]:
    value = _require_object(request, "request")
    _reject_unknown(value, {"interaction", "role", "tier", "risk_flags", "reason", "session_override", "capabilities"}, "request")
    interaction = value.get("interaction")
    if interaction not in INTERACTIONS:
        raise _error("request.interaction", "must be a known interaction")
    role = value.get("role")
    if role is not None:
        if interaction not in NATIVE_INTERACTIONS:
            raise _error("request.role", "is not allowed for claude-review")
        if role not in _catalog(bundle)[1]:
            raise _error("request.role", "is not a known native role")
    tier = value.get("tier")
    if tier not in TIERS:
        raise _error("request.tier", "must be mechanical, routine, complex, or exceptional")
    reason = _require_string(value.get("reason"), "request.reason").strip()
    flags = value.get("risk_flags", [])
    if not isinstance(flags, list) or not all(isinstance(flag, str) and flag in RISK_FLAGS for flag in flags) or len(set(flags)) != len(flags):
        raise _error("request.risk_flags", "must be a unique list of known risk flags")
    if "session_override" in value and value["session_override"] != {}:
        _validate_route(value["session_override"], interaction, "request.session_override", bundle, False)
    capabilities = value.get("capabilities")
    if capabilities is not None:
        caps = _require_object(capabilities, "request.capabilities")
        _reject_unknown(caps, {"provider", "source", "models", "preflight_valid"}, "request.capabilities")
        if caps.get("provider") not in {"codex", "claude"}:
            raise _error("request.capabilities.provider", "must be codex or claude")
        _require_string(caps.get("source"), "request.capabilities.source")
        if "models" in caps:
            models = _require_object(caps["models"], "request.capabilities.models")
            for model, efforts in models.items():
                _require_string(model, "request.capabilities.models model")
                if not isinstance(efforts, list) or not all(isinstance(effort, str) and effort for effort in efforts):
                    raise _error(f"request.capabilities.models.{model}", "must be a string array")
        if "preflight_valid" in caps and not isinstance(caps["preflight_valid"], bool):
            raise _error("request.capabilities.preflight_valid", "must be boolean")
    return {"interaction": interaction, "role": role, "tier": tier, "reason": reason, "risk_flags": flags, "session_override": value.get("session_override"), "capabilities": capabilities}


def _capability_gate(provider: str, model: str, effort: str, capabilities: Mapping[str, Any] | None, limitations: list[str]) -> tuple[str, bool, dict[str, Any]]:
    if capabilities is None:
        if provider == "claude":
            limitations.append("Claude route requires the guarded launcher preflight before any model call")
            return "requires_launcher_preflight", False, {"launcher_allowed": True}
        limitations.append("No native runtime capability metadata was supplied")
        return "unverified", False, {}
    if capabilities["provider"] != provider:
        raise _error("request.capabilities.provider", f"does not match {provider} route")
    models = capabilities.get("models")
    pair_advertised = isinstance(models, Mapping) and model in models and effort in models[model]
    if provider == "claude":
        if models is not None and not pair_advertised:
            limitations.append(f"Claude capability metadata does not support {model}/{effort}")
            return "unsupported", False, {}
        if capabilities.get("preflight_valid") is True:
            return "preflight_valid", True, {"account_status": "unverified", "launcher_allowed": True}
        limitations.append("Claude launcher preflight has not validated this requested route")
        return "requires_launcher_preflight", False, {"launcher_allowed": True}
    if models is None:
        limitations.append("Native capability metadata did not list model and effort pairs")
        return "unverified", False, {}
    if pair_advertised:
        return "supported", True, {}
    limitations.append(f"Native runtime does not advertise {model}/{effort}")
    return "unsupported", False, {}


def _effort_index(bundle: Mapping[str, Any], provider: str, effort: str) -> int:
    try:
        return bundle["effort_orders"][provider].index(effort)
    except ValueError as exc:
        raise _error("effort", f"{effort!r} is not supported by {provider}") from exc


def resolve(snapshot: Any, request: Any) -> dict[str, Any]:
    """Resolve a request exclusively against an immutable saved snapshot."""
    frozen = validate_snapshot(snapshot)
    bundle = frozen["bundle"]
    asked = _validate_request(request, bundle)
    interaction, role = asked["interaction"], asked["role"]
    provider = _provider_for_interaction(interaction)
    route, provenance = _route_for(frozen, interaction, role, asked["session_override"])
    model = route["model"]
    known_provider = _catalog(bundle)[0].get(model)
    if known_provider is not None and known_provider != provider:
        raise _error("resolved.model", f"{model} belongs to {known_provider}, not {provider}")
    reasoning = route["reasoning"]
    profile, profile_source = _profile_for(frozen, provider, model)
    tier = asked["tier"]
    limitations: list[str] = []
    if set(asked["risk_flags"]) & CONSEQUENTIAL_FLAGS and TIERS.index(tier) < TIERS.index("complex"):
        tier = "complex"
        limitations.append("Tier raised to complex because the request has consequential risk")
    if reasoning["mode"] == "adaptive":
        if profile is None:
            raise _error("resolved.reasoning", f"Adaptive routing for {provider}:{model} requires a complete profile")
        proposed_effort = profile["tiers"][tier]
        if "max_effort" in reasoning:
            ceiling = reasoning["max_effort"]
            ceiling_source = provenance["reasoning"] + ".max_effort"
        else:
            ceiling = profile["default_ceiling"]
            ceiling_source = profile_source + ".default_ceiling" if profile_source else "bundle.defaults"
        effort = proposed_effort if _effort_index(bundle, provider, proposed_effort) <= _effort_index(bundle, provider, ceiling) else ceiling
        if effort != proposed_effort:
            limitations.append(f"Adaptive {tier} effort {proposed_effort} is capped at {ceiling}")
    else:
        effort = reasoning["effort"]
        proposed_effort = effort
        ceiling = None
        ceiling_source = None
        if profile is not None:
            recommended = profile["tiers"][tier]
            if _effort_index(bundle, provider, effort) < _effort_index(bundle, provider, recommended):
                limitations.append(f"Fixed effort {effort} is below the Adaptive {tier} recommendation {recommended}")
    status, allowed, extra = _capability_gate(provider, model, effort, asked["capabilities"], limitations)
    decision: dict[str, Any] = {
        "model": model,
        "reasoning": copy.deepcopy(reasoning),
        "effort": effort,
        "proposed_effort": proposed_effort,
        "ceiling": ceiling,
        "ceiling_source": ceiling_source,
        "interaction": interaction,
        "role": role,
        "tier": tier,
        "reason": asked["reason"],
        "limitations": limitations,
        "provenance": {"model": provenance["model"], "reasoning": provenance["reasoning"], "profile": profile_source},
        "capability_status": status,
        "dispatch_allowed": allowed,
        "schema_version": SCHEMA_VERSION,
        "policy_version": frozen["policy_version"],
        "snapshot_fingerprint": frozen["fingerprint"],
    }
    decision.update(extra)
    return decision


def effective_configuration(snapshot: Any) -> dict[str, Any]:
    """Return inherited routes for UI display without task assessment or capability claims."""
    frozen = validate_snapshot(snapshot)
    bundle = frozen["bundle"]
    interactions: dict[str, Any] = {}
    role_ids = [role["id"] for role in bundle["roles"]]
    for interaction in INTERACTIONS:
        route, provenance = _route_for(frozen, interaction, None)
        provider = _provider_for_interaction(interaction)
        profile, profile_source = _profile_for(frozen, provider, route["model"])
        display_reasoning = copy.deepcopy(route["reasoning"])
        ceiling = ceiling_source = None
        if display_reasoning["mode"] == "adaptive":
            if profile is None:
                raise _error(f"effective.interactions.{interaction}", f"Adaptive routing for {provider}:{route['model']} requires a complete profile")
            ceiling = display_reasoning.get("max_effort", profile["default_ceiling"])
            ceiling_source = provenance["reasoning"] + ".max_effort" if "max_effort" in display_reasoning else profile_source + ".default_ceiling"
        entry = {"ceiling": ceiling, "ceiling_source": ceiling_source, "route": {"model": route["model"], "reasoning": display_reasoning}, "provenance": {"model": provenance["model"], "reasoning": provenance["reasoning"], "profile": profile_source}, "specialists": {}}
        if interaction in NATIVE_INTERACTIONS:
            for role in role_ids:
                special_route, special_provenance = _route_for(frozen, interaction, role)
                special_profile, special_profile_source = _profile_for(frozen, provider, special_route["model"])
                special_reasoning = copy.deepcopy(special_route["reasoning"])
                special_ceiling = special_ceiling_source = None
                if special_reasoning["mode"] == "adaptive":
                    if special_profile is None:
                        raise _error(f"effective.interactions.{interaction}.specialists.{role}", "Adaptive route requires a complete profile")
                    special_ceiling = special_reasoning.get("max_effort", special_profile["default_ceiling"])
                    special_ceiling_source = special_provenance["reasoning"] + ".max_effort" if "max_effort" in special_reasoning else special_profile_source + ".default_ceiling"
                entry["specialists"][role] = {"ceiling": special_ceiling, "ceiling_source": special_ceiling_source, "route": {"model": special_route["model"], "reasoning": special_reasoning}, "provenance": {"model": special_provenance["model"], "reasoning": special_provenance["reasoning"], "profile": special_profile_source}}
        interactions[interaction] = entry
    profiles: dict[str, Any] = {}
    for key, profile in bundle["defaults"].get("adaptive_profiles", {}).items():
        profiles[key] = copy.deepcopy(profile)
    for document in frozen["documents"].values():
        if document is not None:
            profiles.update(copy.deepcopy(document.get("adaptive_profiles", {})))
    result: dict[str, Any] = {"interactions": interactions, "profiles": profiles}
    if frozen["policy_version"] == POLICY_VERSION:
        agents: dict[str, Any] = {}
        for role in role_ids:
            route: dict[str, Any] = {}
            provenance: dict[str, str] = {}
            for scope_name, document in (("global", frozen["documents"]["global"]), ("project", frozen["documents"]["project"])):
                agent_route = (document or {}).get("agents", {}).get(role)
                if agent_route:
                    for field in ("model", "reasoning"):
                        if field in agent_route:
                            route[field] = copy.deepcopy(agent_route[field])
                            provenance[field] = f"{scope_name}.agents.{role}.{field}"
            agents[role] = {"route": route, "provenance": provenance}
        result["agents"] = agents
    return result


def _read_cli_json(path: str | None) -> Any:
    try:
        raw = Path(path).read_bytes() if path else sys.stdin.buffer.read(MAX_JSON_BYTES + 1)
        return _parse_json_bytes(raw, "input")
    except OSError as exc:
        raise RoutingError("input: could not be read") from exc


def _write_snapshot_exclusive(path: str, snapshot: Mapping[str, Any]) -> None:
    target = Path(path)
    _assert_no_link_components(target.parent)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _assert_no_link_components(target.parent)
        with target.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(snapshot, output, sort_keys=True, indent=2)
            output.write("\n")
    except FileExistsError as exc:
        raise RoutingError("snapshot output already exists; snapshots are immutable") from exc
    except OSError as exc:
        raise RoutingError("snapshot output could not be created") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and resolve Clanker orchestration routing policy.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("catalog", help="write the bundled policy catalog as JSON")
    snapshot_parser = subcommands.add_parser("snapshot", help="read explicit preferences and create an immutable snapshot")
    snapshot_parser.add_argument("--global", dest="global_path", required=True, help="explicit global preferences path")
    snapshot_parser.add_argument("--project", dest="project_path", help="explicit project preferences path")
    snapshot_parser.add_argument("--bypass", action="append", default=[], help="exact source path to ignore for this run")
    snapshot_parser.add_argument("--output", help="new snapshot file path; creation is exclusive")
    resolve_parser = subcommands.add_parser("resolve", help="resolve a JSON request against a saved snapshot")
    resolve_parser.add_argument("--snapshot", required=True, help="immutable snapshot JSON path")
    resolve_parser.add_argument("--request", help="request JSON file; default reads standard input")
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            result = load_bundle()
        elif args.command == "snapshot":
            result = create_snapshot(args.global_path, args.project_path, args.bypass)
            if args.output:
                _write_snapshot_exclusive(args.output, result)
        else:
            snapshot = _read_cli_json(args.snapshot)
            request = _read_cli_json(args.request)
            result = resolve(snapshot, request)
        print(json.dumps(result, sort_keys=True))
        return 0
    except RoutingError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
