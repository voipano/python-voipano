import pathlib
import re
import subprocess
import sys

files = subprocess.check_output(
    ["git", "ls-files", "-z"]
).split(b"\0")

sensitive_name = re.compile(
    r"(^|/)(\.env(\..*)?|\.npmrc(\..*)?|\.pypirc(\..*)?|"
    r"id_rsa|id_ed25519|\.htpasswd)$|\.(pem|p12|pfx|key)$",
    re.I,
)

patterns = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"npm_[A-Za-z0-9]{30,}"),
    re.compile(r"pypi-[A-Za-z0-9_-]{24,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{35,}", re.I),
]

findings = 0
checked = 0

for raw in files:
    if not raw:
        continue

    name = raw.decode("utf-8", errors="replace")
    path = pathlib.Path(name)
    checked += 1

    if sensitive_name.search(name.replace("\\", "/")):
        print(f"Sensitive filename: {name}")
        findings += 1
        continue

    if not path.is_file():
        continue

    content = path.read_bytes().decode("utf-8", errors="replace")

    if any(pattern.search(content) for pattern in patterns):
        print(f"Possible credential in: {name}")
        findings += 1

print(f"Files checked: {checked}")
print(f"Findings: {findings}")

sys.exit(1 if findings else 0)