# aalpy-compro-examples
Examples of solving competitive programming problems with automata learning using AALpy

## これは？
能動オートマトン学習を用いて解ける競技プログラミングの問題について、AALpy の学習結果を C++ のソースコードに変換するツール **aalpy-compro** とその使用例を公開するリポジトリです。

なお、aalpy-compro はコンテスト中であってもある程度使いやすいように設計しているつもりです。

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
`examples/` 内のソースコードおよびドキュメントを参考にしてください。

現時点では、aalpy-compro についての他の詳しいドキュメントはありません。
