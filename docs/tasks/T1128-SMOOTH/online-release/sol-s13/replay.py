"""Replay the original A5 responses and run the S13 workflow mutations."""

import argparse
import base64
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


EVIDENCE = Path(__file__).resolve().parent
TASK = EVIDENCE.parents[1]
WORKFLOW = Path(".github/workflows/deploy_oss.yml")
ENV = {key: os.environ[key] for key in (
    "PATH", "SystemRoot", "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR", "ProgramFiles"
) if key in os.environ}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def md5(data):
    return base64.b64encode(hashlib.md5(data).digest()).decode()


def git(worktree, *args):
    return subprocess.check_output(["git", *args], cwd=worktree, env=ENV)


def replay_focused(worktree):
    a5 = {case["name"]: case for case in json.loads((TASK / "astra-v5/focused.json").read_bytes())}
    workflow = (worktree / WORKFLOW).read_text(encoding="utf-8")
    start = workflow.index("          check_object_headers() {\n")
    end = workflow.index('          for path in "${paths[@]}"; do', start)
    functions = "\n".join(line[10:] for line in workflow[start:end].splitlines()).rstrip()
    git_dir = git(worktree, "rev-parse", "--absolute-git-dir").decode().strip().replace("\\", "/")
    head = git(worktree, "rev-parse", "HEAD").decode().strip()
    cases = [
        ("working-expectation_git-response /", "crlf", 1, 0),
        ("working-expectation_git-response /index.html", "crlf", 1, 0),
        ("working-expectation_working-response /", "crlf", 0, 1),
        ("working-expectation_working-response /index.html", "crlf", 0, 1),
        ("canonical_wrong-host-only", "blob", 1, 1),
        ("canonical_correct-host", "blob", 0, 0),
        ("canonical_homepage-octet-stream /", "blob", 0, 1),
        ("canonical_homepage-octet-stream /index.html", "blob", 0, 1),
        ("www/sw.js html-mime", "blob", 1, 1),
        ("www/sw-retire.js html-mime", "blob", 1, 1),
    ]
    results = []
    fixtures = {}
    with TemporaryDirectory(prefix="thoradar-s13-focused-") as tmp:
        scratch = Path(tmp)
        for fixture in ("blob", "crlf"):
            (scratch / fixture).mkdir()
        for source in ("index.html", "sw.js", "sw-retire.js"):
            blob = git(worktree, "cat-file", "blob", f"HEAD:{source}")
            crlf = blob.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            assert md5(blob) != md5(crlf), source
            (scratch / "blob" / source).write_bytes(blob)
            (scratch / "crlf" / source).write_bytes(crlf)
            fixtures[source] = {"gitBlob": md5(blob), "crlfCheckout": md5(crlf)}
        for name, fixture, baseline_exit, fixed_exit in cases:
            case = a5[name]
            original = case["bashStdin"]
            prefix = original.split("check_object_headers() {", 1)[0]
            invocation = original.strip().splitlines()[-1]
            repaired = prefix.replace("set -eu\n", "set -euo pipefail\n", 1) + functions + "\n\n" + invocation + "\n"
            env = {**ENV, "GIT_DIR": git_dir, "A5_RESPONSE": case["response"]}
            for version, script, expected in (("A5", original, baseline_exit), ("S13", repaired, fixed_exit)):
                cwd = scratch / fixture
                run = subprocess.run(case["command"], input=script.encode(), cwd=cwd, env=env, capture_output=True)
                stdout, stderr = run.stdout.decode(), run.stderr.decode()
                results.append({
                    "case": name, "version": version, "fixture": fixture,
                    "command": case["command"], "cwd": str(cwd), "gitDir": git_dir, "bashStdin": script,
                    "response": case["response"], "status": run.returncode, "expected": expected,
                    "stdout": stdout, "stderr": stderr,
                })
                print(f"{version} {name}: exit={run.returncode}", flush=True)
                if stdout:
                    print(stdout.splitlines()[-1], flush=True)
                if stderr:
                    print(stderr.rstrip(), flush=True)
    write_json(EVIDENCE / "focused-replay.json", {"head": head, "fixtures": fixtures, "runs": results})
    assert all(run["status"] == run["expected"] for run in results)
    for run in results:
        if run["status"]:
            assert run["stdout"].count("Waiting for ") == 12, run["case"]
            assert run["stderr"].startswith("Verification failed for "), run["case"]


def mutate(worktree, name):
    original = (worktree / WORKFLOW).read_text(encoding="utf-8")
    a5_diff = (TASK / "astra-v5/skip-host.diff").read_text(encoding="utf-8").splitlines()[2:]
    host_before = "\n".join(line[1:] for line in a5_diff if line.startswith("-"))
    host_after = "\n".join(line[1:] for line in a5_diff if line.startswith("+"))
    mutations = {
        "working-tree-md5": (
            'git cat-file blob "HEAD:$source" | openssl dgst -md5 -binary',
            'openssl dgst -md5 -binary "$source"',
            {"CRLF checkout still verifies against the Git blobs": ("crlf-checkout", 1)},
        ),
        "skip-host": (host_before, host_after, {"rejects www-redirect-wrong-host": ("www-redirect-wrong-host", 0)}),
        "ignore-homepage-mime": (
            '                if (!worker && mime != "text/html") exit 1\n', "",
            {f"rejects homepage-octet-stream-{path}": (f"homepage-octet-stream-{path}", 0) for path in ("root", "index")},
        ),
        "www-refresh": (
            """refresh_paths=$(printf 'https://thoradar.online%s\\n' "${paths[@]}")""",
            """refresh_paths=$(printf 'https://thoradar.online%s\\n' "${paths[@]}"; printf 'https://www.thoradar.online%s\\n' "${paths[@]}")""",
            {"normal uploads workers": ("healthy", 0), "retire uploads workers": ("healthy-retire", 0)},
        ),
        "www-allow-302": (
            "if (status != 301 && status != 308) exit 1", "if (status != 301 && status != 302 && status != 308) exit 1",
            {"rejects www-redirect-302": ("www-redirect-302", 0)},
        ),
        "www-active-worker": (
            "verify_object 'https://www.thoradar.online/sw.js' sw-retire.js 1",
            """verify_object 'https://www.thoradar.online/sw.js' "$active_worker" 1""",
            {"rejects www-active-worker": ("www-active-worker", 0)},
        ),
        "skip-md5-comparison": (
            "if (status != 200 || md5 != expected) exit 1", "if (status != 200) exit 1",
            {"rejects wrong-md5": ("wrong-md5-retire", 0)},
        ),
        "short-propagation": (
            "sleep 40", "sleep 5",
            {"main-domain CDN can take six minutes": ("stale-during-propagation-retire", 1)},
        ),
    }
    before, after, targets = mutations[name]
    assert original.count(before) == 1, name
    changed = original.replace(before, after)
    diff = difflib.unified_diff(original.splitlines(keepends=True), changed.splitlines(keepends=True),
                                fromfile=str(WORKFLOW.as_posix()), tofile=f"{name}.yml")
    (EVIDENCE / f"{name}.diff").write_text("".join(diff), encoding="utf-8", newline="\n")
    with TemporaryDirectory(prefix=f"thoradar-s13-{name}-") as tmp:
        candidate = Path(tmp) / "deploy.yml"
        output = Path(tmp) / "deploy.json"
        candidate.write_text(changed, encoding="utf-8", newline="\n")
        command = ["node", "tests/smooth/verify-deploy.mjs", str(output), str(candidate)]
        proc = subprocess.run(command, cwd=worktree, env=ENV, capture_output=True)
        stdout, stderr = proc.stdout.decode(), proc.stderr.decode()
        (EVIDENCE / f"{name}.stdout.txt").write_bytes(proc.stdout)
        (EVIDENCE / f"{name}.stderr.txt").write_bytes(proc.stderr)
        assert output.exists(), (command, stdout, stderr)
        report = json.loads(output.read_bytes())
    failed = [test for test in report["tests"] if not test["pass"]]
    simulations = {scenario: report["simulations"][scenario] for scenario, _ in targets.values()}
    # Retain the full scenario output and relevant mock call arguments, without OSS auth fixture arguments.
    for simulation in simulations.values():
        simulation["calls"] = [call for call in simulation["calls"] if call["tool"] in ("curl", "aliyun", "sleep")]
    write_json(EVIDENCE / f"{name}.json", {
        "command": command, "cwd": str(worktree), "status": proc.returncode, "summary": report["summary"],
        "failed": failed, "scenarios": simulations,
    })
    print(f"{name}: suite exit={proc.returncode} {report['summary']}", flush=True)
    assert proc.returncode == 1, name
    for test, (scenario, status) in targets.items():
        assert any(test in failure["name"] for failure in failed), (name, test, failed)
        assert simulations[scenario]["status"] == status, (name, scenario, status)
        print(f"{scenario}: publish exit={status}", flush=True)
    print(stderr.rstrip(), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worktree", type=lambda path: Path(path).resolve())
    parser.add_argument("action", help="'focused' or the name of one workflow mutation")
    args = parser.parse_args()
    if args.action == "focused":
        replay_focused(args.worktree)
    else:
        mutate(args.worktree, args.action)
