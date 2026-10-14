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
POLICY_VERSION = "7"
NATIVE_ROLES = frozenset((
    "clanker-architect", "clanker-backend-developer", "clanker-code-review",
    "clanker-data-engineer", "clanker-devops-engineer", "clanker-performance-engineer",
    "clanker-qa-engineer", "clanker-test-engineer", "clanker-ui-developer",
    "clanker-ui-ux-reviewer",
))
HOSTS = ("codex", "claude")
NATIVE_INTERACTION_ORDER = ("planning", "implementation", "native-review", "visual-review")
NATIVE_INTERACTIONS = frozenset(NATIVE_INTERACTION_ORDER)
EXTERNAL_INTERACTIONS = {"codex": "claude-review", "claude": "codex-review"}
HOST_INTERACTIONS = {host: NATIVE_INTERACTION_ORDER + (EXTERNAL_INTERACTIONS[host],) for host in HOSTS}
HOST_PREFERENCE_FILES = {"codex": "orchestration-routing.json", "claude": "orchestration-routing-claude.json"}
# The external reviewer is the other provider's launcher.
HOST_LAUNCHERS = {"codex": "scripts/claude_cross_review.py", "claude": "scripts/codex_cross_review.py"}
DEFAULT_HOST = "codex"
HOST_CONFIG_SCHEMA_VERSION = 1
TIERS = ("straightforward", "involved", "demanding")
LEGACY_TIERS = ("mechanical", "routine", "complex", "exceptional")
RISK_FLAGS = frozenset(("security", "data-integrity", "recovery", "cross-layer", "uncertainty", "performance"))
CONSEQUENTIAL_FLAGS = frozenset(("security", "data-integrity", "recovery"))
MAX_JSON_BYTES = 1_048_576
MAX_OVERRIDE_CHARS = 200


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


def _host_config_path() -> Path:
    """Installed bundles carry routing/host.json beside the policy; source checkouts do not."""
    return _policy_path().parent / "host.json"


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


def _validate_host_interactions(host: str, interactions: Any, field: str) -> None:
    if not isinstance(interactions, list):
        raise _error(field, "must be an array")
    interaction_ids: list[str] = []
    for index, item in enumerate(interactions):
        item = _require_object(item, f"{field}[{index}]")
        _reject_unknown(item, {"id", "label", "execution", "default_model"}, f"{field}[{index}]")
        if set(item) != {"id", "label", "execution", "default_model"}:
            raise _error(f"{field}[{index}]", "is missing required fields")
        for key in ("id", "label", "execution", "default_model"):
            _require_string(item[key], f"{field}[{index}].{key}")
        expected = "external" if item["id"] == EXTERNAL_INTERACTIONS[host] else "native"
        if item["execution"] != expected:
            raise _error(f"{field}[{index}].execution", f"must be {expected} for {item['id']}")
        interaction_ids.append(item["id"])
    if tuple(interaction_ids) != HOST_INTERACTIONS[host]:
        raise _error(field, f"must contain the five stable {host}-host interactions in policy order")


def _validate_bundle_document(document: Any, field: str = "bundle") -> dict[str, Any]:
    """Validate a bundled policy already held in memory."""
    bundle = _require_object(document, field)
    required_fields = {"schema_version", "policy_version", "roles", "models", "effort_orders", "hosts"}
    _reject_unknown(bundle, required_fields, field)
    if set(bundle) != required_fields:
        raise _error(field, "is missing required fields")
    _require_version(bundle.get("schema_version"), f"{field}.schema_version")
    if bundle.get("policy_version") != POLICY_VERSION:
        raise _error(f"{field}.policy_version", f"must be {POLICY_VERSION!r}")
    roles, models = bundle["roles"], bundle["models"]
    if not isinstance(roles, list) or not isinstance(models, list):
        raise _error(field, "roles and models must be arrays")
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
    if role_ids != NATIVE_ROLES:
        raise _error(f"{field}.roles", "must contain exactly the 10 active native roles")
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
    hosts = _require_object(bundle["hosts"], f"{field}.hosts")
    if set(hosts) != set(HOSTS):
        raise _error(f"{field}.hosts", "must define exactly the codex and claude hosts")
    for host in HOSTS:
        entry = _require_object(hosts[host], f"{field}.hosts.{host}")
        _reject_unknown(entry, {"interactions", "defaults"}, f"{field}.hosts.{host}")
        if set(entry) != {"interactions", "defaults"}:
            raise _error(f"{field}.hosts.{host}", "is missing required fields")
        _validate_host_interactions(host, entry["interactions"], f"{field}.hosts.{host}.interactions")
        defaults = _require_object(entry["defaults"], f"{field}.hosts.{host}.defaults")
        _require_version(defaults.get("schema_version"), f"{field}.hosts.{host}.defaults.schema_version")
        normalized_defaults = validate_preferences(defaults, bundle=bundle, field=f"{field}.hosts.{host}.defaults", host=host)
        if normalized_defaults != defaults:
            raise _error(f"{field}.hosts.{host}.defaults.adaptive_profiles", "must use the current tier vocabulary")
        for index, item in enumerate(entry["interactions"]):
            default_model = defaults.get("interactions", {}).get(item["id"], {}).get("model")
            if default_model is None:
                raise _error(f"{field}.hosts.{host}.defaults.interactions.{item['id']}", "must define a default model")
            if item["default_model"] != default_model:
                raise _error(f"{field}.hosts.{host}.interactions[{index}].default_model", f"must equal the host default model {default_model!r}")
    return copy.deepcopy(bundle)


def load_bundle(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load and validate the bundled, versioned catalog without reading preferences."""
    candidate = Path(path) if path is not None else _policy_path()
    return _validate_bundle_document(_read_json(candidate, "bundle"), "bundle")

def _catalog(bundle: Mapping[str, Any]) -> tuple[dict[str, str], set[str]]:
    providers = {item["id"]: item["provider"] for item in bundle["models"]}
    roles = {item["id"] for item in bundle["roles"]}
    return providers, roles


def _require_host(host: Any, field: str = "host") -> str:
    if not isinstance(host, str) or host not in HOSTS:
        raise _error(field, "must be codex or claude")
    return host


def _execution_for_interaction(host: str, interaction: str) -> str:
    return "external" if interaction == EXTERNAL_INTERACTIONS[host] else "native"


def _provider_for_interaction(host: str, interaction: str) -> str:
    """Native routes use the host's provider; the external review uses the other provider."""
    if _execution_for_interaction(host, interaction) == "native":
        return host
    return "claude" if host == "codex" else "codex"


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
        _reject_unknown(value, {"mode"}, path)
        return {"mode": "adaptive"}
    raise _error(f"{path}.mode", "must be fixed or adaptive")


def _validate_route(value: Any, interaction: str, path: str, bundle: Mapping[str, Any], allow_specialists: bool, host: str = DEFAULT_HOST) -> dict[str, Any]:
    route = _require_object(value, path)
    allowed = {"model", "reasoning"}
    if allow_specialists:
        allowed.add("specialists")
    _reject_unknown(route, allowed, path)
    if not route:
        raise _error(path, "must contain at least one override")
    provider = _provider_for_interaction(host, interaction)
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
            raise _error(f"{path}.specialists", f"is not allowed for {interaction}")
        normalized_specialists: dict[str, Any] = {}
        for role, specialist in specialists.items():
            if role not in roles:
                raise _error(f"{path}.specialists.{role}", "is not a known native role")
            normalized_specialists[role] = _validate_route(specialist, interaction, f"{path}.specialists.{role}", bundle, False, host)
        normalized["specialists"] = normalized_specialists
    return normalized


def _validate_agent_route(value: Any, path: str, bundle: Mapping[str, Any], host: str = DEFAULT_HOST) -> dict[str, Any]:
    """Validate a sparse native-agent default with no nested activity exceptions."""
    return _validate_route(value, "planning", path, bundle, False, host)


def _validate_profile(value: Any, provider: str, path: str, bundle: Mapping[str, Any]) -> dict[str, Any]:
    profile = _require_object(value, path)
    _reject_unknown(profile, {"tiers"}, path)
    tiers = _require_object(profile.get("tiers"), f"{path}.tiers")
    accepted_tiers = TIERS
    legacy_shape = set(tiers) == set(LEGACY_TIERS)
    if set(tiers) != set(accepted_tiers) and not legacy_shape:
        required = ", ".join(accepted_tiers)
        required += "; complete legacy profiles may define mechanical, routine, complex, and exceptional"
        raise _error(f"{path}.tiers", f"must define exactly {required}")
    if legacy_shape:
        retired_effort = _require_string(tiers["mechanical"], f"{path}.tiers.mechanical")
        if retired_effort not in bundle["effort_orders"][provider]:
            raise _error(f"{path}.tiers.mechanical", f"is not supported by {provider}")
    source_tiers = ({"straightforward": tiers["routine"], "involved": tiers["complex"], "demanding": tiers["exceptional"]}
                    if legacy_shape else tiers)
    normalized_tiers: dict[str, str] = {}
    for tier in accepted_tiers:
        source_tier = {"straightforward": "routine", "involved": "complex", "demanding": "exceptional"}.get(tier, tier) if legacy_shape else tier
        effort = _require_string(source_tiers[tier], f"{path}.tiers.{source_tier}")
        if effort not in bundle["effort_orders"][provider]:
            raise _error(f"{path}.tiers.{source_tier}", f"is not supported by {provider}")
        normalized_tiers[tier] = effort
    return {"tiers": normalized_tiers}


def validate_preferences(document: Any, *, bundle: Mapping[str, Any] | None = None, field: str = "preferences", host: str = DEFAULT_HOST) -> dict[str, Any]:
    """Return a normalized sparse preference document or raise a field-specific error."""
    _require_host(host)
    active_bundle = load_bundle() if bundle is None else bundle
    prefs = _require_object(document, field)
    policy_version = active_bundle.get("policy_version")
    if policy_version != POLICY_VERSION:
        raise _error(f"{field}.policy_version", "is not supported by this routing helper")
    allowed = {"schema_version", "interactions", "adaptive_profiles", "agents"}
    _reject_unknown(prefs, allowed, field)
    _require_version(prefs.get("schema_version"), f"{field}.schema_version")
    normalized: dict[str, Any] = {"schema_version": SCHEMA_VERSION}
    if "interactions" in prefs:
        interactions = _require_object(prefs["interactions"], f"{field}.interactions")
        normalized_interactions: dict[str, Any] = {}
        for interaction, route in interactions.items():
            if interaction not in HOST_INTERACTIONS[host]:
                if interaction in {item for interactions in HOST_INTERACTIONS.values() for item in interactions}:
                    raise _error(f"{field}.interactions.{interaction}", f"is not supported by the {host} host; its external review is {EXTERNAL_INTERACTIONS[host]}")
                raise _error(f"{field}.interactions.{interaction}", "is not a known interaction")
            normalized_interactions[interaction] = _validate_route(route, interaction, f"{field}.interactions.{interaction}", active_bundle, True, host)
        normalized["interactions"] = normalized_interactions
    if "agents" in prefs:
        agents = _require_object(prefs["agents"], f"{field}.agents")
        role_ids = _catalog(active_bundle)[1]
        normalized_agents: dict[str, Any] = {}
        for role, route in agents.items():
            if role not in role_ids:
                raise _error(f"{field}.agents.{role}", "is not a known native role")
            normalized_agents[role] = _validate_agent_route(route, f"{field}.agents.{role}", active_bundle, host)
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


def needs_profile_migration(document: Any, *, host: str = DEFAULT_HOST) -> bool:
    """Validate current preferences and report whether a complete legacy profile needs conversion."""
    validate_preferences(document, host=host)
    profiles = document.get("adaptive_profiles", {})
    return any(set(profile["tiers"]) == set(LEGACY_TIERS) for profile in profiles.values())


def _empty_preferences() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION}


def _hash_document(document: Any) -> str | None:
    return None if document is None else _sha256(_canonical_json(document))


def _snapshot_payload(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in snapshot.items() if key != "fingerprint"}


def load_host_config(path: str | os.PathLike[str] | None = None, bundle: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Strictly validate an installed host configuration; None means the bundle has none."""
    candidate = Path(path) if path is not None else _host_config_path()
    try:
        document = _read_json(candidate, "host_config")
    except FileNotFoundError:
        return None
    config = _require_object(document, "host_config")
    allowed = {"schema_version", "host", "preferences_file", "external_review"}
    _reject_unknown(config, allowed, "host_config")
    if set(config) != allowed:
        raise _error("host_config", "is missing required fields")
    if type(config["schema_version"]) is not int or config["schema_version"] != HOST_CONFIG_SCHEMA_VERSION:
        raise _error("host_config.schema_version", f"must be integer {HOST_CONFIG_SCHEMA_VERSION}")
    host = _require_host(config["host"], "host_config.host")
    active_bundle = load_bundle() if bundle is None else bundle
    if host not in active_bundle["hosts"]:
        raise _error("host_config.host", "is not defined by the bundled policy")
    preferences_file = _require_string(config["preferences_file"], "host_config.preferences_file")
    if preferences_file != HOST_PREFERENCE_FILES[host]:
        raise _error("host_config.preferences_file", f"must be {HOST_PREFERENCE_FILES[host]} for the {host} host")
    review = _require_object(config["external_review"], "host_config.external_review")
    _reject_unknown(review, {"interaction", "launcher"}, "host_config.external_review")
    if set(review) != {"interaction", "launcher"}:
        raise _error("host_config.external_review", "is missing required fields")
    if review["interaction"] != EXTERNAL_INTERACTIONS[host]:
        raise _error("host_config.external_review.interaction", f"must be {EXTERNAL_INTERACTIONS[host]} for the {host} host")
    launcher = _require_string(review["launcher"], "host_config.external_review.launcher")
    launcher_parts = launcher.split("/")
    if launcher.startswith("/") or "\\" in launcher or ":" in launcher or any(part in ("", ".", "..") for part in launcher_parts) or not launcher.endswith(".py"):
        raise _error("host_config.external_review.launcher", "must be a relative path to a Python launcher inside the bundle")
    if launcher != HOST_LAUNCHERS[host]:
        raise _error("host_config.external_review.launcher", f"must be {HOST_LAUNCHERS[host]} for the {host} host")
    return copy.deepcopy(config)


def snapshot_from_documents(global_document: Any = None, *, sources: Mapping[str, str] | None = None, host: str = DEFAULT_HOST) -> dict[str, Any]:
    """Freeze already-read documents and the bundled policy for a reproducible run."""
    _require_host(host)
    bundle = load_bundle()
    global_prefs = None if global_document is None else validate_preferences(global_document, bundle=bundle, field="global", host=host)
    source_values = dict(sources or {})
    _reject_unknown(source_values, {"global"}, "sources")
    normalized_sources = {"global": source_values.get("global")}
    for name, value in normalized_sources.items():
        if value is not None and (not isinstance(value, str) or not value):
            raise _error(f"sources.{name}", "must be a non-empty display path")
    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "host": host,
        "bundle": bundle,
        "documents": {"global": global_prefs},
        "sources": normalized_sources,
        "hashes": {
            "bundle": _sha256(_canonical_json(bundle)),
            "global": _hash_document(global_prefs),
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


def _snapshot_host(requested: str | None, global_path: Path) -> str:
    """Pick the snapshot host from the installed host configuration, else the request, else Codex."""
    config = load_host_config()
    if config is None:
        selected = DEFAULT_HOST if requested is None else _require_host(requested)
        # Arbitrary file names stay accepted, but never freeze the other host's own file as this host's preferences.
        other = next(name for name in HOSTS if name != selected)
        if global_path.name == HOST_PREFERENCE_FILES[other]:
            raise _error("global", f"{HOST_PREFERENCE_FILES[other]} is the {other} host's preference file, not the {selected} host's; "
                                   f"name the host with --host {other} or use {HOST_PREFERENCE_FILES[selected]}")
        return selected
    if requested is not None and requested != config["host"]:
        raise _error("host", f"{requested!r} contradicts the installed host configuration, which names {config['host']!r}")
    if global_path.name != config["preferences_file"]:
        raise _error("global", f"must name the installed host's preference file {config['preferences_file']}")
    return config["host"]


def create_snapshot(global_path: str | os.PathLike[str], *, bypass: list[str] | tuple[str, ...] | set[str] | None = None, host: str | None = None) -> dict[str, Any]:
    """Read only explicitly named config files and create a deterministic snapshot."""
    if global_path is None:
        raise _error("global", "an explicit global configuration path is required")
    if bypass is not None and (not isinstance(bypass, (list, tuple, set)) or not all(isinstance(item, str) and item for item in bypass)):
        raise _error("bypass", "must name exact source paths")
    selected_host = _snapshot_host(host, Path(global_path))
    bypassed = set(bypass or ())
    global_doc, global_source, global_hash, global_bypassed = _read_preference_path(global_path, "global", bypassed)
    snapshot = snapshot_from_documents(global_doc, sources={"global": global_source}, host=selected_host)
    snapshot["hashes"]["global"] = global_hash
    snapshot["bypassed_sources"] = [global_source] if global_bypassed and global_source is not None else []
    snapshot["fingerprint"] = _sha256(_canonical_json(_snapshot_payload(snapshot)))
    return snapshot


def validate_snapshot(snapshot: Any) -> dict[str, Any]:
    """Validate an immutable snapshot without ever consulting live preference files."""
    value = _require_object(snapshot, "snapshot")
    # Check the version first: older snapshots also lack the host field and must get new-run guidance.
    policy_version = value.get("policy_version")
    if policy_version != POLICY_VERSION:
        raise _error("snapshot.policy_version", f"only policy {POLICY_VERSION} is supported. Start a new run to create a current snapshot.")
    required = {"schema_version", "policy_version", "host", "bundle", "documents", "sources", "hashes", "bypassed_sources", "fingerprint"}
    _reject_unknown(value, required, "snapshot")
    if set(value) != required:
        raise _error("snapshot", "is missing required fields")
    _require_version(value["schema_version"], "snapshot.schema_version")
    host = _require_host(value["host"], "snapshot.host")
    bundle = _validate_bundle_document(value["bundle"], "snapshot.bundle")
    documents = _require_object(value["documents"], "snapshot.documents")
    sources = _require_object(value["sources"], "snapshot.sources")
    hashes = _require_object(value["hashes"], "snapshot.hashes")
    expected_names = {"global"}
    expected_hashes = {"bundle", "global"}
    if set(documents) != expected_names or set(sources) != expected_names or set(hashes) != expected_hashes:
        raise _error("snapshot", "documents, sources, and hashes have an invalid shape")
    # The snapshot bundle was generated by load_bundle; validate preference data against it.
    for name in expected_names:
        if documents[name] is not None:
            normalized = validate_preferences(documents[name], bundle=bundle, field=f"snapshot.documents.{name}", host=host)
            if normalized != documents[name]:
                raise _error(f"snapshot.documents.{name}", "must already use the tier vocabulary for its frozen policy version")
        if sources[name] is not None and not isinstance(sources[name], str):
            raise _error(f"snapshot.sources.{name}", "must be a path string or null")
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


def _route_for(snapshot: Mapping[str, Any], interaction: str, role: str | None, session_override: Any = None) -> tuple[dict[str, Any], dict[str, str]]:
    bundle = snapshot["bundle"]
    host = snapshot["host"]
    defaults = bundle["hosts"][host]["defaults"]
    global_prefs = snapshot["documents"]["global"] or _empty_preferences()
    route = copy.deepcopy(defaults["interactions"][interaction])
    provenance = {"model": "bundle.defaults", "reasoning": "bundle.defaults"}

    def apply(value: Mapping[str, Any] | None, source: str) -> None:
        if not value:
            return
        for field in ("model", "reasoning"):
            if field in value:
                route[field] = copy.deepcopy(value[field])
                provenance[field] = source + "." + field

    interaction_route = global_prefs.get("interactions", {}).get(interaction)
    apply(interaction_route, f"global.interactions.{interaction}")
    if role is not None:
        apply(global_prefs.get("agents", {}).get(role), f"global.agents.{role}")
        if interaction_route:
            apply(interaction_route.get("specialists", {}).get(role), f"global.interactions.{interaction}.specialists.{role}")
    if session_override not in (None, {}):
        normalized = _validate_route(session_override, interaction, "request.session_override", bundle, False, host)
        apply(normalized, "session_override")
    return route, provenance


def _profile_for(snapshot: Mapping[str, Any], provider: str, model: str) -> tuple[dict[str, Any] | None, str | None]:
    key = f"{provider}:{model}"
    profile = snapshot["bundle"]["hosts"][snapshot["host"]]["defaults"].get("adaptive_profiles", {}).get(key)
    source = "bundle.defaults.adaptive_profiles." + key if profile is not None else None
    document = snapshot["documents"]["global"]
    if document is not None and key in document.get("adaptive_profiles", {}):
        profile = document["adaptive_profiles"][key]
        source = f"global.adaptive_profiles.{key}"
    return copy.deepcopy(profile) if profile is not None else None, source


def _validate_request(request: Any, bundle: Mapping[str, Any], host: str) -> dict[str, Any]:
    value = _require_object(request, "request")
    _reject_unknown(value, {"interaction", "role", "tier", "risk_flags", "reason", "session_override", "capabilities", "overrides"}, "request")
    interaction = value.get("interaction")
    if interaction not in HOST_INTERACTIONS[host]:
        raise _error("request.interaction", "must be a known interaction")
    role = value.get("role")
    if role is not None:
        if interaction not in NATIVE_INTERACTIONS:
            raise _error("request.role", f"is not allowed for {interaction}")
        if role not in _catalog(bundle)[1]:
            raise _error("request.role", "is not a known native role")
    tier = value.get("tier")
    supported_tiers = TIERS
    if tier not in supported_tiers:
        raise _error("request.tier", f"must be {', '.join(supported_tiers)}")
    reason = _require_string(value.get("reason"), "request.reason").strip()
    flags = value.get("risk_flags", [])
    if not isinstance(flags, list) or not all(isinstance(flag, str) and flag in RISK_FLAGS for flag in flags) or len(set(flags)) != len(flags):
        raise _error("request.risk_flags", "must be a unique list of known risk flags")
    if "session_override" in value and value["session_override"] != {}:
        _validate_route(value["session_override"], interaction, "request.session_override", bundle, False, host)
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
    overrides = value.get("overrides", [])
    if overrides and interaction == EXTERNAL_INTERACTIONS[host]:
        raise _error("request.overrides", f"are native dispatch settings and are not accepted for {interaction}; the launcher preflight checks reviewer overrides")
    if (not isinstance(overrides, list) or not all(isinstance(item, str) and item.strip() and len(item) <= MAX_OVERRIDE_CHARS for item in overrides)
            or len(set(overrides)) != len(overrides)):
        raise _error("request.overrides", f"must be a unique list of setting names up to {MAX_OVERRIDE_CHARS} characters")
    return {"interaction": interaction, "role": role, "tier": tier, "reason": reason, "risk_flags": flags, "session_override": value.get("session_override"), "capabilities": capabilities, "overrides": overrides}


def _capability_gate(provider: str, execution: str, model: str, effort: str, capabilities: Mapping[str, Any] | None, limitations: list[str]) -> tuple[str, bool, dict[str, Any]]:
    name = provider.capitalize()
    if capabilities is None:
        if execution == "external":
            limitations.append(f"{name} route requires the guarded launcher preflight before any model call")
            return "requires_launcher_preflight", False, {"launcher_allowed": True}
        limitations.append("No native runtime capability metadata was supplied")
        return "unverified", False, {}
    if capabilities["provider"] != provider:
        raise _error("request.capabilities.provider", f"does not match {provider} route")
    models = capabilities.get("models")
    pair_advertised = isinstance(models, Mapping) and model in models and effort in models[model]
    if execution == "external":
        if models is not None and not pair_advertised:
            limitations.append(f"{name} capability metadata does not support {model}/{effort}")
            return "unsupported", False, {}
        if capabilities.get("preflight_valid") is True:
            return "preflight_valid", True, {"account_status": "unverified", "launcher_allowed": True}
        limitations.append(f"{name} launcher preflight has not validated this requested route")
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
    host = frozen["host"]
    asked = _validate_request(request, bundle, host)
    interaction, role = asked["interaction"], asked["role"]
    provider = _provider_for_interaction(host, interaction)
    execution = _execution_for_interaction(host, interaction)
    route, provenance = _route_for(frozen, interaction, role, asked["session_override"])
    model = route["model"]
    known_provider = _catalog(bundle)[0].get(model)
    if known_provider is not None and known_provider != provider:
        raise _error("resolved.model", f"{model} belongs to {known_provider}, not {provider}")
    reasoning = route["reasoning"]
    profile, profile_source = _profile_for(frozen, provider, model)
    tier = asked["tier"]
    limitations: list[str] = []
    tier_order = TIERS
    risk_floor = "involved"
    if set(asked["risk_flags"]) & CONSEQUENTIAL_FLAGS and tier_order.index(tier) < tier_order.index(risk_floor):
        tier = risk_floor
        limitations.append(f"Tier raised to {risk_floor} because the request has consequential risk")
    if reasoning["mode"] == "adaptive":
        if profile is None:
            raise _error("resolved.reasoning", f"Adaptive routing for {provider}:{model} requires a complete profile")
        proposed_effort = profile["tiers"][tier]
        effort = proposed_effort
    else:
        effort = reasoning["effort"]
        proposed_effort = effort
        if profile is not None:
            recommended = profile["tiers"][tier]
            if _effort_index(bundle, provider, effort) < _effort_index(bundle, provider, recommended):
                limitations.append(f"Fixed effort {effort} is below the Adaptive {tier} recommendation {recommended}")
    status, allowed, extra = _capability_gate(provider, execution, model, effort, asked["capabilities"], limitations)
    if asked["overrides"]:
        names = ", ".join(asked["overrides"])
        limitations.append(f"Runtime setting reported as replacing the requested route: {names}; dispatch is blocked and no substituted value is assumed")
        status, allowed, extra = "blocked_by_override", False, {"overrides": list(asked["overrides"])}
    decision: dict[str, Any] = {
        "model": model,
        "reasoning": copy.deepcopy(reasoning),
        "effort": effort,
        "proposed_effort": proposed_effort,
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
        "host": host,
        "provider": provider,
        "execution": execution,
    }
    decision.update(extra)
    return decision


def effective_configuration(snapshot: Any) -> dict[str, Any]:
    """Return inherited routes for UI display without task assessment or capability claims."""
    frozen = validate_snapshot(snapshot)
    bundle = frozen["bundle"]
    host = frozen["host"]
    interactions: dict[str, Any] = {}
    role_ids = [role["id"] for role in bundle["roles"]]
    for interaction in HOST_INTERACTIONS[host]:
        route, provenance = _route_for(frozen, interaction, None)
        provider = _provider_for_interaction(host, interaction)
        profile, profile_source = _profile_for(frozen, provider, route["model"])
        display_reasoning = copy.deepcopy(route["reasoning"])
        if display_reasoning["mode"] == "adaptive":
            if profile is None:
                raise _error(f"effective.interactions.{interaction}", f"Adaptive routing for {provider}:{route['model']} requires a complete profile")
        entry = {"route": {"model": route["model"], "reasoning": display_reasoning}, "provenance": {"model": provenance["model"], "reasoning": provenance["reasoning"], "profile": profile_source}, "specialists": {},
                 "provider": provider, "execution": _execution_for_interaction(host, interaction)}
        if interaction in NATIVE_INTERACTIONS:
            for role in role_ids:
                special_route, special_provenance = _route_for(frozen, interaction, role)
                special_profile, special_profile_source = _profile_for(frozen, provider, special_route["model"])
                special_reasoning = copy.deepcopy(special_route["reasoning"])
                if special_reasoning["mode"] == "adaptive":
                    if special_profile is None:
                        raise _error(f"effective.interactions.{interaction}.specialists.{role}", "Adaptive route requires a complete profile")
                entry["specialists"][role] = {"route": {"model": special_route["model"], "reasoning": special_reasoning}, "provenance": {"model": special_provenance["model"], "reasoning": special_provenance["reasoning"], "profile": special_profile_source}}
        interactions[interaction] = entry
    profiles: dict[str, Any] = {}
    for key, profile in bundle["hosts"][host]["defaults"].get("adaptive_profiles", {}).items():
        profiles[key] = copy.deepcopy(profile)
    for document in frozen["documents"].values():
        if document is not None:
            profiles.update(copy.deepcopy(document.get("adaptive_profiles", {})))
    result: dict[str, Any] = {"host": host, "interactions": interactions, "profiles": profiles}
    agents: dict[str, Any] = {}
    document = frozen["documents"]["global"] or _empty_preferences()
    for role in role_ids:
        route: dict[str, Any] = {}
        provenance: dict[str, str] = {}
        agent_route = document.get("agents", {}).get(role)
        if agent_route:
            for field in ("model", "reasoning"):
                if field in agent_route:
                    route[field] = copy.deepcopy(agent_route[field])
                    provenance[field] = f"global.agents.{role}.{field}"
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
    snapshot_parser.add_argument("--global", dest="global_path", required=True, help="explicit global preferences path for the host")
    snapshot_parser.add_argument("--host", choices=HOSTS, help="orchestration host; defaults to the installed routing/host.json host, else codex")
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
            result = create_snapshot(args.global_path, bypass=args.bypass, host=args.host)
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
