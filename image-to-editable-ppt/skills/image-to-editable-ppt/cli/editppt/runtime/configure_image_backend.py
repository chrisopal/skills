#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from deck_run_state import load_deck, load_jobs, read_json, run_dir_from_target, save_deck, write_json


def validate_host_contract(contract):
    """Validate discovery evidence, not tool availability (only the host can observe that)."""
    def fail(message):
        raise ValueError(f"Invalid host-tool contract: {message}")

    def names(value, label):
        if not isinstance(value, list) or any(
            not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:/-]*", name)
            for name in value
        ) or len(value) != len(set(value)):
            fail(f"{label} must be a list of unique parameter names")
        return set(value)

    if not isinstance(contract, dict) or contract.get("schema_version") != 1:
        fail("schema_version must be 1")
    for key in ("discovery_evidence", "input_context_policy", "save_path_policy"):
        if not isinstance(contract.get(key), str) or not contract[key].strip():
            fail(f"{key} is required")
    if not isinstance(contract.get("fallback_policy", {}), dict):
        fail("fallback_policy must be an object")
    if contract.get("fallback_order") or contract.get("fallback_command") or contract.get("fallback_policy", {}).get("on"):
        fail("host tools do not permit implicit CLI/API fallback")
    observed = contract.get("observed_tools")
    operations = contract.get("operations")
    if not isinstance(observed, dict) or not observed or not isinstance(operations, dict):
        fail("observed_tools and operations are required")
    for tool, schema in observed.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:/-]*", tool) or not isinstance(schema, dict):
            fail("observed tool names must be native tool identifiers, never shell commands")
        parameters = names(schema.get("parameters"), f"{tool}.parameters")
        required = names(schema.get("required_parameters"), f"{tool}.required_parameters")
        if not required <= parameters:
            fail(f"{tool} declares required parameters missing from its observed schema")
    if set(operations) != {"generate", "edit"}:
        fail("operations must contain exactly generate and edit")
    for mode in ("generate", "edit"):
        operation = operations.get(mode)
        if not isinstance(operation, dict):
            fail(f"operations.{mode} is required")
        tool = operation.get("tool_name")
        if not isinstance(tool, str) or tool not in observed:
            fail(f"operations.{mode}.tool_name must match an observed tool")
        required = names(operation.get("required_parameters"), f"operations.{mode}.required_parameters")
        schema = observed[tool]
        if not set(schema["required_parameters"]) <= required <= set(schema["parameters"]):
            fail(f"operations.{mode} must cover observed required parameters without inventing parameters")
        for field in (("prompt_parameter", "image_parameter") if mode == "edit" else ("prompt_parameter",)):
            if not isinstance(operation.get(field), str) or operation[field] not in required:
                fail(f"operations.{mode}.{field} must name a required parameter")
        if mode == "edit" and operation["prompt_parameter"] == operation["image_parameter"]:
            fail("edit prompt and image parameters must be distinct")
    return contract


def load_host_contract(path):
    if not path:
        raise ValueError("host-tool contract requires a JSON file")
    try:
        contract = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read host-tool contract: {exc}") from exc
    validate_host_contract(contract)
    allowed = {"schema_version", "discovery_evidence", "observed_tools", "operations", "input_context_policy", "save_path_policy"}
    if set(contract) - allowed:
        raise ValueError("Invalid host-tool contract: unsupported fields; only discovery and operation fields are accepted")
    return {
        **contract,
        "backend_id": "host-tool",
        "requires_openai_api_key": False,
        "mode_policy": "generate-or-edit-per-asset",
        "chroma_key_helper": "editppt image process-sheet",
        "fallback_order": [],
        "fallback_policy": {"on": [], "missing_optional_parameters": False},
        "handoff_rule": (
            "Recheck the exact observed tool and required parameters in the current host session; "
            "call operations.generate/edit through native host tools serially, never as shell commands. "
            "Inspect edit inputs first and follow input_context_policy. Follow save_path_policy but accept "
            "only an explicit local output path returned by that call, verify it exists, and import it "
            "with --backend host-tool --tool-name ACTUAL_TOOL. Never scan for the newest file. "
            "If the tool, input, or valid local result is unavailable, fail the page; never fall back to CLI/API."
        ),
    }


def backend_contract(args):
    is_builtin = args.backend_id == "builtin-imagegen"
    requires_api_key = args.backend_id == "openai-compatible-api"
    contract = {
        "backend_id": args.backend_id,
        "tool_name": args.tool_name,
        "tool_call": args.tool_call,
        "fallback_command": args.fallback_command,
        "runtime_home": args.runtime_home,
        "model": None if is_builtin else args.model,
        "requires_openai_api_key": requires_api_key,
        "mode_policy": "generate-or-edit-per-asset",
        "chroma_key_helper": "editppt image process-sheet",
        "input_context_policy": args.input_context_policy,
        "save_path_policy": (
            "accept only an explicit output_hint or local path returned by image_gen.imagegen, verify it exists, "
            "import the selected output, and never scan for the newest file"
            if is_builtin
            else "write outputs directly to page dir or copy selected outputs before manifest references them"
        ),
        "handoff_rule": (
            "call image_gen.imagegen serially, then import the selected local output; "
            "use editppt image generate/edit only when the built-in tool fallback policy applies"
            if is_builtin
            else "call editppt image generate/edit serially; the CLI selects Codex OAuth first and OpenAI-compatible API fallback second"
        ),
    }
    if is_builtin:
        contract.update(
            {
                "fallback_order": ["codex-oauth", "openai-compatible-api"],
                "required_parameters": {
                    "generate": ["prompt"],
                    "edit": ["prompt", "referenced_image_paths"],
                },
                "fallback_policy": {
                    "on": [
                        "tool-unavailable",
                        "tool-error",
                        "input-unreadable",
                        "no-valid-local-output",
                    ],
                    "missing_optional_parameters": False,
                },
            }
        )
    return contract


def main():
    parser = argparse.ArgumentParser(description="Record the run-level image backend contract.")
    parser.add_argument("run")
    parser.add_argument(
        "--backend-id",
        default="editppt-image-cli",
        choices=["builtin-imagegen", "editppt-image-cli", "openai-compatible-api", "host-tool"],
    )
    parser.add_argument("--contract", help="JSON contract for a discovered native host tool")
    parser.add_argument("--tool-name")
    parser.add_argument("--tool-call")
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--fallback-command")
    parser.add_argument("--runtime-home", default="~/.editppt")
    parser.add_argument("--input-context-policy")
    args = parser.parse_args()

    host = None
    if args.backend_id == "host-tool":
        if any((args.tool_name, args.tool_call, args.fallback_command, args.input_context_policy)):
            parser.error("host-tool contract fields cannot be overridden by CLI flags")
        try:
            host = load_host_contract(args.contract)
        except ValueError as exc:
            parser.error(str(exc))
    elif args.contract:
        parser.error("--contract requires --backend-id host-tool")

    if args.backend_id == "builtin-imagegen":
        fixed_field_overrides = [
            flag
            for flag, value in (
                ("--tool-name", args.tool_name),
                ("--tool-call", args.tool_call),
                ("--fallback-command", args.fallback_command),
                ("--input-context-policy", args.input_context_policy),
            )
            if value is not None
        ]
        if fixed_field_overrides:
            parser.error(
                f"{', '.join(fixed_field_overrides)} cannot override the fixed builtin-imagegen contract"
            )
        args.tool_name = "image_gen.imagegen"
        args.tool_call = "image_gen.imagegen"
        args.fallback_command = "editppt image generate/edit"
        args.input_context_policy = (
            "generation needs prompt; for editing inspect every local input with view_image first, then pass "
            "prompt plus absolute local paths in referenced_image_paths"
        )
    else:
        if args.tool_name is None:
            args.tool_name = "editppt image"
        if args.tool_call is None:
            args.tool_call = "editppt image generate/edit"
        if args.fallback_command is None:
            args.fallback_command = "editppt image"
        if args.input_context_policy is None:
            args.input_context_policy = "pass edit targets and strict visual references via editppt image edit --image"

    run_dir = run_dir_from_target(args.run)
    deck = load_deck(run_dir)
    contract = host if host is not None else backend_contract(args)
    deck["image_backend"] = contract
    save_deck(run_dir, deck)

    jobs = load_jobs(run_dir)
    for page in jobs.get("pages", []):
        request_path = run_dir / page["page_request"]
        request = read_json(request_path)
        request["image_backend"] = contract
        write_json(request_path, request)
    print(json.dumps({"image_backend": contract}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
