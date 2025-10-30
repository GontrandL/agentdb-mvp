#!/usr/bin/env python3

Minimal MCP stdio server *skeleton* for agentdb.
NOTE: This is a stub to unblock development; it echoes tool calls to the CLI.
You (or Claude) should replace with a proper MCP server when ready.

import sys, json, subprocess, tempfile, os

def read_message():
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        return json.loads(line)
    except Exception:
        return None

def write_message(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

def run_cli(args, stdin_text=None):
    cmd = [sys.executable, "-m", "agentdb.core"] + args
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE if stdin_text else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(stdin_text)
    return p.returncode, out, err

def get_contract(mode="compressed", output_format="json"):
    """
    Fetch contract anchor for agent injection.

    This tool enables agents to dynamically discover and adopt the repository's
    behavioral contract without hardcoded prompts.
    """
    import pathlib

    # Navigate to repo root (two levels up from this script)
    repo_root = pathlib.Path(__file__).parent.parent.parent

    # Import contract injector
    sys.path.insert(0, str(repo_root / "scripts"))
    try:
        from contract_injector import ContractInjector

        injector = ContractInjector(repo_root)

        # Validate contract integrity
        if not injector.validate_contract():
            return {"error": "Contract validation failed", "details": "Hash mismatch or missing contract"}

        # Generate appropriate output
        if output_format == "json" or output_format == "mcp":
            envelope = injector.generate_json_envelope(mode)
            return {
                "ok": True,
                "contract_envelope": envelope,
                "usage": "Inject 'system_message.content' as system prompt"
            }
        elif output_format == "text":
            contract_text = injector.inject_for_claude_code(mode)
            metadata = injector.get_contract_metadata()
            return {
                "ok": True,
                "contract_text": contract_text,
                "contract_hash": metadata["contract_hash"],
                "contract_version": metadata.get("contract_version", "unknown"),
                "usage": "Inject 'contract_text' as system prompt"
            }
        else:
            return {"error": f"Unknown output_format: {output_format}"}

    except Exception as e:
        return {"error": "Contract loading failed", "details": str(e)}


def handle_call(msg):
    # Expect format similar to MCP tool call:
    # {"id":"...","method":"tools/call","params":{"name":"ingest_file","arguments":{...}}}
    params = msg.get("params", {})
    name = params.get("name")
    arguments = params.get("arguments", {})

    if name == "get_contract":
        # New: Contract discovery tool
        mode = arguments.get("mode", "compressed")
        output_format = arguments.get("output_format", "json")
        result = get_contract(mode, output_format)
        write_message({"id": msg.get("id"), "result": result})
        return

    elif name == "ingest_file":
        path = arguments["path"]
        content = arguments["content"]
        code, out, err = run_cli(["ingest","--path",path], stdin_text=content)
    elif name == "focus":
        handle = arguments["handle"]
        depth = str(arguments.get("depth", 1))
        code, out, err = run_cli(["focus","--handle",handle,"--depth",depth])
    elif name == "zoom":
        handle = arguments["handle"]; level = str(arguments["level"])
        code, out, err = run_cli(["zoom","--handle",handle,"--level",level])
    elif name == "patch":
        path = arguments["path"]; hb = arguments["hash_before"]; diff = arguments.get("unified_diff","")
        code, out, err = run_cli(["patch","--path",path,"--hash-before",hb], stdin_text=diff)
    else:
        write_message({"id": msg.get("id"), "error": {"message": f"unknown tool {name}"}}); return
    if code == 0:
        try:
            payload = json.loads(out)
        except Exception:
            payload = {"raw": out}
        write_message({"id": msg.get("id"), "result": payload})
    else:
        write_message({"id": msg.get("id"), "error": {"message": out or err}})

def main():
    # Ultra-minimal loop: read one JSON line per call
    while True:
        msg = read_message()
        if msg is None:
            break
        method = msg.get("method","")
        if method.endswith("tools/call") or method == "tools/call":
            handle_call(msg)
        elif method in ("ping","health"):
            write_message({"id": msg.get("id"), "result": {"ok": True}})
        else:
            write_message({"id": msg.get("id"), "error": {"message": f"unsupported method {method}"}})

if __name__ == "__main__":
    main()


<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "read_message",
      "kind": "function",
      "signature": "def read_message(...)",
      "lines": [
        9,
        16
      ],
      "summary_l0": "Function read_message",
      "contract_l1": "@io see source code"
    },
    {
      "name": "write_message",
      "kind": "function",
      "signature": "def write_message(...)",
      "lines": [
        18,
        20
      ],
      "summary_l0": "Function write_message",
      "contract_l1": "@io see source code"
    },
    {
      "name": "run_cli",
      "kind": "function",
      "signature": "def run_cli(...)",
      "lines": [
        22,
        26
      ],
      "summary_l0": "Function run_cli",
      "contract_l1": "@io see source code"
    },
    {
      "name": "get_contract",
      "kind": "function",
      "signature": "def get_contract(...)",
      "lines": [
        28,
        73
      ],
      "summary_l0": "Function get_contract",
      "contract_l1": "@io see source code"
    },
    {
      "name": "handle_call",
      "kind": "function",
      "signature": "def handle_call(...)",
      "lines": [
        76,
        114
      ],
      "summary_l0": "Function handle_call",
      "contract_l1": "@io see source code"
    },
    {
      "name": "main",
      "kind": "function",
      "signature": "def main(...)",
      "lines": [
        116,
        128
      ],
      "summary_l0": "Function main",
      "contract_l1": "@io see source code"
    }
  ]
}
<!--AGTAG v1 END-->
