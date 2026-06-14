"""Small Coactra CLI for scaffolding, validation, and environment checks."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coactra")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check local Coactra environment")
    init = sub.add_parser("init", help="create a minimal Coactra project")
    init.add_argument("name")
    init.add_argument("--template", default="agent")
    validate = sub.add_parser("validate", help="validate a JSON/YAML team spec shape")
    validate.add_argument("path")
    return parser


def _doctor() -> int:
    print("coactra doctor")
    print(f"python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    checks = {
        "pydantic": importlib.util.find_spec("pydantic") is not None,
        "pydantic_ai": importlib.util.find_spec("pydantic_ai") is not None,
        "yaml": importlib.util.find_spec("yaml") is not None,
    }
    for name, present in checks.items():
        print(f"{name}={'yes' if present else 'no'}")
    return 0


def _init(name: str, template: str) -> int:
    target = Path(name)
    target.mkdir(parents=True, exist_ok=True)
    app = '''from __future__ import annotations

import asyncio

from coactra import Team


async def main() -> None:
    team = Team.local(model="openai:gpt-4.1-mini")
    agent = await team.add_agent(name="assistant")
    try:
        print(await agent.run("Say hello from Coactra"))
    finally:
        await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
'''
    (target / "app.py").write_text(app)
    (target / ".env.example").write_text("OPENAI_API_KEY=\n")
    readme = (
        f"# {target.name}\n\n"
        f"Created with `coactra init --template {template}`.\n\n"
        "Run:\n\n```bash\npython app.py\n```\n"
    )
    (target / "README.md").write_text(readme)
    print(f"created {target}")
    return 0


def _load_spec(path: Path) -> Any:
    text = path.read_text()
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError("YAML validation requires coactra[workflow] or PyYAML") from exc
        return yaml.safe_load(text)
    return json.loads(text)


def _validate(path_text: str) -> int:
    path = Path(path_text)
    if not path.exists():
        print(f"{path} does not exist", file=sys.stderr)
        return 1
    try:
        data = _load_spec(path)
    except Exception as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("invalid: spec must be an object", file=sys.stderr)
        return 1
    agents = data.get("agents", [])
    if agents is not None and not isinstance(agents, list):
        print("invalid: agents must be a list", file=sys.stderr)
        return 1
    for index, agent in enumerate(agents or []):
        if not isinstance(agent, dict) or not isinstance(agent.get("name"), str):
            print(f"invalid: agents[{index}] must contain a string name", file=sys.stderr)
            return 1
    print(f"valid {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return _doctor()
    if args.command == "init":
        return _init(args.name, args.template)
    if args.command == "validate":
        return _validate(args.path)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
