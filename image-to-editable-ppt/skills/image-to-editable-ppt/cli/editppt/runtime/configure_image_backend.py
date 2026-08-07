#!/usr/bin/env python3
import argparse
import json

from deck_run_state import load_deck, load_jobs, read_json, run_dir_from_target, save_deck, write_json


def backend_contract(args):
    is_builtin = args.backend_id == "builtin-imagegen"
    is_agent_tool = args.backend_id == "agent-image-tool"
    requires_api_key = args.backend_id == "openai-compatible-api"
    contract = {
        "backend_id": args.backend_id,
        "runtime_id": args.runtime_id,
        "tool_name": args.tool_name,
        "tool_call": args.tool_call,
        "fallback_command": args.fallback_command,
        "runtime_home": args.runtime_home,
        "model": None if is_builtin else args.model,
        "fallback_model": "gpt-image-2" if is_builtin or is_agent_tool else None,
        "requires_openai_api_key": requires_api_key,
        "mode_policy": "generate-or-edit-per-asset",
        "chroma_key_helper": "editppt image process-sheet",
        "input_context_policy": args.input_context_policy,
        "save_path_policy": (
            "accept only an explicit output_hint or local path returned by image_gen.imagegen, verify it exists, "
            "import the selected output, and never scan for the newest file"
            if is_builtin
            else (
                "accept only an explicit local path returned by the discovered agent image tool, verify it exists, "
                "then import it with producer provenance; never scan for the newest file"
                if is_agent_tool
                else "write outputs directly to page dir or copy selected outputs before manifest references them"
            )
        ),
        "handoff_rule": (
            "call image_gen.imagegen serially, then import the selected local output; "
            "use editppt image generate/edit only when the built-in tool fallback policy applies"
            if is_builtin
            else (
                "inspect available tools and installed skills, select a candidate only after capability validation, "
                "call it serially, and import its explicit local output; otherwise use the declared CLI fallback"
                if is_agent_tool
                else "call editppt image generate/edit serially; the CLI selects Codex OAuth first and OpenAI-compatible API fallback second"
            )
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
    elif is_agent_tool:
        contract.update(
            {
                "required_capabilities": [
                    "image-generation",
                    "reference-image-editing",
                    "explicit-local-output",
                ],
                "discovery_policy": {
                    "strategy": "inspect-runtime-tools-first",
                    "inspect": ["native tools", "installed skills", "MCP tools", "configured image models"],
                    "reject_if": [
                        "vision-input-only",
                        "text-only",
                        "generation-without-reference-image-editing",
                        "no-explicit-local-output",
                    ],
                },
                "fallback_order": ["codex-oauth", "openai-compatible-api"],
                "fallback_policy": {
                    "on": [
                        "tool-unavailable",
                        "tool-error",
                        "input-unreadable",
                        "no-valid-local-output",
                    ],
                    "missing_required_capability": True,
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
        choices=["builtin-imagegen", "agent-image-tool", "editppt-image-cli", "openai-compatible-api"],
    )
    parser.add_argument("--runtime-id")
    parser.add_argument("--tool-name")
    parser.add_argument("--tool-call")
    parser.add_argument("--model")
    parser.add_argument("--fallback-command")
    parser.add_argument("--runtime-home", default="~/.editppt")
    parser.add_argument("--input-context-policy")
    args = parser.parse_args()

    if args.backend_id == "builtin-imagegen":
        fixed_field_overrides = [
            flag
            for flag, value in (
                ("--tool-name", args.tool_name),
                ("--tool-call", args.tool_call),
                ("--fallback-command", args.fallback_command),
                ("--input-context-policy", args.input_context_policy),
                ("--runtime-id", args.runtime_id),
            )
            if value is not None
        ]
        if fixed_field_overrides:
            parser.error(
                f"{', '.join(fixed_field_overrides)} cannot override the fixed builtin-imagegen contract"
            )
        args.tool_name = "image_gen.imagegen"
        args.tool_call = "image_gen.imagegen"
        args.runtime_id = "codex"
        args.fallback_command = "editppt image generate/edit"
        args.input_context_policy = (
            "generation needs prompt; for editing inspect every local input with view_image first, then pass "
            "prompt plus absolute local paths in referenced_image_paths"
        )
    elif args.backend_id == "agent-image-tool":
        if args.runtime_id is None:
            args.runtime_id = "auto"
        if args.tool_name is None:
            args.tool_name = "auto-discover"
        if args.tool_call is None:
            args.tool_call = "runtime-native image generation/edit tool or skill"
        if args.fallback_command is None:
            args.fallback_command = "editppt image generate/edit --model gpt-image-2"
        if args.input_context_policy is None:
            args.input_context_policy = (
                "inspect every local input with the runtime's vision capability, then pass prompt plus all reference "
                "images using the discovered tool's supported local-path or attachment mechanism"
            )
    else:
        if args.runtime_id is None:
            args.runtime_id = "standalone-cli"
        if args.model is None:
            args.model = "gpt-image-2"
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
    contract = backend_contract(args)
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
