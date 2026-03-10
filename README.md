# aalpy-compro-examples
Examples of solving competitive programming problems with automata learning using AALpy

## これは？
能動オートマトン学習を用いて解ける競技プログラミングの問題について、AALpy の学習結果を C++ のソースコードに変換する `aalpy-compro` とその使用例を公開するリポジトリです。

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

> [!NOTE]
> 現在、aalpy-compro は hatchling と hatch-vcs を用いてバージョン管理をしており、aalpy-compro-examples ではワークスペースの aalpy-compro をインストールするように uv 側で設定しています。  
> aalpy-compro のバージョンが上がった後、`uv sync` の再実行などではバージョンが上がらない事象を確認しています。  
> もしバージョンが上がらなければ、`uv sync --reinstall-package aalpy-compro` も試してみてください。

## 使用方法について
`examples/` 内のソースコードおよびドキュメントを参考にしてください。

現時点では、aalpy-compro についての他の詳しいドキュメントはありません。
