#!/usr/bin/env python3
"""Append-only run log for design and orchestration runs, replay for resume, and final CSV rows.

Each run writes `<repo>/.clanker/runs/<run>.jsonl`, one JSON event per line, never rewritten.
When the run ends, `finish` replays the log and appends one row to `.clanker/runs.csv` and one
row per finding to `.clanker/findings.csv`.

Usage:
    clanker_log.py start  --repo R --chat design|implementation --host claude|codex --change NAME
                          --routes PATH [--orchestrator-model MODEL/EFFORT]       # prints the run ID
    clanker_log.py event  --repo R --run RUN '{"type": "finding", ...}'
    clanker_log.py replay --repo R --run RUN                                     # prints the state as JSON
    clanker_log.py finish --repo R --run RUN --outcome OUTCOME [--notes TEXT]

Events (every event also gets `at`, an ISO timestamp):
    start         run, chat, host, change, routes {role: {model, effort}}, orchestrator_model
    round-start   gate (plan|code|functional|refactor), round
    round-end     gate, round, native, cross            (each: the reviewer's status)
    finding       gate, round, id, source, severity, summary
    triage        gate, round, id, triage (accept|user-decision|reject), reason
    fixed         gate, round, id, by (implementor|orchestrator)
    user-decision gate, round, id, decision (take|skip)
    usage         role, and any of tokens, seconds, model, effort (observed values only)
    end           outcome (done|stopped-at-limit|blocked|small-job-declined)

Round numbers count up across a run for each gate, so a fresh code gate after a functional fix
cycle continues the numbering. A finding is identified by its gate, round, and ID. Functional
round 1 is the first check; each later functional round is a recheck that ends one fix cycle.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib
import sys
from typing import Any

ROLES = ("implementor", "reviewer", "functional", "cross-review")
NEEDED_ROLES = {"design": ("reviewer", "cross-review"), "implementation": ROLES}
GATES = ("plan", "code", "functional", "refactor")
OUTCOMES = ("done", "stopped-at-limit", "blocked", "small-job-declined")
EVENT_TYPES = ("start", "round-start", "round-end", "finding", "triage", "fixed", "user-decision", "usage", "end")

RUNS_COLUMNS = (
    "run", "chat", "host", "change", "started", "ended", "outcome",
    "orchestrator_model", "implementor_model", "reviewer_model", "functional_model", "cross_review_model",
    "orchestrator_tokens", "implementor_tokens", "reviewer_tokens", "functional_tokens", "cross_review_tokens",
    "cross_review_seconds", "plan_rounds", "code_rounds", "refactor_rounds", "functional_cycles",
    "small_fixes_by_orchestrator", "notes",
)
FINDINGS_COLUMNS = ("run", "gate", "round", "id", "source", "severity", "summary", "triage", "user_decision",
                    "fixed_by", "reason")


class LogError(Exception):
    pass


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# --- Routes -------------------------------------------------------------------------------------


def read_routes(path: pathlib.Path, host: str, needed: tuple[str, ...]) -> dict[str, dict[str, str]]:
    """Read routes.jsonc (JSON plus full-line `//` comments) and return the needed role entries."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise LogError(f"{path}: cannot read routes file ({error})") from error
    try:
        data = json.loads("\n".join(line for line in lines if not line.lstrip().startswith("//")))
    except json.JSONDecodeError as error:
        raise LogError(f"{path}: not valid JSON ({error})") from error
    if not isinstance(data, dict) or data.get("host") != host:
        raise LogError(f"{path}: key `host` must be {host!r}")
    roles = data.get("roles")
    routes = {}
    for role in needed:
        entry = roles.get(role) if isinstance(roles, dict) else None
        if not (isinstance(entry, dict) and all(isinstance(entry.get(k), str) and entry[k].strip()
                                                for k in ("model", "effort"))):
            raise LogError(f"{path}: key `roles.{role}` needs a non-empty string `model` and `effort`")
        routes[role] = {"model": entry["model"], "effort": entry["effort"]}
    return routes


# --- Log ----------------------------------------------------------------------------------------


def log_path(repo: pathlib.Path, run: str) -> pathlib.Path:
    return repo / ".clanker" / "runs" / f"{run}.jsonl"


def append(path: pathlib.Path, event: dict[str, Any], mode: str = "a") -> None:
    if event.get("type") not in EVENT_TYPES:
        raise LogError(f"Unknown event type {event.get('type')!r}")
    event = {**event, "at": event.get("at") or now()}
    try:
        with path.open(mode, encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as error:
        raise LogError(f"{path}: write failed ({error})") from error


def start(repo: pathlib.Path, chat: str, host: str, change: str, routes_path: pathlib.Path,
          orchestrator_model: str = "") -> str:
    routes = read_routes(routes_path, host, NEEDED_ROLES[chat])
    run = f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{change}"
    path = log_path(repo, run)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise LogError(f"{path.parent}: cannot create ({error})") from error
    append(path, {"type": "start", "run": run, "chat": chat, "host": host, "change": change, "routes": routes,
                  "orchestrator_model": orchestrator_model}, mode="x")
    return run


def read_events(path: pathlib.Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise LogError(f"{path}: cannot read run log ({error})") from error
    events = [json.loads(line) for line in lines if line.strip()]
    if not events or events[0].get("type") != "start":
        raise LogError(f"{path}: run log does not begin with a start event")
    return events


def replay(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Rebuild the run state: gate, round, findings, open work, pending decisions, cycles, routes, usage."""
    first = events[0]
    state: dict[str, Any] = {
        "run": first["run"], "chat": first["chat"], "host": first["host"], "change": first["change"],
        "routes": first["routes"], "orchestrator_model": first.get("orchestrator_model", ""),
        "started": first["at"], "ended": None, "outcome": None,
        "gate": None, "round": None, "round_open": False, "gate_rounds": 0,
        "rounds": {gate: 0 for gate in GATES}, "functional_cycles": 0,
        "findings": {}, "usage": {}, "small_fixes": 0,
    }
    for event in events[1:]:
        kind = event["type"]
        if kind == "round-start":
            gate = event["gate"]
            if gate != state["gate"] or gate == "functional":
                state["gate_rounds"] = 0
            state.update(gate=gate, round=event["round"], round_open=True)
            state["gate_rounds"] += 1
            state["rounds"][gate] += 1
            if gate == "functional":
                state["functional_cycles"] = state["rounds"]["functional"] - 1
        elif kind == "round-end":
            state["round_open"] = False
        elif kind == "finding":
            key = f"{event['gate']}/{event['round']}/{event['id']}"
            state["findings"][key] = {
                "gate": event["gate"], "round": event["round"], "id": event["id"], "source": event.get("source", ""),
                "severity": event.get("severity", ""), "summary": event.get("summary", ""),
                "triage": "", "user_decision": "", "fixed_by": "", "reason": ""}
        elif kind in ("triage", "fixed", "user-decision"):
            key = f"{event['gate']}/{event['round']}/{event['id']}"
            finding = state["findings"].get(key)
            if finding is None:
                raise LogError(f"{kind} event for unknown finding {key}")
            if kind == "triage":
                finding.update(triage=event["triage"], reason=event.get("reason", ""))
            elif kind == "fixed":
                finding["fixed_by"] = event["by"]
                state["small_fixes"] += event["by"] == "orchestrator"
            else:
                finding["user_decision"] = event["decision"]
        elif kind == "usage":
            usage = state["usage"].setdefault(event["role"], {})
            for key in ("tokens", "seconds"):
                if isinstance(event.get(key), (int, float)):
                    usage[key] = usage.get(key, 0) + event[key]
            for key in ("model", "effort"):
                if event.get(key):
                    usage[key] = event[key]
        elif kind == "end":
            state.update(ended=event["at"], outcome=event["outcome"])
    findings = state["findings"].values()
    state["open_findings"] = [f for f in findings if f["fixed_by"] == "" and f["gate"] != "refactor" and (
        f["triage"] == "accept" or f["user_decision"] == "take")]
    state["pending_decisions"] = [f for f in findings if f["triage"] == "user-decision" and not f["user_decision"]]
    state["untriaged"] = [f for f in findings if not f["triage"]]
    return state


# --- Final rows ---------------------------------------------------------------------------------


def model_column(state: dict[str, Any], role: str) -> str:
    observed = state["usage"].get(role, {})
    if observed.get("model"):
        return f"{observed['model']}/{observed.get('effort') or 'unknown'}"
    route = state["routes"].get(role)
    return f"{route['model']}/{route['effort']} (req)" if route else ""


def run_row(state: dict[str, Any], notes: str) -> dict[str, Any]:
    usage = state["usage"]
    row = {"run": state["run"], "chat": state["chat"], "host": state["host"], "change": state["change"],
           "started": state["started"], "ended": state["ended"], "outcome": state["outcome"],
           "orchestrator_model": state["orchestrator_model"],
           "cross_review_seconds": usage.get("cross-review", {}).get("seconds", ""),
           "plan_rounds": state["rounds"]["plan"], "code_rounds": state["rounds"]["code"],
           "refactor_rounds": state["rounds"]["refactor"], "functional_cycles": state["functional_cycles"],
           "small_fixes_by_orchestrator": state["small_fixes"], "notes": notes}
    for role in ROLES:
        column = role.replace("-", "_")
        row[f"{column}_model"] = model_column(state, role)
        row[f"{column}_tokens"] = usage.get(role, {}).get("tokens", "")
    row["orchestrator_tokens"] = usage.get("orchestrator", {}).get("tokens", "")
    return row


def append_rows(path: pathlib.Path, columns: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    """Append rows with the csv writer, writing the header first when the file is absent."""
    try:
        if path.exists():
            with path.open(newline="", encoding="utf-8") as handle:
                header = next(csv.reader(handle), None)
            if header != list(columns):
                raise LogError(f"{path}: existing header does not match these columns; use a new versioned file")
            new = False
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            new = True
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, quoting=csv.QUOTE_ALL)
            if new:
                writer.writeheader()
            writer.writerows(rows)
    except OSError as error:
        raise LogError(f"{path}: write failed ({error})") from error


def finish(repo: pathlib.Path, run: str, outcome: str, notes: str = "") -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise LogError(f"Outcome must be one of {', '.join(OUTCOMES)}")
    path = log_path(repo, run)
    if replay(read_events(path))["outcome"]:
        raise LogError(f"{path}: run already ended")
    append(path, {"type": "end", "outcome": outcome})
    state = replay(read_events(path))
    append_rows(repo / ".clanker" / "runs.csv", RUNS_COLUMNS, [run_row(state, notes)])
    append_rows(repo / ".clanker" / "findings.csv", FINDINGS_COLUMNS,
                [{"run": run, **finding} for finding in state["findings"].values()])
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append-only run log and final CSV rows.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "event", "replay", "finish"):
        command = commands.add_parser(name)
        command.add_argument("--repo", type=pathlib.Path, default=pathlib.Path.cwd())
        if name == "start":
            command.add_argument("--chat", required=True, choices=tuple(NEEDED_ROLES))
            command.add_argument("--host", required=True, choices=("claude", "codex"))
            command.add_argument("--change", required=True)
            command.add_argument("--routes", required=True, type=pathlib.Path)
            command.add_argument("--orchestrator-model", default="")
        else:
            command.add_argument("--run", required=True)
        if name == "event":
            command.add_argument("event", help="The event as a JSON object with a `type`")
        if name == "finish":
            command.add_argument("--outcome", required=True, choices=OUTCOMES)
            command.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            print(start(args.repo, args.chat, args.host, args.change, args.routes, args.orchestrator_model))
        elif args.command == "event":
            try:
                event = json.loads(args.event)
            except json.JSONDecodeError as error:
                raise LogError(f"Event is not valid JSON ({error})") from error
            if not isinstance(event, dict):
                raise LogError("Event must be a JSON object")
            path = log_path(args.repo, args.run)
            if not path.exists():
                raise LogError(f"{path}: no such run log; start the run first")
            append(path, event)
        elif args.command == "replay":
            print(json.dumps(replay(read_events(log_path(args.repo, args.run))), indent=2))
        else:
            finish(args.repo, args.run, args.outcome, args.notes)
            print(f"Appended rows to {args.repo / '.clanker' / 'runs.csv'} and findings.csv")
    except LogError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
