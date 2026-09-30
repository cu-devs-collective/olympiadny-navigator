"""Execute this project's DATA-API scenario against an explicitly supplied server."""

import argparse
import json
import pathlib
import urllib.error
import urllib.request
from typing import Any

import jsonschema
import yaml


ROOT = pathlib.Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="For example http://localhost:8080/api")
    args = parser.parse_args()
    config = yaml.safe_load((ROOT / "DATA-API.yaml").read_text())
    variables: dict[str, str] = {}

    def interpolate(value: Any) -> Any:
        if isinstance(value, str):
            for key, replacement in variables.items():
                value = value.replace("${" + key + "}", replacement)
            return value
        if isinstance(value, dict):
            return {key: interpolate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [interpolate(item) for item in value]
        return value

    def execute(step):
        request = interpolate(step.get("request", {}))
        path = step["path"]
        for key, value in request.get("path", {}).items():
            path = path.replace("{" + key + "}", str(value))
        body = request.get("body")
        req = urllib.request.Request(
            args.base_url.rstrip("/") + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                **interpolate(config["api"].get("defaultHeaders", {})),
                **request.get("headers", {}),
            },
            method=step["method"],
        )
        try:
            response = urllib.request.urlopen(req, timeout=step.get("timeoutMs", 5000) / 1000)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            status = response.status
            raw = response.read()
        if status not in step["expected"]["statusCodes"]:
            raise RuntimeError(f"{step['id']}: unexpected HTTP {status}")
        data = json.loads(raw) if raw else {}
        for field in step["expected"].get("requiredFields", []):
            if field not in data:
                raise RuntimeError(f"{step['id']}: missing field {field}")
        if "bodySchema" in step["expected"]:
            jsonschema.validate(data, step["expected"]["bodySchema"])
        for key, path in step.get("extract", {}).items():
            item = data
            for segment in path.removeprefix("$.").split("."):
                item = item[segment]
            variables[key] = str(item)
        print(f"OK {step['id']} (HTTP {status})")

    try:
        for step in config["checks"]:
            execute(step)
    finally:
        if "sessionToken" in variables:
            for step in config.get("cleanup", []):
                execute(step)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
