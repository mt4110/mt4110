# mt4110

まーきー（mt4110）です。ローカルで使えるセキュリティOSS（Veilシリーズ）を作っています。
下は公開リポジトリの一覧です。各リポジトリへのリンクと説明を載せています。
毎日 9:17（日本時間）ごろに自動で更新します。

<!-- 肩書き・所属・連絡先は、公開情報だけでは断定できないので書いていません。足すときはこのコメントを消して、上の自己紹介に1行足してください。 -->

<!-- REPOS:START -->
<!-- この範囲は scripts/update_readme.py が上書きします。手で編集しないでください。 -->

## veil シリーズ（セキュリティOSS）

シークレットの検出や共有、通信経路の観測など、ローカルで完結するセキュリティ向けのOSSです。

- [leak-fence](https://github.com/mt4110/leak-fence) — LeakFenceは、APIが他人のレコード・許可していない項目・取得枠を超えるデータを返す前に止める、Rust／Cloudflare Workers向けセキュリティOSSです。既存の認証・認可へ接続し、送信前に内容と永続取得枠を検査。
- [veil-arena](https://github.com/mt4110/veil-arena) — ホストOSを壊さず安全に検証できるeBPF/Rust用の使い捨てサンドボックス環境（特権単一ノード/kindによるk8s）を構築。veil-arenaのセットアップとテストを即座に開始します。
- [veil-db-guard](https://github.com/mt4110/veil-db-guard) — 既存RDSの認証・接続経路・防御設定の構築と検証を支援するローカルファーストOSS
- [veil-decoy](https://github.com/mt4110/veil-decoy) — 内部不正やソースコード流出を検知・監視するためのゼロトラスト防衛ツールです。本物と区別のつかない偽のAPIキー（ハニートークン）を生成し、コードベースや環境変数に紛れ込ませます。万が一コード泥棒がそのキーを利用した場合、即座にアクセス元の情報をトラッキングしてアラートを発出。
- [veil-drop](https://github.com/mt4110/veil-drop) — 短いテキスト（APIキー等、パスワード）を暗号化し、URLで共有するツールです。Rust CLIがAES-256-GCMで暗号化し、受信ページがブラウザー内のWeb Crypto APIで復号します。
- [veil-keeper](https://github.com/mt4110/veil-keeper) — Read-only systemd cgroup planning and isolated nftables verification in Rust
- [veil-rs](https://github.com/mt4110/veil-rs) — コード・ログ内のシークレットや個人情報（PII）を検出・マスキングするRust製CLI。不完全なスキャンをエラーとして扱い、署名付きローカルRulePackに対応。
- [veil-tell](https://github.com/mt4110/veil-tell) — CLIが外のどこに何を送ろうとしたかを一覧で見せ、知らない送り先だけ止めるラッパー。sudo不要・ローカル完結・テレメトリーなし。
- [veil-vault](https://github.com/mt4110/veil-vault) — 取得された瞬間にKVから物理削除される、完全ゼロトラストな「一回読み切り型」シークレットブローカー。中継サーバーに痕跡を一切残さない自己破壊APIです。
- [veil-warden](https://github.com/mt4110/veil-warden) — eBPFを活用したLinuxサーバー向けのゼロトラスト防衛・監視ツール。カーネルレベルで不審なプロセスや不正なネットワーク接続をリアルタイムに検知・遮断します。機密情報の外部送信に対する警告機能（Secret Warning）を備え、直感的なTUIでシステム状態を可視化。
- [zt-gateway](https://github.com/mt4110/zt-gateway) — Local file exchange gateway: scan, sanitize, sign, encrypt and verify. Personal portfolio / Apache-2.0.

## 開発ツール

CLI、テンプレート、CI や作業の補助など、開発の手元で使う道具です。

- [.github](https://github.com/mt4110/.github) — Shared community health files and defaults for mt4110 repositories
- [bitshave](https://github.com/mt4110/bitshave) — (Image Optim.appのCLI版)冗長データを削って画像を軽量化する決定論的ロスレスCLI
- [ci-self-runner](https://github.com/mt4110/ci-self-runner) — 個人運用向け self-hosted CI runner kit for macOS。colima+docker+GitHub Actions を最短導入し、owner guard付きで verify を安全・再現的に実行する運用基盤。外部fork PRは拒否して事故を防止。
- [crossport](https://github.com/mt4110/crossport) — 「8080番、誰が使ってる？」をもう推測しない。Git/Docker/K8sのコンテキスト付きでポートを可視化・管理できる次世代のlsof代替ツール。
- [google-apple-cloudflare-whitelist](https://github.com/mt4110/google-apple-cloudflare-whitelist) — Google / Apple / Cloudflare Public IP Range Fetcher and Network Allowlist Generator
- [image-drop-input](https://github.com/mt4110/image-drop-input) — Product-safe React image field for durable image state.
- [local-ai-review](https://github.com/mt4110/local-ai-review) — Local LLM-powered PR review with GitHub Actions. Zero API cost, fast diff-based analysis using Qwen3-Coder on self-hosted runners.
- [npm-package-template](https://github.com/mt4110/npm-package-template) — Single-package npm repository template with a calm, explicit release lane.
- [ops-whisper](https://github.com/mt4110/ops-whisper) — 原文の位置・一致件数・省略件数を残し、返す量を絞るローカル検索CLI。共有前の伏せ字は任意。秘密の検出は veil-rs の担当。外部送信なし。
- [readme-gif-crafter](https://github.com/mt4110/readme-gif-crafter) — README用にMP4を最適化されたGIFに変換するRust製ツール。サイズ自動調整機能付き。
- [rec-watch](https://github.com/mt4110/rec-watch) — RecWatch は、macOSの画面収録などで作成された動画ファイルを、自動で監視・変換するCLIツールです。フォルダに動画を保存するだけで、自動的に1080pのMP4（H.264）に変換し、完了を通知します。
- [review-firewall](https://github.com/mt4110/review-firewall) — Review the review. Protect the author.
- [specbackfill](https://github.com/mt4110/specbackfill) — git diff から、未回収の設計・テスト・移行・ドキュメント作業を逆算するルールベース CLI
- [webp-guard](https://github.com/mt4110/webp-guard) — Safe, resumable bulk JPEG/PNG-to-WebP conversion, verification, and delivery planning CLI. Go + cwebp; Nix dev environment.
- [xc-ops-bridge](https://github.com/mt4110/xc-ops-bridge) — 好きなエディタ（Antigravity/VSCode/Zed/JetBrains/nvim/Emacs）で Swift を編集し、ビルド/テストは Xcode（xcodebuild）に統一するための運用キット。

## 日本向けデータ変換

郵便番号や駅名など、日本の公開データを扱いやすくするための変換ツールです。

- [geo-line-ranker](https://github.com/mt4110/geo-line-ranker) — Deterministic geo-first and line-first recommendation engine for explainable school-event discovery.
- [postal_converter_ja](https://github.com/mt4110/postal_converter_ja) — 日本郵便局のデータを自動更新機能付き、Rustの非同期クローリングシステム。最加速で最新の郵便番号データの更新化がされます。
- [station_converter_ja](https://github.com/mt4110/station_converter_ja) — High-performance Japanese Station Converter & API.

## macOSアプリ

クラウド同期なしで使う、macOS向けのデスクトップアプリです。

- [md-viewer](https://github.com/mt4110/md-viewer) — Markdownの扱いに慣れていない人のためのローカルMarkdownビューアー。Rust + Tauri
- [prompt-recipe](https://github.com/mt4110/prompt-recipe) — クラウド同期なし、ローカルで完結するプロンプト管理ツール。Spotlight風UIで{{変数}}を展開し、キーボード操作ですばやくコピー。
- [still](https://github.com/mt4110/still) — AIとの開発で、使わなくなった生成物やコンテナが溜まっていませんか？ stillは、容量と中身を確認しながら整理できる無料のクリーナーです。

## 実験・研究

検証用の試作と、お遊びのCLIです。研究・実験用として置いています。

- [claude_ai_my_optim](https://github.com/mt4110/claude_ai_my_optim) — Claude AIを自分用にカスタマイズする土台
- [loto_cli](https://github.com/mt4110/loto_cli) — (お遊びコマンド)日本のロト6およびロト7のための、高機能乱数生成ツールです。単なるランダム生成だけでなく、様々なアルゴリズムを選択して「狙った」数字を生成することができます。
- [memory-lifeboat](https://github.com/mt4110/memory-lifeboat) — Local-first, encrypted rescue of AI product memories and browser context.

## アーカイブ

開発を止めたリポジトリと、反例として残しているものです。

<details>
<summary>アーカイブ（10件）</summary>

- [drop-squash](https://github.com/mt4110/drop-squash)
- [musubi-foundation](https://github.com/mt4110/musubi-foundation) — Source-of-truth docs for MUSUBI: constitution, glossary, whitepaper drafts, ADRs, and architecture diagrams.
- [patchgate](https://github.com/mt4110/patchgate) — PatchGateはPR差分の危険度を即時に数値化し、テスト不足・破壊的変更・依存更新リスクを同一ポリシーで判定するローカルファースト品質ゲート。CIと開発フックを同期し、レビュー優先度を毎回自動で揃え、導入直後から運用負荷と見逃しを同時に減らします。
- [pi-musubi-core](https://github.com/mt4110/pi-musubi-core) — A Web3 dating dApp on Pi Network. Utilizing escrow payments to eliminate bots and ensure authentic matchmaking.
- [sns-signal-studio](https://github.com/mt4110/sns-signal-studio) — Alpha: openCrawお試しを強調したSNSニッチ探索と1分動画生成スタジオ (OpenClaw + Claude + Sora)
- [software-satellite-lab](https://github.com/mt4110/software-satellite-lab) — ソフトウェア開発特化のサテライトシステム実験室
- [veil-blackhole](https://github.com/mt4110/veil-blackhole) — Archived research prototype for read-only macOS DNS observation and offline replay. No traffic blocking.
- [veil-env](https://github.com/mt4110/veil-env) — 平文の .env を撲滅するゼロトラストCLI。外部ボルトからメモリへ直接シークレットを引き込み、子プロセスへ安全に注入します。
- [veil-L7](https://github.com/mt4110/veil-L7) — Veilシリーズの研究記録（開発見送り・アーカイブ済み）。クラウドDBの個人データ保護案を調査し、既存のOSSで足りる部分と残る課題から見送りを判断した記録と、旧案の設計メモを残しています。
- [veil-mesh-consensus](https://github.com/mt4110/veil-mesh-consensus) — Autonomous mesh defense & attack extermination bridging Byzantine-resilient QUIC consensus (Ed25519 + Multi-Sig QuorumCertificate)…

</details>

## 未分類

グループ用トピックがまだ付いていない公開リポジトリです。topic を付けると、次回の更新で各グループへ移ります。

- [repotick](https://github.com/mt4110/repotick) — 開発フォルダの依存関係を手動で点検する macOS アプリ
<!-- REPOS:END -->
