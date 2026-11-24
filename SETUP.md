# プロフィール README の自動グループ分け

公開リポジトリをトピックでグループ分けし、`mt4110/mt4110` の README に書き出します。フォーク、非公開リポジトリ、プロフィール用リポジトリ自身は出しません。

## 手順

1. このブランチを `main` にマージする前に、グループ用トピックを付ける。まず確認だけする。

   ```bash
   ./apply-topics.sh
   ```

   問題なければ、自分の手で付ける。

   ```bash
   ./apply-topics.sh --apply
   ```

   `gh` へのログインが必要です。既存のトピックは消しません。`bash` 3.2 でも動きます。アーカイブ済みリポジトリへ topic を付けられるかは、未確認です。付かなくても、GitHub 上で Archived ならアーカイブ欄へ自動で入ります。

2. `main` にマージする。リポジトリの Actions を許可する。Settings → Actions → General → Workflow permissions が **Read and write** であることを確認する（ここが Read だけだと、workflow は一覧を作れても push できません）。

3. Actions タブから `Update profile README` を `workflow_dispatch` で一度回し、コミットが入るか確認する。内容が同じならコミットは作られません。

4. [github.com/mt4110](https://github.com/mt4110) を開いて、プロフィールに一覧が出ているか見る。

ブランチ保護を付ける場合は、github-actions[bot] が `README.md` を push できる設定にしてください。

`apply-topics.sh --apply` は、このリポジトリ以外の公開リポジトリを変更します。CI からは呼びません。

## 新しいリポジトリを足したとき

次のいずれかです。何もしないと、次の更新で「未分類」に出ます（消えて見えなくなることはありません）。

- `gh repo edit mt4110/<name> --add-topic group-veil` のように、グループ用トピックを1つ付ける。使える topic は下表。
- 名前が `veil-` で始まる場合は、トピックなしでも veil グループに入る。
- GitHub 上で Archive したリポジトリは、トピックなしでもアーカイブ欄に入る（折りたたみ表示）。

反映は、次の自動実行か、Actions の手動実行です。

他のリポジトリを作った瞬間や、topic を付けた瞬間に、この workflow を起動することはできません。GitHub Actions には「自分の別リポジトリが変わったら」というイベントがなく、公開イベントにも topic の変更は出てきません。別リポジトリから `workflow_dispatch` を叩くには、このリポジトリへ書き込める PAT などが送り手側に必要です。資格情報を増やさず、他リポジトリにも workflow を足さないため、起動は毎日 9:17（日本時間）ごろの schedule と、手動の `workflow_dispatch` だけにしています。schedule は GitHub 側の混雑で遅れることがあります。すぐ反映したいときは手動で回してください。

`musubi-foundation` と `pi-musubi-core` は、いま GitHub 上で Archived です。反例としてアーカイブ欄に残すため、`group-archive` も assignments に入れています。Archive を外したあともアーカイブ欄に置くためのもので、外すかどうかは別に判断してください。

## グループとトピック

| グループ | topic | 備考 |
| --- | --- | --- |
| veil シリーズ（セキュリティOSS） | `group-veil` | 名前が `veil-` で始まるリポジトリの予備ルールあり |
| 開発ツール | `group-devtools` | |
| 日本向けデータ変換 | `group-japan-data` | |
| macOSアプリ | `group-macos` | |
| 実験・研究 | `group-lab` | |
| アーカイブ | `group-archive` | GitHub の Archived は自動でここへ入る |
| 未分類 | （topic なし） | 付け忘れを見失わないための欄 |

振り分けの順は次のとおりです。

1. フォーク、非公開、`mt4110` 自身は出さない
2. Archived ならアーカイブ
3. `group-*` トピックが付いていれば、そのグループ（複数付いているときは、`groups.yml` の order が小さい方）
4. 名前が `veil-` で始まるなら veil グループ
5. それ以外は未分類

同じグループの中は、リポジトリ名の昇順です。push しただけでは順番が動かないので、毎日の実行で diff が荒れません。

割り当て表の本体は `groups.yml` の `assignments` です。

## 一覧の見た目

各行はリンクと説明です。説明は次のように短くしています。

- 改行はスペースにまとめ、`**太字**` は外す
- `日本語 / English` のようにスラッシュのあとが英語の対訳なら、日本語側だけ残す。文中の `Git/Docker` のように続きが日本語のスラッシュは残す
- おおよそ140字を超えるものは、句点があればそこで切り、なければ省略記号を付ける

説明の全文は、各リポジトリ側にあります。

## スクリプトについて

`scripts/update_readme.py` は Python 3 の標準ライブラリだけを使います。ローカルでも Actions でも、追加のパッケージは不要です。設定は `groups.yml` ですが、PyYAML は使わず、この用途向けの小さなパーサで読んでいます。

一覧は `<!-- REPOS:START -->` と `<!-- REPOS:END -->` のあいだだけを書き直します。マーカーの外（自己紹介など）はいじりません。自己紹介に肩書きや連絡先を足すときは、README 先頭の HTML コメントを消して、そこに1行足してください。公開プロフィールの company と location は断定に使っていません。

内容が同じならファイルは更新せず、workflow もコミットしません。

ローカルで、トピックを付ける前に完成形を見るとき:

```bash
python3 scripts/update_readme.py --overlay-assignments
```

`--overlay-assignments` は CI では使いません。本番は GitHub API が返す topics だけを見ます。

ルールの確認（ネットワーク不要）:

```bash
python3 scripts/test_update_readme.py
```

トークンは環境変数 `GITHUB_TOKEN`（Actions の組み込みトークン）を使います。無くても公開リポジトリの取得はできますが、レート制限が厳しくなります。組み込みトークンでは、他の非公開リポジトリは見えません。見えても一覧には出しません。

## workflow

- 毎日 09:17（Asia/Tokyo）ごろと、手動の `workflow_dispatch`
- 権限は `contents: write` のみ
- 使う Action は `actions/checkout` だけ。コミット SHA `3d3c42e5aac5ba805825da76410c181273ba90b1`（v7.0.1）に固定
- コミット作者は github-actions[bot]
- 先に `scripts/test_update_readme.py` を実行し、落ちたら README は更新しない

README のマーカーより上は、自由に書き換えてください。
