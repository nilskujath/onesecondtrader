import re
import subprocess
from pathlib import Path

PYPROJECT_PATH = Path("pyproject.toml")
CHANGELOG_PATH = Path("CHANGELOG.md")


def get_commit_messages():
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        latest_tag = result.stdout.strip()
    except subprocess.CalledProcessError:
        latest_tag = ""

    if latest_tag:
        cmd = ["git", "log", "--pretty=format:%s", f"{latest_tag}..HEAD"]
    else:
        cmd = ["git", "log", "--pretty=format:%s"]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


def determine_bump_level(messages):
    bump = "patch"
    for msg in messages:
        if "BREAKING CHANGE" in msg:
            return "major"
        if msg.startswith("feat"):
            bump = "minor"
        if msg.startswith("fix") and bump != "minor":
            bump = "patch"
    return bump


def bump_version(current, level):
    major, minor, patch = map(int, current.split("."))
    if level == "major":
        major += 1
        minor = 0
        patch = 0
    elif level == "minor":
        minor += 1
        patch = 0
    elif level == "patch":
        patch += 1
    return f"{major}.{minor}.{patch}"


def read_current_version():
    content = PYPROJECT_PATH.read_text()
    match = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', content)
    return match.group(1) if match else None


def update_pyproject(new_version):
    content = PYPROJECT_PATH.read_text()
    updated = re.sub(
        r'version\s*=\s*"\d+\.\d+\.\d+"',
        f'version = "{new_version}"',
        content,
    )
    PYPROJECT_PATH.write_text(updated)


def update_changelog(new_version, messages):
    lines = [f"## v{new_version}\n"]
    for msg in messages:
        lines.append(f"- {msg}\n")
    lines.append("\n")
    if CHANGELOG_PATH.exists():
        lines.append(CHANGELOG_PATH.read_text())
    CHANGELOG_PATH.write_text("".join(lines))


def main():
    current = read_current_version()
    if not current:
        return

    messages = get_commit_messages()
    if not messages:
        return

    level = determine_bump_level(messages)
    new_version = bump_version(current, level)

    update_pyproject(new_version)
    update_changelog(new_version, messages)

    print(new_version)


if __name__ == "__main__":
    main()
