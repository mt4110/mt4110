#!/usr/bin/env python3
"""Stdlib tests for profile README grouping. No network."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import update_readme as ur

ROOT = Path(__file__).resolve().parent.parent


def _config() -> dict:
    return {
        "owner": "mt4110",
        "skip": ["mt4110"],
        "groups": [
            {
                "id": "veil",
                "title": "veil シリーズ",
                "topic": "group-veil",
                "order": 1,
                "collapsed": False,
                "blurb": "手元で動くセキュリティ向けのOSSです。",
            },
            {
                "id": "devtools",
                "title": "開発ツール",
                "topic": "group-devtools",
                "order": 2,
                "collapsed": False,
                "blurb": "",
            },
            {
                "id": "archive",
                "title": "アーカイブ",
                "topic": "group-archive",
                "order": 9,
                "collapsed": True,
                "blurb": "止めたものです。",
            },
        ],
        "uncategorized": {"title": "未分類", "blurb": "topic がありません。"},
        "fallback": [{"prefix": "veil-", "group_id": "veil"}],
        "assignments": [],
    }


def _repo(name: str, **extra) -> dict:
    data = {
        "name": name,
        "full_name": f"mt4110/{name}",
        "html_url": f"https://github.com/mt4110/{name}",
        "description": extra.pop("description", None),
        "fork": False,
        "private": False,
        "archived": False,
        "topics": [],
    }
    data.update(extra)
    return data


class DescriptionTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(ur.clean_description(None), "")
        self.assertEqual(ur.clean_description("  \n\t "), "")

    def test_space_after_japanese_punctuation(self):
        self.assertEqual(ur.clean_description("です。 次です。"), "です。次です。")
        self.assertEqual(
            ur.clean_description("ですか？ stillは続きます。"),
            "ですか？ stillは続きます。",
        )

    def test_strips_bold_and_collapses_space(self):
        text = "**RecWatch** は、動画を\n変換します。"
        self.assertEqual(ur.clean_description(text), "RecWatch は、動画を 変換します。")

    def test_keeps_japanese_side_of_translation(self):
        text = (
            "(Image Optim.appのCLI版)冗長データを削って画像を軽量化する決定論的ロスレスCLI"
            " / Deterministic lossless image optimizer CLI (size delta + time)."
        )
        self.assertEqual(
            ur.clean_description(text),
            "(Image Optim.appのCLI版)冗長データを削って画像を軽量化する決定論的ロスレスCLI",
        )

    def test_keeps_slash_inside_japanese_sentence(self):
        text = (
            "「8080番、誰が使ってる？」をもう推測しない。"
            "Git/Docker/K8sのコンテキスト付きでポートを可視化できるツール。"
            "/ Stop guessing what is using the port with a long English translation here."
        )
        cleaned = ur.clean_description(text)
        self.assertIn("Git/Docker/K8s", cleaned)
        self.assertNotIn("Stop guessing", cleaned)

    def test_keeps_english_slash_lists(self):
        text = "Google / Apple / Cloudflare Public IP Range Fetcher"
        self.assertEqual(ur.clean_description(text), text)
        license_line = (
            "Local file exchange gateway: scan, sanitize, sign. Personal portfolio / Apache-2.0."
        )
        self.assertEqual(ur.clean_description(license_line), license_line)

    def test_shortens_long_text_on_sentence_boundary(self):
        sentence = "あ" * 80 + "。"
        extra = "い" * 80 + "。"
        cleaned = ur.clean_description(sentence + extra)
        self.assertEqual(cleaned, sentence)
        self.assertLessEqual(len(cleaned), ur.DESC_LIMIT)

    def test_keeps_every_complete_sentence_that_fits(self):
        first = "あ" * 40 + "。"
        second = "い" * 40 + "。"
        third = "う" * 80 + "。"
        self.assertEqual(ur.clean_description(first + second + third), first + second)

    def test_english_sentence_beats_a_cut_inside_parentheses(self):
        text = (
            "High-performance Japanese Station Converter & API. "
            "Auto-updating, diff-aware, multi-DB delivery "
            "(PostgreSQL / MySQL / SQLite artifact), written in Rust & Next.js "
            "with a much longer tail so the whole line exceeds the scan limit."
        )
        self.assertEqual(
            ur.clean_description(text),
            "High-performance Japanese Station Converter & API.",
        )

    def test_hard_cut_uses_ellipsis(self):
        cleaned = ur.clean_description("あ" * 200)
        self.assertLessEqual(len(cleaned), ur.DESC_LIMIT)
        self.assertTrue(cleaned.endswith("…"))

    def test_escapes_html_and_strips_markers(self):
        cleaned = ur.clean_description("a <b> c <!-- REPOS:END -->")
        self.assertNotIn(ur.END_MARK, cleaned)
        self.assertIn("&lt;b&gt;", cleaned)
        self.assertNotIn("<b>", cleaned)

    def test_idempotent(self):
        raw = "**名前** です。 / English translation that is certainly long enough to drop."
        once = ur.clean_description(raw)
        self.assertEqual(ur.clean_description(once), once)


class GroupingTests(unittest.TestCase):
    def test_precedence(self):
        cfg = _config()
        archived = _repo(
            "veil-old",
            archived=True,
            topics=["group-veil", "group-devtools"],
        )
        self.assertEqual(ur.assign_group(archived, cfg), "archive")
        both = _repo("tool", topics=["group-devtools", "group-veil"])
        self.assertEqual(ur.assign_group(both, cfg), "veil")
        prefixed = _repo("Veil-Keeper")
        self.assertEqual(ur.assign_group(prefixed, cfg), "veil")
        plain = _repo("notes")
        self.assertIsNone(ur.assign_group(plain, cfg))

    def test_overlay_then_topic_wins_over_prefix(self):
        cfg = _config()
        cfg["assignments"] = [{"repo": "veil-rs", "topic": "group-devtools"}]
        repos = [_repo("veil-rs")]
        ur.overlay_assignments(repos, cfg)
        self.assertEqual(ur.assign_group(repos[0], cfg), "devtools")

    def test_render_skips_fork_private_and_profile_and_sorts_by_name(self):
        cfg = _config()
        repos = [
            _repo("zzz", description="後"),
            _repo("aaa", description="先"),
            _repo("Forked", fork=True, description="fork"),
            _repo("secret", private=True, description="private"),
            _repo("hidden", visibility="private", description="private2"),
            _repo("mt4110", description="profile"),
            _repo("veil-b", description="ビー"),
            _repo("Veil-A", description="エー"),
            _repo("old", archived=True, description="古い"),
        ]
        text = ur.render_section(repos, cfg)
        self.assertLess(text.index("Veil-A"), text.index("veil-b"))
        self.assertLess(text.index("[aaa]"), text.index("[zzz]"))
        self.assertNotIn("Forked", text)
        self.assertNotIn("secret", text)
        self.assertNotIn("hidden", text)
        self.assertNotIn("mt4110/mt4110", text)
        self.assertIn("<details>", text)
        self.assertIn("アーカイブ（1件）", text)
        self.assertNotIn("## 開発ツール", text)
        self.assertIn(ur.GENERATED_NOTE, text)

    def test_rewrite_is_idempotent_and_dry_run_does_not_write(self):
        cfg = _config()
        section = ur.render_section([_repo("aaa", description="ひとつ")], cfg)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "README.md"
            path.write_text(
                "intro\n\n" + ur.START_MARK + "\n" + ur.END_MARK + "\n",
                encoding="utf-8",
            )
            self.assertTrue(ur.rewrite_readme(path, section, dry_run=False))
            once = path.read_text(encoding="utf-8")
            self.assertIn("intro", once)
            self.assertFalse(ur.rewrite_readme(path, section, dry_run=False))
            self.assertEqual(path.read_text(encoding="utf-8"), once)
            self.assertTrue(ur.rewrite_readme(path, section + "x\n", dry_run=True))
            self.assertEqual(path.read_text(encoding="utf-8"), once)

    def test_rewrite_rejects_duplicate_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "README.md"
            path.write_text(
                ur.START_MARK + "\n" + ur.END_MARK + "\n" + ur.END_MARK + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                ur.rewrite_readme(path, "x\n", dry_run=False)


class ConfigTests(unittest.TestCase):
    def test_real_groups_file(self):
        cfg = ur.load_config(ROOT / "groups.yml")
        self.assertEqual(cfg["owner"], "mt4110")
        self.assertEqual([g["id"] for g in cfg["groups"]], [
            "veil",
            "devtools",
            "japan-data",
            "macos",
            "lab",
            "archive",
        ])
        self.assertTrue(cfg["groups"][-1]["collapsed"])
        self.assertEqual(len(cfg["assignments"]), 45)
        dot = next(a for a in cfg["assignments"] if a["repo"] == ".github")
        self.assertEqual(dot["topic"], "group-devtools")
        topics = {g["topic"] for g in cfg["groups"]}
        self.assertEqual({a["topic"] for a in cfg["assignments"]}, topics)

    def test_intro_has_no_hype_words(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        intro = readme.split(ur.START_MARK)[0]
        for word in ("最強", "鉄壁", "突破不可能"):
            self.assertNotIn(word, intro)
        # The biography above the markers is the owner's. Do not pin its wording.
        self.assertIn("# mt4110", intro)
        self.assertGreater(len(intro.strip()), len("# mt4110"))
        self.assertEqual(readme.count(ur.START_MARK), 1)
        self.assertEqual(readme.count(ur.END_MARK), 1)


if __name__ == "__main__":
    unittest.main()
