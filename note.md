# command_line-rudesheim-python 作業復帰メモ

最終更新: 2026-07-16（実装反映済み）

## 目的（今回の設計変更の意図）
- `Parser` が `Option` / `Command` を直接知らない構成へ寄せる。
- ただし公開API層 (`rudesheim.command_line`) が parse内部層を継承しない。
- parse系の識別は `parse_identifier()` の戻り値（`parse.Option` / `parse.Command`）で行う。

## 現在の構成
- 公開層: `lib/rudesheim/command_line/__init__.py`
  - 公開クラス: `Selectable`, `Option`, `Command`, `SelectableCategory`, `Parser` ほか
  - `Selectable`/派生は **parse層を継承しない**
  - `parse_identifier()` で `parse.*` の識別子クラスを返す
- parse内部層: `lib/rudesheim/command_line/parse/__init__.py`
  - Parser専用の選択処理実装: `Selectable`, `Option`, `Command`
  - 補助: `ShortKeyDecorator`, `LongKeyDecorator`, `key_decorator_for`
  - 例外: `BasicException`, `UndefinedOptionSpecified`, `OptionIsInConflict`
  - `parse.Parser` は削除済み（循環回避のため）

## 重要な実装ポイント
- `command_line.Parser` 実装は公開層に存在。
- `Parser.parse()` は以下で動作:
  - `selectables` を動的生成（固定で Option/Command を持たない）
  - `key_spec()` で `getopt` spec を収集
  - `reduce` で `parse_order()` 順に `parse_with(...)` を適用
- `Option.key_spec()` は現在この仕様:
  - short/long どちらか片方の配列に **1要素** を入れて返す
  - 返り値形式: `( short_specs, long_specs )`

## 互換性破壊として実施済み
- `OptionCategory` を削除
- `options_defines` を削除
- `SelectableCategory` + `selectables_defines` に統一
- `README.md`, `tests/test_command_line.py`, `examples/*.py`, `lib/...egg-info/PKG-INFO` も更新済み

## 直近コミット
- repo: `command_line-rudesheim-python`
- commit: `5f2ecb2`
- message: `refactor: split parse internals and decouple command_line`

## テスト状態
- コマンド: `python3 -m unittest discover -s tests -p "test_*.py"`
- 結果: 27 tests, all OK

## 次に検討していた内容
- `docker --context prod compose up` のような「親グローバルoption + subcommandローカルoption」対応
- 提案方針（未実装）:
  - Optionにスコープ概念 (`global` / `local`) を導入
  - 2フェーズ解析（親global先読み -> command確定 -> 子local解析）

## 補足
- `note/` ディレクトリは変更していない。
- このメモは復帰用に `command_line-rudesheim-python/note.md` のみ更新。

## 2026-03-08 時点の合意（未実装）

### 要件の再定義
- 目的は「Docker互換ライブラリ化」ではない。
- 目的は「Dockerのような引数順を要求されても処理できる汎用性」の実現。
- 具体的には、以下の並びを文脈付きで扱えること:
  - global option
  - command
  - command文脈のlocal option
  - subcommand と残余引数

### 使う側の負担を減らす方針
- 利用者に「subcommandの中で再度 `parse()` を書く」ことを要求しない。
- `Command.parser_define()` は継続利用し、宣言だけで再帰解析はライブラリ内部で自動実行する。
- 利用者は parse手続きではなく、決定結果の取得だけを意識すればよい形にする。

### APIイメージ（方向性）
- `parser_define()` は「その command 配下の文法宣言」を返す最小責務にする。
- 解析結果は `result/context` から取得可能にする:
  - command path（どの command / subcommand が選ばれたか）
  - categoryごとの selected option
  - command単位の残余引数
- `this`（`cls`）や引数から決定情報を取り出せる導線を提供する。

### 現状メモ
- 実装変更はまだ行っていない。
- 一時的に加えた実装変更は取り消し済み。

## 2026-03-10 会話ログ要約（設計検討）

### Option / Command の設計意図（再確認）
- `Option` はカテゴリ内の選択を表す。
  - 例: `-v`, `--depth=3`
  - `SelectableCategory` ごとに 1 つ選択される前提
  - 重複指定は `OptionIsInConflict`
  - 振る舞いは Option 側へ寄せ、呼び出し側の `if/elif` を減らす
- `Command` は位置引数の文脈切り替えを表す。
  - 例: `build`, `install`
  - 選択後に `parser_define()` で下位文法へ委譲
  - 再帰的に subcommand を解析する入口

### 新しく出た方向性
- 複雑な subcommand 対応に向け、利用者の起点を `Parser` から `Command` に寄せる案を検討開始。
- 想定フロー:
  - 利用者は最初に root `Command` 派生へ実行時引数を渡す
  - `Command` が自身の `Parser` を使って Category へ変換
  - Category から次の `Command` を選択
  - `Command -> Parser -> Command -> Parser -> ...` を再帰
- 目的:
  - 利用者に再帰 `parse()` 記述を強いない
  - `RootCommand.run(argv)` のような単一起点に寄せる

### この方向での注意点（深掘り）
- 責務肥大
  - 危険: `Command` が文法定義・解析制御・実行を抱えて巨大化
  - 対策: 解析ループは runtime 側へ分離し、`Command` は宣言と実行責務に限定
- 循環依存の再発
  - 危険: parse内部層と公開層の密結合が戻る
  - 対策: 継承依存ではなく識別子/プロトコル中心を維持
- エラー責務の曖昧化
  - 危険: 未定義 option の判定階層がぶれる
  - 対策: 「現在 command 文脈で未定義なら即エラー」など規則固定
- global/local option の衝突
  - 危険: 同名 option の解釈が順序依存になる
  - 対策: 優先順位（例: local > global）と同名許可ポリシーを先に仕様化
- 解析結果モデル不足
  - 危険: 深い階層で文脈情報（どの command 配下か）が追跡しづらくなる
  - 対策: 全体一意な `Category` / `Selectable` 命名を前提にし、必要最小限で path 情報を補助保持
- 残余引数の境界不明瞭化
  - 危険: どの階層が何を消費したか追跡不能
  - 対策: トークン消費規約と `--` 終端規則を固定
- テストの組み合わせ爆発
  - 危険: subcommand 拡張で既存テストが壊れやすい
  - 対策: 契約テスト（順序/衝突/継承/未知オプション）を先に固定
- 移行リスク
  - 危険: `Parser` 起点利用者の互換性破壊
  - 対策: `Command` 起点 API を追加し、段階移行で `Parser` は当面併存

### 2026-03-10 追加合意（解消済み）
- `Category` と `Selectable` の名前は全体で一意とする。
  - 同名を使いたい場合は package で分離する（例: `add.XCategory`, `remove.XCategory`）。
- `add --help` と `remove --help` は同一 `Category` で共有しない。
  - 基本処理は共通化しても、文脈が異なるため別 `Option` オブジェクトとして扱う。

### 現時点の未解消課題
- `Command` 起点へ寄せる方向は有効。
- ただし実装前に最低限、以下を仕様化する必要がある。
  - スコープ規則（global/local の優先と継承）
  - エラー発生規則（どの文脈で何を未定義とするか）

## 2026-04-04 会話ログ要約（Command interface 再整理）

### Selectable と Command の責務分離
- `description()` のような表示系は `Command` 固有ではない。
- 表示系を持たせるなら `Option` / `Command` の共通上位である `Selectable` が持つべき。
- したがって `Command` 固有 interface の議論に `description()` や `command_name()` を含めない。

### Command の入れ子構造
- `Command` は「子 `Command` 候補を配下文法に含められる selectable」として捉える。
- 依存関係は「親 `Command` が子 `Command` を直接実行する」ではなく、
  `parser_define()` が返す文法定義の中に次の `Command` 候補が入る構造として考える。
- 例: `git -> worktree -> add`
  - `GitCommand`
    - top-level command category を持つ
    - その候補に `WorktreeCommand` が入る
  - `WorktreeCommand`
    - subcommand category を持つ
    - その候補に `AddCommand` が入る
  - `AddCommand`
    - local option / argument を持つ

### Command 派生に必要な interface 候補
- `parser_define()`
  - その command 配下の文法宣言を返す
- `run_with( this, categories, arguments )`
  - その command が担当する subcommand として振る舞う method
  - `categories` は root から当該 command に至るまでに確定した全 `Category` を詰めた連想配列
  - `arguments` はその command 文脈で最終的に残った引数

### run_with を確定する前に必要な規則
- `run_with( this, categories, arguments )` の形自体は有力。
- ただし正式確定の前に、
  「次の subcommand に進むか」「現在 command で終了するか」の規則を先に決める必要がある。
- `Command` が中間ノードにも終端ノードにもなれるなら、
  子 subcommand が確定した場合は子へ進み、
  確定しなかった場合は現在 command の `run_with(...)` を呼ぶ、という規則が自然。

### 有名 CLI に照らした前提
- `git remote`, `git worktree`, `docker image`, `docker container`, `kubectl config` などは、
  中間 command でありつつ、単独入力時の help / usage / 既定動作の対象にもなる。
- そのため、「子 command を持つ command は実行しない」と決め打ちしない方が現実の CLI に合う。
- `Command` は「枝にもなれるし終端にもなれる」と扱う前提が妥当。

### subcommand と通常引数の区別
- `subcommand` と directory 名などの通常引数は、文字列だけでは区別できない。
- 区別は「現在の command 文脈で、次の位置に何が許されるか」という文法で決まる。
- まず現在 command 文脈の subcommand 候補と照合し、
  一致しなければその位置で許される通常引数として扱う。
- どちらにも該当しなければエラー。
- 同じ文字列でも文脈が変われば意味が変わる。
  - 例: `git worktree add`
    - `worktree` 直下では `add` は subcommand
  - 例: `git worktree add add`
    - 2個目の `add` は `add` command 文脈では path などの通常引数になりうる

### current implementation に対する読み替え
- 現在の examples / README では、`run_with` を持つのは主に `OptionForRun` であり `Command` ではない。
- 既存 `Command` は `parser_define()` を持つ枝として使われている。
- 実行タイミングの本質は「default selectable だから実行」ではない。
- 正確には「最終的に選ばれた executable selectable に対して `run_with(...)` を呼ぶ」。
- examples ではそれが default selectable なので、見かけ上「default のときに実行」になっている。

### 今後さらに仕様化すべき問い
- `Command` が子 subcommand を持つ場合でも、自身の `run_with(...)` を持てるものとするか
- 子 subcommand が確定したときの優先規則をどうするか
- subcommand category 不成立時に、現在 command の `run_with(...)` へフォールバックするか

## 2026-06-07 作業状況

### リポジトリ状態
- ブランチ: `work`
- HEAD: `5f2ecb2 refactor: split parse internals and decouple command_line`
- `origin/main` / `origin/develop` は `ab957a3 refactor: rename ItemForhelp to ItemForHelp` のため、`work` はローカルで 1 commit 先行している。
- 未追跡:
  - `note.md`
  - `dist/`
  - 各種 `__pycache__/`
- 2026-06-07 の検証で `lib/command_line_rudesheim_python.egg-info/PKG-INFO` と `SOURCES.txt` が再生成され、tracked 差分が出ている。

### 実装済み内容
- 公開 API 層は `lib/rudesheim/command_line/__init__.py` に残し、parse 内部層を `lib/rudesheim/command_line/parse/__init__.py` に分離済み。
- 公開 `Selectable` / `Option` / `Command` は parse 内部 class を継承せず、`parse_identifier()` で内部識別子を返す構成になっている。
- `Parser.parse()` は category の `selectables_defines()` から lookup と `getopt` spec を組み立て、parse 識別子の `parse_order()` 順に処理する。
- `Command.parser_define()` により、`build --release` や `install --depth 3` のような 1 階層 subcommand 解析はテスト済み。

### 確認結果
- `python3 -m unittest discover -s tests -p 'test_*.py'`
  - 27 tests OK
- `env PYTHONPATH=lib python3 examples/smoke_install_check.py`
  - `mode=apply args=['target']`
- `.venv/bin/python -m build`
  - sdist / wheel の生成自体は成功

### 判明している問題
- 生成された wheel に `rudesheim/command_line/parse/__init__.py` が入っていない。
- 一時 venv に wheel を install して import すると、以下で失敗する。
  - `ModuleNotFoundError: No module named 'rudesheim.command_line.parse'`
- 原因候補:
  - `pyproject.toml` の `[tool.setuptools.packages.find] include` が `["rudesheim", "rudesheim.command_line"]` だけで、`rudesheim.command_line.parse` を含んでいない。

### 次アクション
- `pyproject.toml` の package include に `rudesheim.command_line.parse` を含める、または `rudesheim.*` へ寄せる。
- 修正後に以下を再確認する。
  - `python3 -m unittest discover -s tests -p 'test_*.py'`
  - `.venv/bin/python -m build`
  - 生成 wheel を一時 venv に install して `import rudesheim.command_line` が成功すること

## 何をしようとしていたか

### 直近でやろうとしていたこと
- `Parser` が公開 API の `Option` / `Command` 実装を直接知りすぎないように、parse 内部処理を分離しようとしていた。
- ただし公開 API が内部 parse class を継承する形にはせず、`parse_identifier()` で内部識別子を返すプロトコルに寄せようとしていた。
- その分離を入れたうえで、既存の「カテゴリごとに選択された object が振る舞いを持つ」設計を維持しようとしていた。
- `OptionCategory` / `options_defines` ではなく、`SelectableCategory` / `selectables_defines` に統一し、Option と Command を同じ selectable として扱える土台を作ろうとしていた。

### 次に進めようとしていた設計
- Docker や Git のような、階層 command を持つ CLI を自然に扱えるようにしたかった。
- 具体的には `docker --context prod compose up` や `git worktree add ...` のように、以下が混ざる入力を文脈付きで扱う方向だった。
  - root / global option
  - command
  - command local option
  - subcommand
  - command 文脈ごとの残余引数
- 利用者に subcommand の中で手動で `parse()` を再実行させず、`Command.parser_define()` に文法を宣言すれば、ライブラリ内部が再帰解析する形を目指していた。
- 将来的には `RootCommand.run(argv)` のような単一起点へ寄せ、利用者は解析手続きではなく最終的に選ばれた object の `run_with(...)` を扱えばよい形にしたかった。

### 実装前に決めようとしていた規則
- global option と local option の優先順位、継承範囲、同名 option を許すかどうか。
- 未定義 option をどの command 文脈でエラーにするか。
- command が子 subcommand を持つ場合でも、自身の `run_with(...)` を実行可能にするか。
- 子 subcommand が見つかった場合は子へ進み、見つからなかった場合は現在 command を終端として扱うか。
- subcommand 候補と通常引数が同じ文字列だった場合に、現在の文法でどう判定するか。

### いま最初に片付けるべきこと
- 現在は package build 後の wheel に `rudesheim.command_line.parse` が含まれず、install 後 import が壊れる。
- そのため、次の実装検討に入る前に `pyproject.toml` の package include を修正して、分離済み parse 層が配布物に入る状態へ戻す必要がある。

## 2026-07-07 会話ログ要約（run_with 駆動と ParseState 設計）

未実装・設計のみ。優先順位は変わらず、`pyproject.toml` の package include 修正が最優先のまま。

### tie() の keys 仕様（実装読解で確認）
- `Selectable.tie(keys, description)` の `keys` は `(short, long)` のペアではなく、個々の key 文字列を並べた collection。各 key は `len(key)` で自身の長さから短縮形/長形式を自己判定する（`key_decorator_for`）。
- `None` は key として許可されない。`Option` 側では `key_spec` 内の `len(key)` で `TypeError` になる。`Command` 側はクラッシュしないが、どの入力とも一致しない無意味な dead entry になるだけで、意図された使い方ではない。

### categories/arguments の再帰は実装済みと確認
- `Command.parse_with` が `matched.parser_define().parse(...)` で子 scope を再帰的に解決し、`categories_for_update.update(...)` で親にマージする機構は既存実装済みで正しく動作する。
- 非 GNU 版 `getopt`（最初の非オプション引数でオプション解析を打ち切る）により、「global は先頭、local は subcommand 直後」という並び順制約が自動的に強制されている。global/local の優先順位問題の一部はこれで実質解消。

### run_with へ context 引数を追加
- `run_with(this, categories, arguments)` に、木全体で共有する横断的情報（I/O、dry-run 設定、exit code 集約など）を運ぶ `context` 引数を追加する。
- 位置は `this` の直後: `run_with(this, context, categories, arguments=())`。
  - 理由: Python はデフォルト引数を末尾にしか置けない。`arguments` を省略可能にするには最後に置く必要があり、逆算して `context` は `this` の直後になる。

### run_with は末端（terminal）でのみ、1 回だけ呼ぶ
- 枝 command は子への委譲を自分の `run_with` 内で明示的に行わない（`this.run(...)` のような自己駆動の継続呼び出しは持たせない）。委譲の可否は再帰（parse 機構）側が既に知っている情報であり、二重管理・書き忘れバグを避けるため。
- 枝 command が `run_with` を持つかどうかは任意の設計選択（例: `ComposeSubcommand.default()` を別クラス `ComposeUsage` にするか `ComposeCommand` 自身にするか）であり、フレームワーク側の構造的要請ではない。この判断で 2026-04-04 の未解消課題「子 subcommand を持つ Command が自身の run_with を持てるか」は解消。
- `run_with` が呼ばれるのは「command path の再帰が止まった時点」＝以下いずれか:
  - (a) 残余引数が尽きた
  - (b) 次 token が subcommand 候補と不一致
  - (c) `parser_define()` がそもそも次の Command 系 category を持たない

### run 関数は作らず、Parser.parse を改良する方針
- `Command` に `.run(argv)` のような駆動用 method は追加しない。制御は従来通り `Parser` に集約し、`Command` は `parser_define()` と `run_with(...)` だけを持つ軽量なままにする。
- `Parser.parse()` 自体を「解決 + run_with 起動」まで行うように改良する。ただし `parse()` は `Command.parse_with` 内から再帰的に自分自身を呼ぶ構造のため、そのまま run_with 起動を埋め込むと再帰の各階層で `run_with` が重複して呼ばれてしまう。
- 対策: `parse()` の中身（既存の getopt 構築 + reduce）を `resolve()` という「解決のみ行う」内部 method に切り出す。`Command.parse_with` の再帰は `.parser_define().resolve(...)` を呼ぶ（run は呼ばない）。公開 `parse(this, context, arguments)` は `resolve()` を呼んだ後、最後に 1 回だけ確定した terminal の `run_with(...)` を呼ぶ。
- `resolve` に `_` prefix を付けない（このコードベースは `parse_with` 等の内部専用 method にも `_` を付けないスタイルのため、既存スタイルに合わせて公開名 `resolve` のまま）。

### 有無の表現に None を使わない
- 「終端（terminal）が確定しているか」を `None` で表さず、0〜1 要素の list（`[]` / `[object]`）で表現する。フィールド名は複数形 `terminals`。
- 選択ロジックは `is None` を使わず、`next_terminals + [matched]` のような list 連結で「あれば先頭を優先、なければ fallback」を表現する。取り出しは可読性を優先し `[ (next_terminals + [ matched ])[0] ]` の形（`[0:1]` スライスではなく index + list 包みを採用）。

### tuple で渡していた引数を ParseState に集約
- `parse_with` の引数（旧: `this, categories_templates, selectable, categories, categories_for_update, context, arguments, terminals` の 8 個。うち `categories` はどの実装からも参照されない死に引数だった）を `ParseState` という 1 つの object に集約。
- `ParseState` は `context` / `categories` / `arguments` / `terminals` を持つ。
- `ParseState` に `@classmethod following(this, parse_state, arguments, terminals)` を追加。`context`/`categories` を引き継ぎつつ `arguments`/`terminals` だけ差し替えた新しい `ParseState` を作れる。
- `parse_with` 側からは `state.following(state, ...)` のように **instance 経由**で呼ぶ。`ParseState.following(...)` という名指し呼び出しにすると、`parse/__init__.py` が `command_line/__init__.py` を逆 import することになり循環 import になるため（既存コードが `parser_define()` を名前を書かず object 経由で呼んでいるのと同じ回避策）。

### 検討したが採用しなかった案
- `ParseState.first_argument()`（`arguments[0]` を取り出す accessor）→ 不採用。単純に `state.arguments[0]` のまま。
- `ParseState.define_for(selectable)`（`selectable[state.arguments[0]]` を関数化）→ 不採用。`Command.parse_with` 内でローカル変数 `define = selectable[state.arguments[0]]` に留める。

### 未反映（実装はまだ行っていない）
- 上記すべて設計のみで、`lib/rudesheim/command_line/__init__.py` / `lib/rudesheim/command_line/parse/__init__.py` の実ファイルはまだ変更していない。
- この設計に伴い、以下の派生変更も必要だが未着手:
  - `Parser.parse_from_default(this)` → `parse_from_default(this, context)`（`parse` が `context` を要求するようになった影響）
  - `OptionForRun.run_with(this, categories, arguments)` / `OptionForPrint.run_with(...)` / `BasicHelp.run_with(...)` を新 signature `run_with(this, context, categories, arguments=())` に合わせる変更

## 2026-07-16 会話ログ要約（命名整理と ParseState 実装の小規模リファクタ）

未実装・設計のみ。2026-07-07 分の続き。優先順位は変わらず `pyproject.toml` の package include 修正が最優先。

### 分岐の書き方
- 分岐に `or` / `and` を使わない。使いたくなったら先に相談する。
  - 理由: `if A or B: return X` のように 1 箇所にまとめると、breakpoint を `return` に貼っても A/B どちらが真だったか区別できない。`if A: return X` / `if B: return X` と分ければ、どちらの `return` で止まったかで一発診断できる。
  - 適用例: `Command.parse_with` の入口ガードを `if 0 == len(state.arguments) or state.arguments[0] not in selectable: return state` から、2 つの独立した `if ... return state` に分割。

### 変数抽出の基準
- 複数回参照する式だけを変数に切り出す。1 回しか参照しない変数は作らない（例: `register_result` は `zip(...)` の引数として 1 回しか使っていなかったため、呼び出し式をそのまま `zip` に渡す形にインライン化した）。
- `state.arguments[0]` は `key` という変数名に切り出す（`Command.parse_with` で 2 回参照するため）。ただし `if 0 == len(state.arguments): return state` より後、`key` を使う箇所より前に置く（空リストで `arguments[0]` を触ると `IndexError` になるため）。
- 変数名は「出自（添字0番目など）」ではなく「その文脈での役割」で付ける。`first_argument` ではなく、`selectable` 辞書を引く key であることを表す `key` を採用。
- `resolve()` 内の `selectable.parse_identifier()` は同一ループ内で 3 回呼ばれていたため `identifier` に切り出した。

### 定型パターンの言語機能への置き換え
- `keys_specs[0].extend(register_result[0]); keys_specs[1].extend(register_result[1])` は `zip(keys_specs, register_result)` でペアにして `for spec, result in zip(...): spec.extend(result)` にまとめた（添字 `0`/`1` の書き分けが消える）。
- `if identifier not in selectables: selectables[identifier] = {}` は `dict.setdefault` で `selectables.setdefault(identifier, {})[...] = ...` の 1 行にまとめた。
- `state.categories.update(...)` は Python 組み込み `dict.update()` のことで、独自実装は不要と確認済み。

### selectable / selectables の混同を解消
- `resolve()` 内では `selectable`（単数、1 つの Option/Command クラス）と `selectables`（複数、`{identifier: {key: (category, selectable)}}` の辞書）を正しく区別している。
- しかし `parse_with` の 3 番目の引数名が `selectable`（単数）になっていたにもかかわらず、実体は `{key: (category, selectable)}` という辞書だった（`resolve()` 側で `selectables[each.parse_identifier()]` という辞書を渡していた）。これを `selectables_by_key` に改名して区別した。

### define と selectable の混同を解消（実は元のソース由来の問題）
- `resolve()` 内の `define`（`for define in category.selectables_defines(): ...`）は `DefineOfSelectable` のインスタンス（`.selectable()` / `.keys()` / `.description()` を持つ）。
- 一方 `parse_with` 内の `define`（`define = selectable[key]` や `define = selectables_by_key[key]`）は中身が単なる `(category, selectable)` タプルで、`DefineOfSelectable` とは無関係の別物だった。これは元の（未変更の）ソースの時点で既にあった命名の重複。
- `selectables_by_key` への改名で `selectable` という名前が `parse_with` のスコープ内で空いたため、`define` を廃止してタプル分解 `category, selectable = selectables_by_key[key]` に変更。あわせて `matched` / `selected` という別名も廃止し、「選ばれた Option/Command クラス」は一貫して `selectable` と呼ぶように統一した。

### 未反映（実装はまだ行っていない）
- 上記もすべて設計のみで、`lib/rudesheim/command_line/__init__.py` / `lib/rudesheim/command_line/parse/__init__.py` の実ファイルはまだ変更していない。
- 2026-07-07 分に記載した派生変更（`parse_from_default` への `context` 追加、`OptionForRun` 系 `run_with` の新 signature 対応）も未着手のまま。

## 2026-07-16（続き） 実装反映・破壊的変更として確定

### 互換性の方針決定
- 既存の「Option だけで完結する `parse()`」（`Command` を一切使わない既存テスト全体・README の Quick Start 等）との非互換を検討した結果、**破壊的変更として進める**ことで確定。
- 影響範囲: `Parser.parse()` は常に `resolve()` の結果から terminal を 1 つ確定させ、その `run_with(...)` を呼んで返り値をそのまま返す形に変更。Command 系 category を持たない（`terminals` が最後まで空の）構成で `.parse()` を呼ぶと `IndexError` になる。この場合は `.resolve(context, arguments)` を直接使い、`state.categories` / `state.arguments` を自分でハンドリングする（`examples/run.py`, `examples/smoke_install_check.py` はこの形に更新済み）。

### 実装時に見つけた 2 つの潜在バグ（設計段階では気づかなかった）
1. **`state.arguments` が生の getopt tuple のまま Command 側に渡ることがある**
   - 原因: `Option.parse_with` が「getopt の `(opts, remaining)` タプルを `remaining` だけに剥がす」役目を兼ねていたため、あるレベルの category が全て `Command` 型（`Option` 型 selectable が 1 つも無い）だと `Option.parse_with` 自体が実行されず、剥がされないまま `Command.parse_with` に生タプルが渡っていた。
   - 症状: `key = state.arguments[0]` が文字列ではなく getopt の opts list になり、`TypeError: unhashable type: 'list'`。
   - **元のソース（未変更時点）にも同じ構造の潜在バグがあったが、既存テストのどの fixture も「Command 型 selectable だけの category」を作っていなかったため踏まれていなかった。**
   - 対策: `ParseState` に `opts` フィールドを新設し、`arguments`（残余位置引数）とは独立に持たせた。`resolve()` は最初から `arguments` を getopt の `remaining` だけに設定し、`opts` は `Option.parse_with` だけが読む。
2. **category の既定値埋めが `Option.parse_with` にバンドルされていたため、Option 型 selectable が無い category では `default()` が一度も呼ばれない**
   - 症状: `ComposeSubcommand` のような「Command 型 selectable だけの category」で、該当 token が渡されなかった場合、`categories` にそのカテゴリのキー自体が存在しないままになる。
   - **これも元のソースの構造に起因する潜在バグ。**
   - 対策: 既定値埋めループ（`for category in categories_templates: ...category.default()`）を `Option.parse_with` から `Parser.resolve()` 側（reduce の後、`Option` の有無に関係なく必ず 1 回実行）に移動。

### 実装したファイル
- `lib/rudesheim/command_line/__init__.py`: `ParseState`（`context`/`categories`/`opts`/`arguments`/`terminals`、`following` classmethod）、`Parser.resolve` / `Parser.parse` / `Parser.parse_from_default`、`OptionForRun` / `OptionForPrint` / `BasicHelp` の `run_with` signature 更新。
- `lib/rudesheim/command_line/parse/__init__.py`: `Selectable` / `Option` / `Command` の `parse_with` を `ParseState` ベースに更新（`selectables_by_key` への改名、`define` 廃止しタプル分解、`or`/`and` 不使用、`state.following(...)` による instance 経由呼び出しで循環 import 回避）。

### テスト
- `tests/test_command_line.py`:
  - `ParserTests` / `CommandParserTests` は `.parse()` ではなく `.resolve(None, ...)` を呼び、`result[0]`/`result[1]` ではなく `result.categories`/`result.arguments` を見る形に更新（Option/Command だけで `run_with` を持たない既存 fixture が引き続き使えるように）。
  - 新設 `TerminalDispatchTests`: `Context`(global) → `Compose`(枝, 自身に `run_with` あり) → `Up`(葉, local `DetachCategory` あり) という 2 階層構成で、
    - 深い葉まで到達して `run_with` が 1 回だけ呼ばれ `context`/`categories`/`arguments` が正しく渡ること
    - global category（`ContextCategory`）が再帰後も生き残ること
    - 子 subcommand 未指定時に「一番近い、既にマッチ済みの祖先」（ここでは `Compose`）の `run_with` にフォールバックし、その際 `ComposeSubcommand.default()`（`Up`）は `categories` には入るが実行はされないこと
    を検証。
  - 全 30 tests OK（`python3 -m unittest discover -s tests -p 'test_*.py'` / `test/run.py` 双方で確認）。
- `examples/run.py`, `examples/smoke_install_check.py`: `run_with` に `context` 追加、`.parse()`/`.parse_from_default()` ではなく `.resolve(None, ...)` + 手動 `run_with` 呼び出しに変更。両方とも実行確認済み。

### 未着手・要フォローアップ
- `README.md` は旧 API（`run_with(this, categories, arguments)` / `parse()` がタプルを返す前提）のままで、今回の変更と整合しなくなっている。更新はまだ行っていない。
- 2026-06-07 時点の最優先課題（wheel に `rudesheim.command_line.parse` が入らない `pyproject.toml` の package include 修正）は今回も未着手のまま。
- Root レベルで `RootSubcommand` にすら何もマッチしない（`terminals` が最後まで空）場合、`.parse()` は `IndexError` になる。中間 command と違い root には「フォールバック先の既にマッチ済みの祖先」が存在しないため。今回はこのケースをテストで踏んでいない（root 用の既定 terminal をどう用意するかは未設計）。

## 2026-07-16（続き2） run_with 既定動作を Selectable に統一

### 経緯
- 実装後にコミット（`9698512`）を確認したところ、私が実装した時点には無かった `Command.run_with` の既定実装（`raise RunWithNotImplemented()`）が追加されていた（ユーザー側またはlinterによる追記と推定）。
- これと `OptionForRun` の既定 `run_with`（`pass`、無言no-op）が別々に定義されており、「`Option` 系は無言no-op、`Command` 系は例外」という非対称な既定動作になっていた。
- さらに、`SelectableCategory.default()` の意味が `Option` 系（default の戻り値がそのまま実行される）と `Command` 系（default はcategoriesに記録されるだけで実行されない。子subcommand未指定時は直近の確定済み祖先へフォールバック。root には祖先が無いため `IndexError`）とで食い違っていることも判明（**この不整合自体は未解消。design論点として残っている**）。

### 決定・実装した内容
1. `Selectable` に既定 `run_with(this, context, categories, arguments=())` を追加し、`RunWithNotImplemented` を raise するようにした。
2. `Command` 独自の `run_with`（`Selectable` と同じ内容だった）を削除し、`Selectable` から継承する形に統一。
3. `OptionForRun` を削除。
   - 理由: 継承していた `OptionForPrint` と両 examples の `Main` はどちらも `run_with` を自前で上書きしており、`OptionForRun` の `pass`（無言no-op）を実際には一度も使っていなかった。`isinstance` 等の型チェック用途も無し（grepで確認済み）。
4. `OptionForPrint` の親を `OptionForRun` → `Option` に変更（中身は無変更）。
5. `BasicHelp` / `BasicVersion` は自前で `run_with` を持つ・継承するだけなので無変更。
6. `examples/run.py` / `examples/smoke_install_check.py`: `class Main( cl.OptionForRun )` → `class Main( cl.Option )` に変更（`run_with` の中身はそのまま、`context`/`categories`/`arguments` を使うので直接上書き）。

### 検討したが採用しなかった案
- `Selectable.run_with` の中身を `raise` 直書きではなく、引数を取らない `run()` を呼ぶだけにし、`run()` 側に `raise RunWithNotImplemented()` を置く案（`OptionForPrint`/`BasicHelp` は `context`/`categories`/`arguments` を一切使っていないため、`run()` だけ実装すれば済む形にする意図）。
  - 一度提案・設計まで詰めたが、最終的に不採用。`Command` 派生や `Main` は結局 `context`/`categories`/`arguments` を使うため `run_with` を直接上書きすることになり、`run()` の恩恵を受けるのは `OptionForPrint` 系だけで限定的。間接層が増える割に利益が薄いと判断し、`run_with` 直書きのシンプルな形に戻した。

### 確認結果
- 全 30 tests OK（`python3 -m unittest discover -s tests -p 'test_*.py'`）。
- `examples/run.py`（引数無し／`-v`）、`examples/smoke_install_check.py` とも実行確認済み。
- `OptionForRun` への参照は `lib/`/`tests/`/`examples/` から完全に消えたことを grep で確認済み（`README.md` のみ旧記載が残存、既知のフォローアップ項目）。

### 未解消のまま残っている論点
- `SelectableCategory.default()` の意味が `Option` 系と `Command` 系で異なる非対称性（上記「経緯」参照）は今回スコープ外。統一案（`Command.parse_with` の未マッチ分岐も `default()` を選んで明示マッチと同じ経路で再帰させる）は提示済みだが未実装・未合意。
- Root レベルで何もマッチしない場合の `IndexError` も、この非対称性解消と合わせて直る見込みだが未着手。

## 2026-07-16（続き3） run_with の引数を1個（RunParameters）に集約

### 決定内容
- `run_with(this, context, categories, arguments=())` という3引数を、`run_with(this, run_parameters)` という1引数に集約。
- 新設 `RunParameters` クラス（`user_data` / `categories` / `arguments` を保持）が実体。`ParseState` はこれを `run_parameters` フィールドとして内包し、それとは別に解析専用の内部情報（`opts`, `terminals`）を持つ、という役割分離にした。
- `context` という名前は分かりにくいという指摘を受け、`user_data` に改名（呼び出し側=ユーザーが持ち込む不透明なデータ、という意味を明確化）。`RunState` という案も出たが「複数の値をまとめた入れ物」という実体に合わせて `RunParameters`（複数形）に確定。
- `Parser.resolve` / `Parser.parse` / `Parser.parse_from_default` の引数名も `context` → `user_data` に統一。

### 検討したが不採用だった名前
- `context`の代案として `caller_state` / `user_data` を提示 → `user_data` を採用。
- `RunState`（クラス名） → 「状態」より「実行のためのパラメータ一式」に合わせて `RunParameters` を採用。

### 実装したファイル
- `lib/rudesheim/command_line/__init__.py`: `RunParameters` 新設、`ParseState` を `run_parameters`/`opts`/`terminals` の3フィールドに再構成、`Selectable.run_with` / `OptionForPrint.run_with` / `BasicHelp.run_with` を単一引数化、`Parser.resolve`/`parse`/`parse_from_default` の引数名を `user_data` に統一。
- `lib/rudesheim/command_line/parse/__init__.py`: `Option.parse_with` / `Command.parse_with` 内の `state.categories`/`state.arguments`/`state.context` を `state.run_parameters.categories`/`state.run_parameters.arguments`/`state.run_parameters.user_data` に置き換え。
- `tests/test_command_line.py`: `ParserTests`/`CommandParserTests`/`TerminalDispatchTests` を新フィールド構成・新 `run_with` signature に追従。
- `examples/run.py`, `examples/smoke_install_check.py`: `run_with` 実装と呼び出し側を新 signature に追従。

### 確認結果
- 全 30 tests OK。
- `examples/run.py`（引数無し／`-v`／`-h`）、`examples/smoke_install_check.py` とも実行確認済み（`-h` で `BasicHelp.run_with`＝instance method 版の経路も確認）。
- `state.categories`/`state.arguments`/`state.context`/`RunState` という旧参照が `lib/`/`tests/`/`examples/` に残っていないことを grep で確認済み。

### 未着手・要フォローアップ（変わらず）
- `README.md` は依然として旧 API 記載のまま。
- `pyproject.toml` の package include 修正（wheel に parse 層が入らない件）。
- `SelectableCategory.default()` の `Option`/`Command` 間の非対称性、および root での `IndexError`。

## 2026-07-16（続き4） `Parser.resolve`/`parse`/`parse_from_default` の `user_data` を末尾・省略可能に

### 決定内容
- `resolve(this, user_data, arguments)` / `parse(this, user_data, arguments)` の引数順を `resolve(this, arguments, user_data=None)` / `parse(this, arguments, user_data=None)` に変更。`user_data` を省略できるようにするため、Python の仕様上デフォルト引数は末尾にしか置けない、という理由で末尾に移動。
- `parse_from_default(this, user_data=None)` も同様に既定値を追加。
- `run_with(this, run_parameters)` 側は変更なし（`user_data` は `RunParameters.user_data` フィールドとして既に1引数に集約済みのため対象外）。

### 実装したファイル
- `lib/rudesheim/command_line/__init__.py`: `Parser.resolve`/`parse`/`parse_from_default` の引数順序変更。
- `lib/rudesheim/command_line/parse/__init__.py`: `Command.parse_with` 内の再帰呼び出し `selectable.parser_define().resolve(...)` の引数順を追従。
- `tests/test_command_line.py`: `user_data` が単なる placeholder（`None`）だった呼び出しは省略する形に簡略化。`log`（実際に使う `user_data`）を渡していた `TerminalDispatchTests` の2箇所は `parse(arguments, log)` の順に変更。
- `examples/run.py`, `examples/smoke_install_check.py`: 同様に `None` の明示指定を省略。

### 確認結果
- 全 30 tests OK。両 examples とも実行確認済み。

## 2026-07-16（続き5） `user_data` を `user_datas` に改名し、既定値を `[]` に（可変デフォルト引数の罠を検出・修正）

### 決定内容
- `user_data`（単数）→ `user_datas`（複数形）に改名。`RunParameters`/`ParseState.following`/`Parser.resolve`/`parse`/`parse_from_default`/`parse/__init__.py` の再帰呼び出し、全て追従。
- 既定値を `None` ではなく `[]` にしたいという要望があったため変更しようとしたところ、**Pythonの可変オブジェクトをデフォルト引数にする既知の罠**を実際に踏んだ（`user_datas` を明示せずに `.parse()` を複数回呼ぶと、`.append()` した内容が呼び出しをまたいで蓄積してしまうことを実演で確認: 1回目 `['ping']` → 2回目 `['ping', 'ping']`）。
- 対策として、外部に見える既定値は `[]` のまま、内部実装だけ `None` を sentinel にして呼び出しごとに新しい `[]` を作る形にした（`user_datas = [] if user_datas is None else user_datas` を `resolve()` 冒頭に追加。`parse`/`parse_from_default` は `None` を許容してそのまま `resolve` に委譲するだけで済む）。
  - これは以前避けた「有無をNoneで表す」という設計判断とは別物。あちらは**ライブラリ利用者から見える意味論**（terminalsの有無など）の話で、今回はPython言語仕様の可変デフォルト引数バグを避けるための**実装内部限定**の技法。

### 実装したファイル
- `lib/rudesheim/command_line/__init__.py`: `RunParameters.user_datas`、`ParseState.following`、`Parser.resolve`/`parse`/`parse_from_default` を改名・`None`-sentinel化。
- `lib/rudesheim/command_line/parse/__init__.py`: `Command.parse_with` 内の再帰呼び出しを `user_datas` に追従。
- `tests/test_command_line.py`: `TerminalDispatchTests` の `run_parameters.user_data.append(...)` を `user_datas.append(...)` に改名。

### 確認結果
- 可変デフォルト引数バグが直っていることを実演で確認（`user_datas` を渡さず複数回 `.parse()` しても蓄積しない）。
- 全 30 tests OK。両 examples とも実行確認済み。

## 2026-07-16（続き6） 未カバーだった経路にテストを追加（ライブラリは変更せず）

### 方針
- 「このライブラリを使ったときに通るであろう経路」を洗い出し、既存30 testsで踏まれていないものにテストを追加。
- ライブラリ側の修正が必要な経路（root で何もマッチしない場合の `IndexError` の解消など）は対象外。Mock必須の経路・reflection必須の経路も対象外。
- 見つかった既存の未カバー経路はいずれも**ライブラリを直さなくても構築可能**だったので、全てテストとして追加できた。

### 追加した観点（新設16 tests、`SelectableProtocolTests` / `RunWithDispatchTests` / `ParserEdgeCaseTests`）
1. 裸の `cl.Selectable`（`Option`でも`Command`でもない）を category に直接 tie した場合
   - `key_spec` が `([],[])` を返すため getopt 側に一切登録されず、CLI から明示的に指定すると `UndefinedOptionSpecified` になる（`-p` を渡す）
   - `default()` 経由でのみ選択できる（何も渡さない場合）
   - これにより `parse/__init__.py` 側の internal `Selectable.parse_with`（何もしない既定）も初めて経路を通る
2. `ItemForHelp.description()` の既定実装（`this.__name__`）を上書きしないクラスでの動作
3. `Selectable.with_value()` の既定実装（`this` をそのまま返す）を、`value_amount()>0` だが `with_value` を上書きしないクラスで確認
4. `SelectableCategory.default()` の基底実装
   - `selectables_defines()` が空で `default()` 未上書き → `DefaultDoesNotExist`
   - `selectables_defines()` が非空で `default()` 未上書き → 先頭の selectable を返す
5. `DefineOfOption.option()` が `.selectable()` のエイリアスであること
6. `Selectable.run_with()` の既定実装（`RunWithNotImplemented` を raise）
   - 素の `Option` に対して直接呼ぶ場合
   - `run_with` を上書きしていない `Command` が `.parse()` で末端になった場合
7. `Parser.parse()` が `IndexError` になる経路（Command系categoryが1つも無い＝Optionだけの Parser で `.parse()` した場合。既知の未解決事項の実例としてそのまま記録）
8. `OptionForPrint`/`BasicHelp` の `run_with()` を実際に呼び出し、標準出力を `io.StringIO` + `contextlib.redirect_stdout` で捕捉して検証（従来は `print_string()` の文字列だけ検証しており、`run_with()` 自体は一度も呼ばれていなかった）
9. `user_datas` の可変デフォルト引数バグの回帰テスト（`user_datas` を渡さず `.parse()` を2回呼んでも蓄積しないことを確認）
10. `Parser.parse_from_default()`（従来ゼロカバレッジだった）。`sys.argv` を一時的に差し替えて確認（save/restore、ライブラリのmockではない）
11. `Parser.resolve()` の `0 == len(selectables)` 分岐を、「`categories_templates` が空」ではなく「非空だが全カテゴリの `selectables_defines()` が空」という別経路（`Category_2` 使用）から踏む
12. `GetoptError` のうち `"not recognize"` を含まないもの（値必須オプションに値が無い等）が `UndefinedOptionSpecified` に変換されず `resolve()` が暗黙に `None` を返すという、ライブラリ側の未修正の挙動をそのまま記録

### 実装したファイル
- `tests/test_command_line.py`: `import io` / `import contextlib` を追加。上記フィクスチャと3つの新規 `TestCase` クラスを追加。

### 確認結果
- 全 46 tests OK（既存30 + 新規16）。`test/run.py`（互換ランナー）、両 examples とも実行確認済み。

## 2026-07-16（続き2） Command の run_with 既定実装

### 決定
- `command_line.Command` に `run_with(this, context, categories, arguments = ())` の既定実装を追加。
- 中身は無害な `pass` ではなく、新設した `RunWithNotImplemented(BasicException)` を送出する形にした。
- 理由: `terminals`（`.parse()` が最後に `run_with` を呼ぶ対象）に入るのは常に `Command` 系のみ（`Option.parse_with` は `terminals` に一切触れない）。override し忘れた `Command` が terminal になったとき、`SelectableCategory.default()` が `DefaultDoesNotExist` を投げて失敗を明示する既存方針と揃え、黙って何もしないより早期に検知できるようにした。
- `OptionForRun.run_with` の無害な `pass` はそのまま維持（`OptionForRun` は "常に subclass で override される前提の hook" であり、素の `OptionForRun` が terminal として選ばれる想定自体が無いため、今回は不整合として扱わず据え置き）。

### 動作確認
- `Build`（`run_with` 未 override）を明示的に選ばせて `.parse()` を呼ぶと `RunWithNotImplemented` が正しく送出されることを確認。
- 別件として、root レベルで何もマッチしない場合（上記フォローアップ項目）は `terminals` 自体が空になるため `IndexError` のまま。今回の変更はこのケースを解消しない。

## 2026-07-16（続き7） README.md を最新 API に全面更新

### 経緯
- ここまでの一連の変更（`ParseState`/`RunParameters`、`OptionForRun` 削除、`user_datas`、`Command`/`parser_define()` によるsubcommand機能）を通じて、`README.md` は何度も「未着手・要フォローアップ」として記録したまま放置していた。

### 実施内容
- 全コード例をスクラッチで実際に実行して検証した上で書き換え。
- `Option` だけの例（Before/After・Real Workflow・Value Option・Quick Start）は `categories, arguments = cl.Parser(...).parse(...)` から `state = cl.Parser(...).resolve(...)` / `state.run_parameters.categories` / `state.run_parameters.arguments` に更新。
- Quick Start の `Main` は `cl.OptionForRun` ではなく `cl.Option` を直接継承する形に変更。
- 新設セクション:
  - 「Two Ways To Drive It」: `resolve()`（実行しない）と `parse()`（Commandの木を辿ってrun_withを自動で1回呼ぶ）の使い分け
  - 「Subcommands / Command Tree」: これまでREADMEに一切無かった `Command`/`parser_define()`/自動dispatchの説明。dockerのcompose風の例を実行確認込みで掲載。global/localのcategory継承、`RunWithNotImplemented`、root階層の`IndexError`（未解決事項）も明記
  - 「`RunParameters`」: `user_datas`/`categories`/`arguments`の説明
- 「Required vs Free (Contract)」を `Selectable`（新設）/`Option`/`Command`（新設）/`SelectableCategory`/`Parser`/`OptionForPrint`系まで全面的に書き直し。

### 確認結果
- 全46 tests OK、`examples/smoke_install_check.py` 実行確認済み。README中の全コード例はスクラッチで動作検証してから記載。

### 未着手・要フォローアップ（残り）
- `pyproject.toml` の package include 修正（wheel に parse 層が入らない件）。
- `SelectableCategory.default()` の `Option`/`Command` 間の非対称性、および root での `IndexError`。

## 2026-07-16（続き8） バージョンを 2.0 に、1.0 との非互換を明記

### 実施内容
- `pyproject.toml` の `version` を `0.1.0` → `2.0.0` に変更。
- `README.md` 冒頭に「Version 2.0 — Breaking Change Notice」節を新設し、1.0 と互換性が無いこと（`parse()` の返り値がタプルでなくなった、`run_with` が単一引数 `RunParameters` になった、`OptionForRun` 削除）を明記。
- `lib/command_line_rudesheim_python.egg-info/PKG-INFO` は build 時に自動再生成されるファイルのため手動編集はしていない（`pyproject.toml` の version が次回 build 時に反映される）。

### 確認結果
- 全46 tests OK（バージョン表記変更のみで実装への影響は無し）。

## 2026-07-16（続き9） 実装本体（lib/）に英語docstringを追加

### 方針
- `lib/rudesheim/command_line/__init__.py`（公開API）・`lib/rudesheim/command_line/parse/__init__.py`（内部層）の両方に英語でdocstringを追加。
- 各関数について「引数がどんな構造か」「小さい使用例」「注意点」を中心に記載。名前を読めば分かる説明（例: `name #this is name variable` のようなもの）は書かない。
- 複雑な出力（`BasicHelp.print_string()`のフォーマット等）は「テストの実際の出力例を見たほうが早い」旨だけ書き、逐一書き下さない。
- `parse/__init__.py`側は「内部層であり、公開層の同名クラスとは無関係（継承していない）」という、これまで何度も混乱の元になった点を モジュール docstring で明示。

### 記載した主な注意点（コード上は自明でない箇所）
- `Selectable.tie(keys, description)` の `keys` は `(short, long)` のペアではなく、各要素の文字数（1文字=short、2文字以上=long）で自己判定される独立したkeyの集合であること。
- `Selectable.with_value(strings)` の `strings` は複数形に見えるが実際はgetoptが渡す単一の`str`であること。
- 素の `Selectable`（`Option`でも`Command`でもない）は `key_spec()` が何も返さないため、CLIからは明示的に選べず `default()` 経由でしか到達できないこと。
- `RunParameters`/`ParseState`の各フィールドの役割（`user_datas`はライブラリが一切関与しない素通し値であること等）。
- `Parser.parse()` はCommand系categoryが木のどこかに無いと `IndexError` になること、`resolve()` は `"not recognize"` を含まない `GetoptError` を暗黙に `None` として返す既知の未修正挙動があること。
- `BasicHelp` は他の多くのSelectableと異なり**instance化**が必要で、`tie()`ではなく`DefineOfOption`で紐付ける必要があること。
- `Command.parse_with`の末端解決ロジック（子が見つからなければ直近の確定済み祖先にフォールバックする）の要点。

### 確認結果
- 全46 tests OK。両examples（`run.py`の引数無し／`-v`／`-h`、`smoke_install_check.py`）とも実行確認済み。
- `cl.Selectable.tie.__doc__` 等でdocstringが正しく参照できることを確認済み。

## 2026-07-16（続き10） `SelectableCategory.default()` の Option/Command 非対称性を解消（`decided_for` + `Terminal`）

### 背景・経緯
- 続き9までで残っていた既知の未解決事項を洗い出す中で、`default()` の意味が `Option` と `Command` とで食い違っていることに気付いた: `Option` は `default()` の戻り値が実際に使われる（値として消費される）のに対し、`Command` は `default()` の戻り値が `categories` に記録されるだけで、実行対象（terminal）の決定には一切関与しない。
- 具体例（`ComposeSubcommand.default()` が `Up` を返すケース）で確認: `compose` とだけ打つと `categories[ComposeSubcommand]` には `Up` が入るが、実際に呼ばれるのは直近の確定済み祖先 `Compose` の `run_with` であり、`Up.run_with` は一切呼ばれない。「`default()` は"選ばれなかった時にcategoryを埋める値を返す関数"のはずなのに、Command用のdefaultだけ実行に無関係」という非対称性が本質的な設計不備だと結論。
- root（`Parser.parse()`の一番外側）でCommand系categoryが1つもmatchしなかった場合、フォールバック先の祖先Commandが存在しないため`state.terminals[0]`が`IndexError`になる既知の穴（続き9までのnoteにも記載）も、同じ根本原因（`default()`の戻り値が実行経路に乗らない）から生じていることを確認。
- 「`default()`の戻り値も、明示的にmatchした場合と同じように再帰・実行の資格を持つべき」という方向で合意しつつ、単純に統一すると2つの問題が新たに発生することが分かった:
  1. **自己参照の無限再帰**: `category.default()`が、そのcategoryを宣言している`Command`自身を返すと、空引数のまま同じ未match分岐を無限に繰り返す。
  2. **「compose単体でcomposeの持つ処理を呼びたい」という要望との衝突**: 単純に「未matchなら`default()`に再帰する」を全階層に適用すると、`ComposeSubcommand.default()`が`Up`を返す限り、bareな`compose`は常に`Up.run_with`まで潜ってしまい、`Compose`自身の`run_with`（例: usage表示）を呼ぶ手段が無くなる。これは`git stash`が`git stash push`にフォールバックするのと同じ動きとしては正当だが、"compose自身の処理を代理無しで呼びたい"という要求とは別物であり、両立させる必要があった。

### 最終設計
1. `Selectable`に`decided_for(category, state)`を追加（base: no-op、`state`をそのまま返す）。呼ばれるタイミングは「このselectableがcategoryの値として決まった直後」——明示match経由（`parse.Command.parse_with`から）でも、`default()`経由（`Parser.resolve()`の埋めループから）でも、必ずこのタイミングで統一的に呼ばれる。
2. `Command`が`decided_for`をoverride: 自分の`parser_define()`に再帰し、再帰先が terminal を確定できなければ自分自身にfallback（`(next_state.terminals + [this])[0]`という既存のfallback式をそのまま流用）。
3. 新規`Terminal(Selectable)`を追加。overrideは一切無く、base の no-op `decided_for`をそのまま継承するだけの印。ネストしたCommand-typeのcategoryの`default()`に使うと「これ以上潜らず、自分を宣言している親Commandの`run_with`に委譲する」という意味になり、(2)の自己再帰問題を回避しつつ"proxyクラス無しでcompose自身の処理を呼ぶ"という要望も満たす。
4. rootには「委譲先の親」が存在しないため`Terminal`は使えない。rootのCommand-type categoryの`default()`には**実在する`Command`**（前段のexampleでは`Compose`自身）を返す必要がある——これは"compose upが実在の別commandである"のと同じ理屈で、proxyではなく本体。この制約により`Parser.resolve()`/`Parser.parse()`側にはroot専用の特別分岐が一切不要になった（`decided_for`が明示match/default()どちらの経路でも同じ再帰をたどるため、rootでも自然にterminalsが埋まる）。
5. `Parser.resolve()`の埋めループを、`category.default()`で埋めた値にも`decided_for`を通すよう変更（`state = default_value.decided_for(category, state)`）。
6. `parse.Command.parse_with`（`lib/rudesheim/command_line/parse/__init__.py`）は「keyを探してcategoriesに詰め、`selectable.decided_for(...)`に委譲する」だけの薄い実装に簡略化。再帰・fallbackの実ロジックは`command_line.Command.decided_for`に一本化（重複を避けるため）。
7. `decided_for`の置き場所を`parse/__init__.py`側にできないか検討したが、`parse.Command`は公開APIの`Command`サブクラス（`Compose`等）の継承チェーンに入っておらず（`parse_identifier()`によるタグ付けのみで繋がる設計）、`selectable.decided_for(...)`という呼び出しがそもそも届かないため不可能と判断。`parse_identifier()`/`key_spec()`/`external_key_for()`と同様、「利用者は普段触らないが種別ごとの多態性が要るので公開側に置かざるを得ない」枠として`command_line.*`側に置いた。
8. 新たな制約として、**1つの`Parser`の`categories_templates_`にCommand-type categoryは1つまで**（Option-type categoryは複数可）とドキュメント化。理由: 埋めループは`categories_templates_`の順に処理され、複数のCommand-type categoryが両方未matchで`decided_for`により再帰した場合、後段の`decided_for`が前段の`.terminals`への寄与を問答無用で上書きしてしまい、優先順位が未定義になる。実行時チェックは入れず、文書上の制約に留めた（`OptionIsInConflict`のような能動的な検出は今回は見送り）。

### 実装
- `lib/rudesheim/command_line/__init__.py`: `Selectable.decided_for`（no-op）、`Command.decided_for`（再帰+fallback）、`Terminal`クラス新設、`Parser.resolve()`の埋めループ更新。
- `lib/rudesheim/command_line/parse/__init__.py`: `Command.parse_with`を簡略化。
- `tests/test_command_line.py`: `test_fallback_terminal_is_nearest_matched_ancestor`のfixture（`ComposeSubcommand.default()`）を`Up`→`cl.Terminal`に変更（"compose自身の処理が呼ばれる"という元の意図を維持）。新規テストを3件追加（`TerminalDispatchTests.test_root_default_recurses_instead_of_index_error`: rootのdefault()が実在Commandなら`.parse([])`が`IndexError`にならず届くこと／`DecidedForTests.test_terminal_decided_for_is_inert_no_op`／`DecidedForTests.test_category_with_no_declared_selectables_always_dispatches_to_its_default`: `selectables_defines()`が空でも`default()`をoverrideすれば常にそのCommandに落ちる縮退ケース）。
- `README.md`: 「Subcommands / Command Tree」の例・解説を`Terminal`/`decided_for`ベースに全面更新（`$ myapp`引数無しの例を追加、以前は`IndexError`だったが動くようになったことを明示）。「Required vs Free」に`decided_for`（`Selectable`/`Command`）と`Terminal`の節を追加。1 Parser内Command-type category単一の制約を明記。

### 副次的な発見（未対応、別件として記録のみ）
- `Parser.resolve()`には「どのcategoryも`selectables_defines()`に1件も無ければ即座に空の`ParseState`を返す」早期returnがあり、埋めループ自体をスキップする。このため「category単体では`selectables_defines()`が空でも、Parser全体としては他のcategoryが何か1つでも宣言していれば埋めループは動く」という前提を満たさないと、`default()`をoverrideしていても`decided_for`まで届かない（早期returnで握りつぶされる）。新規テストではこれを踏まないよう、無関係な`NoopCategory`を隣に置いて回避した。この早期returnの妥当性自体は今回のスコープ外として未着手のまま。

### 確認結果
- 全49 tests OK（46 + 新規3）。`examples/run.py`（引数無し／`--example`／`--version`／`--help`）、`examples/smoke_install_check.py`とも実行確認済み。README「Subcommands / Command Tree」の全コード例をスクラッチで実行し、記載通りの出力を確認済み。

## 2026-07-16（続き10） `key_spec`/`external_key_for`/`decided_for` を `parse.*` へ移設

### 経緯・前回結論の訂正
- 上記「副次的な発見」の直前のセクションで「`decided_for`を`parse/__init__.py`側に置くのは不可能」（`parse.Command`は公開`Command`の継承チェーンに入らないため`selectable.decided_for(...)`が届かない、という理由）と結論づけていたが、これは**呼び出し規約を変えれば解消できる**ことが分かった。
- `parse_with`が既にやっている「`this`=識別子クラス、実データは引数で渡す」という形に`key_spec`/`external_key_for`/`decided_for`も合わせ、`selectable.parse_identifier().the_method( ..., selectable )`という呼び方に統一すれば、継承に頼らずとも`parse.*`側に実装を置ける。
- 一方で`value_amount()`/`with_value()`/`tie()`/`basic_tie()`/`run_with()`は「利用者が値・振る舞いを渡すためのデータ・拡張点」または「種別分岐すら無い純粋な公開API」なので、`command_line.*`側に残す。

### 実施内容
- `command_line.Selectable`/`Option`/`Command`から`external_key_for`/`key_spec`/`decided_for`を削除。`parse_identifier`はそのまま残す（これが唯一の"入口"）。
- `parse.Selectable`/`Option`/`Command`に`external_key_for(key, selectable)`/`key_spec(key, selectable)`/`decided_for(category, state, selectable)`を実装（`selectable`を明示引数として追加）。`parse.Option.key_spec`は`this.value_amount()`ではなく`selectable.value_amount()`を見るように修正。`parse.Command.decided_for`は`this.parser_define()`ではなく`selectable.parser_define()`を呼ぶよう修正（`command_line.Command.decided_for`から移設）。
- 呼び出し箇所5箇所を全て`identifier.the_method( ..., selectable )`の形に統一:
  - `Parser.resolve()`のlookup構築ループ（`external_key_for`/`key_spec`）
  - `Parser.resolve()`の埋めループ（`decided_for`）
  - `BasicHelp.print_string()`（`external_key_for`）
  - `parse.Command.parse_with`内の再帰呼び出し（`decided_for`）
- `SelectableCategory.selectables_defines()`のdocstringに残っていた`Selectable.key_spec()`への古い参照も、移設先を指すよう修正。
- `tests/test_command_line.py`の`DecidedForTests.test_terminal_decided_for_is_inert_no_op`が`cl.Terminal.decided_for(None, state)`と旧APIを直接呼んでいたため、`cl.Terminal.parse_identifier().decided_for(None, state, cl.Terminal)`に修正。

### 確認結果
- 全49 tests OK。`examples/run.py`（引数無し／`-v`／`-h`）、`examples/smoke_install_check.py`、`test/run.py`（互換ランナー）とも実行確認済み。
- `grep`で`.external_key_for(`/`.key_spec(`/`.decided_for(`の呼び出し箇所が全て`identifier`/`parse_identifier()`経由に揃っていることを確認済み。
