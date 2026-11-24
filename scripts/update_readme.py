#!/usr/bin/env python3
"""Update the profile README repository list between marker comments.

Uses only the Python 3 standard library so the same script can run locally
and in GitHub Actions without pip install. groups.yml is parsed with a small
subset parser because PyYAML is not in the standard library.

Grouping precedence:
  1. skip (profile repo, forks, private repos)
  2. archived == true -> archive group
  3. a grouping topic (group-*) -> that group
     (if more than one, the group with the lowest order wins)
  4. name prefix fallback (veil- -> veil group, case-insensitive)
  5. 未分類

Within a group, repositories are sorted by name so the list stays put
when something is merely pushed. Descriptions are shortened for scanning:
a Japanese/English pair split by "/" keeps the Japanese side, and long
text is cut to about DESC_LIMIT characters.

Usage:
  python3 scripts/update_readme.py
  python3 scripts/update_readme.py --overlay-assignments
  python3 scripts/update_readme.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

START_MARK = "<!-- REPOS:START -->"
END_MARK = "<!-- REPOS:END -->"
GENERATED_NOTE = (
    "<!-- この範囲は scripts/update_readme.py が上書きします。手で編集しないでください。 -->"
)
API_VERSION = "2022-11-28"
USER_AGENT = "mt4110-profile-readme"
DESC_LIMIT = 140

_JA = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")

# ---------------------------------------------------------------------------
# Minimal YAML subset (mappings, lists, scalars, comments). No anchors/tags.
# ---------------------------------------------------------------------------


def _parse_scalar(raw: str):
    s = raw.strip()
    if s == "" or s in ("null", "~"):
        return None
    if s in ("true", "True", "yes", "Yes"):
        return True
    if s in ("false", "False", "no", "No"):
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        inner = s[1:-1]
        if s[0] == '"':
            inner = bytes(inner, "utf-8").decode("unicode_escape")
        return inner
    if " #" in s:
        s = s[: s.index(" #")].rstrip()
        return _parse_scalar(s)
    return s


def _parse_yaml(text: str):
    # Strip comments that occupy a whole line; keep inline via _parse_scalar.
    raw_lines = text.splitlines()
    items = []  # (indent, content)
    for line in raw_lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        items.append((indent, line.strip()))

    def parse_block(index: int, indent: int):
        # Peek to decide mapping vs list
        if index >= len(items):
            return None, index
        _i, content = items[index]
        if content.startswith("- "):
            return parse_list(index, indent)
        return parse_map(index, indent)

    def parse_map(index: int, indent: int):
        result = {}
        while index < len(items):
            i, content = items[index]
            if i < indent:
                break
            if i > indent:
                raise ValueError(f"unexpected indent at: {content}")
            if content.startswith("- "):
                break
            if ":" not in content:
                raise ValueError(f"expected key: value at: {content}")
            key, rest = content.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            index += 1
            if rest:
                result[key] = _parse_scalar(rest)
            else:
                # nested block or empty
                if index < len(items) and items[index][0] > indent:
                    value, index = parse_block(index, items[index][0])
                    result[key] = value
                else:
                    result[key] = None
        return result, index

    def parse_list(index: int, indent: int):
        result = []
        while index < len(items):
            i, content = items[index]
            if i < indent:
                break
            if i > indent:
                raise ValueError(f"unexpected indent at: {content}")
            if not content.startswith("- "):
                break
            item_body = content[2:].strip()
            index += 1
            child_indent = indent + 2
            if not item_body:
                if index < len(items) and items[index][0] > indent:
                    value, index = parse_block(index, items[index][0])
                    result.append(value)
                else:
                    result.append(None)
            elif item_body.startswith("- "):
                raise ValueError(f"nested list on same line not supported: {content}")
            elif ":" in item_body:
                key, rest = item_body.split(":", 1)
                key = key.strip()
                rest = rest.strip()
                mapping = {key: _parse_scalar(rest) if rest else None}
                # continuation keys of this list item
                while index < len(items):
                    ni, ncontent = items[index]
                    if ni < child_indent or ncontent.startswith("- "):
                        break
                    if ni != child_indent:
                        # deeper nest under a key
                        break
                    if ":" not in ncontent:
                        raise ValueError(f"expected key: value at: {ncontent}")
                    k, r = ncontent.split(":", 1)
                    k, r = k.strip(), r.strip()
                    index += 1
                    if r:
                        mapping[k] = _parse_scalar(r)
                    elif index < len(items) and items[index][0] > child_indent:
                        mapping[k], index = parse_block(index, items[index][0])
                    else:
                        mapping[k] = None
                # handle first key empty with nested (rare)
                if mapping[key] is None and not rest:
                    pass
                result.append(mapping)
            else:
                result.append(_parse_scalar(item_body))
        return result, index

    if not items:
        return {}
    doc, idx = parse_map(0, items[0][0])
    if idx != len(items):
        raise ValueError(f"unparsed YAML starting at: {items[idx]}")
    return doc


def load_config(path: Path) -> dict:
    data = _parse_yaml(path.read_text(encoding="utf-8"))
    if not data or "groups" not in data:
        raise SystemExit(f"invalid config: {path}")
    groups = data["groups"]
    required = ("id", "title", "topic", "order")
    for group in groups:
        missing = [key for key in required if key not in group]
        if missing:
            raise SystemExit(f"group is missing {missing}: {group}")
    groups = sorted(groups, key=lambda g: int(g["order"]))
    data["groups"] = groups
    ids = [g["id"] for g in groups]
    topics = [g["topic"] for g in groups]
    if len(ids) != len(set(ids)):
        raise SystemExit("groups.yml has a duplicate group id")
    if len(topics) != len(set(topics)):
        raise SystemExit("groups.yml has a duplicate group topic")
    if "archive" not in ids:
        raise SystemExit("groups.yml is missing an archive group (id: archive)")
    known_ids = set(ids)
    known_topics = set(topics)
    data.setdefault("skip", [])
    data.setdefault("assignments", [])
    data.setdefault("fallback", [])
    data.setdefault("uncategorized", {"title": "未分類", "blurb": ""})
    data.setdefault("owner", "mt4110")
    seen_repos = []
    for rule in data["fallback"]:
        if rule.get("group_id") not in known_ids:
            raise SystemExit(f"fallback group_id is unknown: {rule}")
        if not rule.get("prefix"):
            raise SystemExit(f"fallback prefix is empty: {rule}")
    for assignment in data["assignments"]:
        repo = assignment.get("repo")
        topic = assignment.get("topic")
        if not repo:
            raise SystemExit(f"assignment is missing repo: {assignment}")
        if topic not in known_topics:
            raise SystemExit(f"assignment topic is unknown: {assignment}")
        seen_repos.append(repo)
    if len(seen_repos) != len(set(seen_repos)):
        raise SystemExit("groups.yml lists the same repo twice in assignments")
    return data


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------


def _api_request(url: str, token: str | None) -> tuple[object, str | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = json.loads(res.read().decode("utf-8"))
            link = res.headers.get("Link")
            return body, link
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise SystemExit(f"GitHub API error {exc.code} for {url}: {detail}") from exc


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    # <url>; rel="next", <url>; rel="last"
    for part in link_header.split(","):
        if 'rel="next"' in part:
            m = re.search(r"<([^>]+)>", part)
            if m:
                return m.group(1)
    return None


def fetch_repos(owner: str, token: str | None) -> list[dict]:
    url = (
        f"https://api.github.com/users/{owner}/repos"
        f"?per_page=100&type=owner&sort=updated"
    )
    repos: list[dict] = []
    while url:
        body, link = _api_request(url, token)
        if not isinstance(body, list):
            raise SystemExit(f"unexpected API response: {body}")
        repos.extend(body)
        url = _next_link(link)
    return repos


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


def _split_bilingual(text: str) -> str:
    """Keep the Japanese side of a Japanese / English description.

    Slashes inside a Japanese sentence (Git/Docker/K8s など) stay put,
    because the text after them still contains Japanese.
    """
    if not _JA.search(text):
        return text
    for match in re.finditer(r"\s*/\s*", text):
        left = text[: match.start()].rstrip()
        right = text[match.end() :].lstrip()
        if not left or not _JA.search(left):
            continue
        if _JA.search(right):
            continue
        if len(right) < 30 or not re.match(r"[A-Za-z]", right):
            continue
        return left
    return text


def _balanced(text: str) -> bool:
    return text.count("(") == text.count(")") and text.count("（") == text.count("）")


def _sentence_ends(text: str) -> list[int]:
    ends = [i + 1 for i, ch in enumerate(text) if ch in "。！？"]
    ends.extend(m.end() for m in re.finditer(r"[.!?](?:\s|$)", text))
    return sorted(set(ends))


def _shorten(text: str, limit: int = DESC_LIMIT) -> str:
    """Fit a description on a scan of the list.

    Keep the longest run of complete sentences that fits. A short label
    such as 「8080番、誰が使ってる？」 does not count as the whole line.
    If nothing ends inside the limit, cut without opening a parenthesis.
    """
    if len(text) <= limit:
        return text
    fitting = [
        end
        for end in _sentence_ends(text)
        if 24 <= end <= limit and _balanced(text[:end])
    ]
    if fitting:
        return text[: max(fitting)].rstrip()
    room = limit - 1
    cut = text[:room]
    if cut.count("(") > cut.count(")"):
        cut = cut[: cut.rfind("(")]
    if cut.count("（") > cut.count("）"):
        cut = cut[: cut.rfind("（")]
    closer = max(cut.rfind(")"), cut.rfind("）"), cut.rfind(","), cut.rfind("、"))
    if closer >= 40 and _balanced(cut[: closer + 1]):
        cut = cut[: closer + 1]
    else:
        space = cut.rfind(" ")
        if space >= 40:
            cut = cut[:space]
    return cut.rstrip(" 、,;:・-/") + "…"


def clean_description(desc: str | None) -> str:
    if not desc:
        return ""
    text = desc.replace("\r", "\n")
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # 「です。 次」は詰める。「ですか？ still」のラテン文字の前は空けたままにする。
    text = re.sub(
        r"([。、！？])\s+(?=[\u3040-\u30ff\u4e00-\u9fff])",
        r"\1",
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = text.replace(START_MARK, "").replace(END_MARK, "")
    text = _split_bilingual(text)
    text = _shorten(text.strip())
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    return text


def format_item(repo: dict) -> str:
    name = repo["name"]
    url = repo.get("html_url") or f"https://github.com/{repo.get('full_name', name)}"
    desc = clean_description(repo.get("description"))
    if desc:
        return f"- [{name}]({url}) — {desc}"
    return f"- [{name}]({url})"


def topic_to_group(config: dict) -> dict[str, dict]:
    return {g["topic"]: g for g in config["groups"]}


def group_id_map(config: dict) -> dict[str, dict]:
    return {g["id"]: g for g in config["groups"]}


def is_listed(repo: dict, skip: set[str]) -> bool:
    """Public, non-fork repositories except names in skip (the profile repo)."""
    if repo.get("private") or repo.get("visibility") == "private":
        return False
    if repo.get("fork"):
        return False
    if repo.get("name") in skip:
        return False
    return True


def assign_group(repo: dict, config: dict) -> str | None:
    """Return group id, or None for 未分類. Repos in skip should not be called."""
    groups_by_id = group_id_map(config)
    groups_by_topic = topic_to_group(config)
    archive = groups_by_id.get("archive")

    if repo.get("archived"):
        if archive is None:
            raise SystemExit("groups.yml is missing an archive group (id: archive)")
        return "archive"

    topics = repo.get("topics") or []
    matched = [groups_by_topic[t] for t in topics if t in groups_by_topic]
    if matched:
        matched.sort(key=lambda g: int(g["order"]))
        return matched[0]["id"]

    name = repo.get("name") or ""
    for rule in config.get("fallback") or []:
        prefix = str(rule.get("prefix") or "")
        if prefix and name.lower().startswith(prefix.lower()):
            return rule["group_id"]

    return None  # 未分類


def overlay_assignments(repos: list[dict], config: dict) -> None:
    mapping = {a["repo"]: a["topic"] for a in (config.get("assignments") or [])}
    for repo in repos:
        topic = mapping.get(repo["name"])
        if not topic:
            continue
        topics = list(repo.get("topics") or [])
        if topic not in topics:
            topics.append(topic)
        repo["topics"] = topics


def sort_repos(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda r: (r.get("name") or "").casefold())


def render_section(repos: list[dict], config: dict) -> str:
    skip = set(config.get("skip") or [])
    visible = [r for r in repos if is_listed(r, skip)]

    buckets: dict[str, list[dict]] = {g["id"]: [] for g in config["groups"]}
    uncategorized: list[dict] = []
    for repo in visible:
        gid = assign_group(repo, config)
        if gid is None:
            uncategorized.append(repo)
        else:
            buckets[gid].append(repo)

    lines: list[str] = [GENERATED_NOTE, ""]
    for group in config["groups"]:
        items = sort_repos(buckets[group["id"]])
        if not items:
            continue
        title = group["title"]
        blurb = (group.get("blurb") or "").strip()
        lines.append(f"## {title}")
        lines.append("")
        if blurb:
            lines.append(blurb)
            lines.append("")
        if group.get("collapsed"):
            lines.append("<details>")
            lines.append(f"<summary>{title}（{len(items)}件）</summary>")
            lines.append("")
            lines.extend(format_item(r) for r in items)
            lines.append("")
            lines.append("</details>")
        else:
            lines.extend(format_item(r) for r in items)
        lines.append("")

    if uncategorized:
        u = config["uncategorized"]
        items = sort_repos(uncategorized)
        lines.append(f"## {u['title']}")
        lines.append("")
        blurb = (u.get("blurb") or "").strip()
        if blurb:
            lines.append(blurb)
            lines.append("")
        lines.extend(format_item(r) for r in items)
        lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    return text


def bucket_counts(repos: list[dict], config: dict) -> dict[str, int]:
    skip = set(config.get("skip") or [])
    counts = {g["id"]: 0 for g in config["groups"]}
    counts["uncategorized"] = 0
    hidden = 0
    for repo in repos:
        if not is_listed(repo, skip):
            hidden += 1
            continue
        gid = assign_group(repo, config)
        if gid is None:
            counts["uncategorized"] += 1
        else:
            counts[gid] += 1
    counts["hidden"] = hidden
    counts["fetched"] = len(repos)
    return counts


def rewrite_readme(readme: Path, section: str, dry_run: bool) -> bool:
    """Return True if the file would change (or did change)."""
    if not readme.exists():
        raise SystemExit(f"README not found: {readme}")
    original = readme.read_text(encoding="utf-8")
    if original.count(START_MARK) != 1 or original.count(END_MARK) != 1:
        raise SystemExit(
            f"{readme} の {START_MARK} と {END_MARK} は、それぞれ1つだけ必要です。"
        )
    start = original.index(START_MARK) + len(START_MARK)
    end = original.index(END_MARK)
    if end < start:
        raise SystemExit("README markers are in the wrong order.")
    # Keep a blank line after START and before END for readability.
    new = original[:start] + "\n" + section + original[end:]
    if new == original:
        print("README is already up to date.")
        return False
    if dry_run:
        print("README would change (dry-run; not writing).")
        return True
    readme.write_text(new, encoding="utf-8")
    print(f"Updated {readme}")
    return True


def default_paths() -> tuple[Path, Path]:
    here = Path(__file__).resolve()
    root = here.parent.parent
    return root / "groups.yml", root / "README.md"


def main(argv: list[str] | None = None) -> int:
    cfg_default, readme_default = default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=cfg_default)
    parser.add_argument("--readme", type=Path, default=readme_default)
    parser.add_argument(
        "--overlay-assignments",
        action="store_true",
        help="Merge groups.yml assignments into API topics (local preview only).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--print-section",
        action="store_true",
        help="Print the generated section to stdout.",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None
    repos = fetch_repos(config["owner"], token)
    if args.overlay_assignments:
        overlay_assignments(repos, config)
    counts = bucket_counts(repos, config)
    print(
        f"fetched {counts['fetched']}, hidden {counts['hidden']} "
        "(forks, private, or skip)"
    )
    for group in config["groups"]:
        print(f"  {group['id']}: {counts[group['id']]}")
    print(f"  uncategorized: {counts['uncategorized']}")
    section = render_section(repos, config)
    if args.print_section:
        sys.stdout.write(START_MARK + "\n" + section + END_MARK + "\n")
    rewrite_readme(args.readme, section, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
