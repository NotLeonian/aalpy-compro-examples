# aalpy-compro-examples
Examples of solving competitive programming problems with automata learning using AALpy

## これは？
能動オートマトン学習を用いて解ける競技プログラミングの問題について、AALpy の学習結果を C++ のソースコードに変換するツール **aalpy-compro** とその使用例を公開するリポジトリです。

また、aalpy-compro には正規表現から等価な最小 DFA に変換する補助機能も含まれています。  
これは能動オートマトン学習そのものではなく、オートマトンを扱うための別系統の機能です。

aalpy-compro はコンテスト中であってもある程度使いやすいように設計しているつもりです。

> [!CAUTION]
> **aalpy-compro をコンテスト中に使用しようとする場合は、使用したいコンテストのルールを事前に確認してください。**  
> また、AALpy は「AtCoder生成AI対策ルール - 20251003版」([ja](https://info.atcoder.jp/entry/llm-rules-ja) / [en](https://info.atcoder.jp/entry/llm-rules-en)) などで定義されている「生成 AI」にはあたらないとリポジトリの作成者 (@NotLeonian) は考えていますが、**コンテスト中に使用したい場合はそのコンテストの生成 AI に関するルールを事前に確認するとともに、能動オートマトン学習および AALpy について事前に知っておくことを推奨します。**
>
> **If you intend to use aalpy-compro during a contest, please check the rules of the contest you plan to participate in beforehand.**  
> The repository author (@NotLeonian) believes that AALpy does not fall under the category of “generative AI” as defined by rules such as the “AtCoder Rules against Generative AI - Version 20251003” ([ja](https://info.atcoder.jp/entry/llm-rules-ja) / [en](https://info.atcoder.jp/entry/llm-rules-en)); however, **if you intend to use it during a contest, it is recommended that you check that contest’s rules regarding generative AI in advance and familiarize yourself beforehand with active automata learning and AALpy.**

## 推奨環境
### aalpy-compro および examples
uv が使える環境を推奨します。

### 生成された C++ コードを動作させる環境
aalpy-compro は C++ のソースコードの一部を出力します。  
使用者が適切に `main` 関数などを追記したうえで、 GCC または Clang でコンパイルすることを想定しています。  
その際、コンパイルオプションで `-std=gnu++17` を指定することを仮定しています。  
したがって、`-std=gnu++17` に対応しているバージョンの GCC または Clang を使用することを推奨します。

> [!WARNING]
> **C++17 以上に対応していないジャッジ環境においては、生成されたコードの一部の記述を修正しないとコンパイルエラーになる可能性があります。**

## インストール
1. uv をインストールする。
1. このリポジトリをクローンする。
1. プロジェクトルートで `uv sync` をする。

uv の設定によっては、`uv python install` 等の他のコマンドの実行も必要になるかもしれません。

## 使用方法について
### 使用方法の軽い説明
`uv run aalpy-compro ...` を実行します（`...` の部分でコマンドライン引数を指定）。  
venv 環境を使えば `aalpy-compro` コマンドを使用することも可能です（上級者向け）。

`--kind common` では、C++ の `class DFA` などが生成されます。  
現状の仕様では、これによって生成されるソースコードをファイルの先頭に書かないとコンパイルエラーになります。

具体的な DFA を得るために、`--kind learn` による能動オートマトン学習または `--kind regex` による正規表現からの変換を使用できます。  
このとき、使用者は `--key` に続けて、その DFA に対する他の DFA と被らないキーを指定する必要があります。

`--kind learn` では、能動オートマトン学習を行えます。  
使用者はアルファベット `alphabet` および受理判定の関数 `accepts` が記述された Python のソースコードのパスを、`--path` に続けて与える必要があります。  
また、使用者は使用するオラクル（`wp`, `random_wp`, `state_prefix` のどれか 1 つ）を `--oracle` に続けて与えるか、その代わりに学習中に受理判定などに使用する語の一覧を `eq_words`（語のリスト）または `iter_eq_words`（語が `yield` 文の返り値として列挙された関数）として `--path` に与えた Python のソースコード内に記述する必要があります。

さらに、`--oracle wp` とした場合、最小 DFA の状態数の上界を `--max-states` に続けて与える必要があります。  
与えた値が実際の最小 DFA の状態数より小さい場合、`aalpy_compro.errors.ConstraintViolationError` により終了する（もしくは等価でない DFA が返る）可能性がありますが、大きすぎると実行に時間がかかる可能性があります。

> [!WARNING]
> 受理判定関数の表す言語が本当に正規言語であり、さらに `--oracle wp` とし、かつ `--max-states` に実際の最小 DFA の状態数以上の値を設定した場合のみ、返ってくる DFA が学習したい正規言語と等価であることが保証できます。  
> **そうでない場合、等価でない DFA を返す可能性があります。**

基本的には `--oracle wp` を使用するとよいでしょう（その他は上級者向け）。

aalpy-compro では、語を表現するために各文字のリストなどではなく**各文字のタプル**を使用しています。  
`accepts` や `eq_words` または `iter_eq_words` は、語が各文字のタプルとして表現されることを前提に実装する必要があります。

`--kind regex` では、正規表現から等価な最小 DFA への変換が行えます。  
使用者はアルファベット `alphabet` および aalpy-compro の `Regex` クラス（または `ComplementRegex` クラス）による正規表現 `regex` が記述された Python のソースコードのパスを、`--path` に続けて与える必要があります。  
なお、`regex` を定義するために `aalpy_compro` から `Regex` を import する必要があります（基本的には `Regex` のみで十分ですが、`ComplementRegex` の import も必要になるかもしれません）。

### 使用方法の詳細について
`examples/` 内のソースコードおよびドキュメントを参考にしてください。
