# examples/abc418_g
## 問題
[AtCoder Beginner Contest 418 G - Binary Operation](https://atcoder.jp/contests/abc418/tasks/abc418_g)

以降、このドキュメントではこの問題を「ABC418-G」と呼ぶ。

## 使用方法
### 素朴な accepts 判定関数の記述
[property.py.tmpl](./property.py.tmpl) に `alphabet` と `accepts` 関数を Python で記述する。

> [!NOTE]
> 適切に `accepts` 関数が実装されていれば、`alphabet` の中身は重要ではない。  
> たとえば、`[0, 1]` の代わりに `["0", "1"]` と書いても、`accepts` 関数の実装で吸収させることができる。

`accepts` 関数は CYK 法で実装している。  
ローカルで実行するためのものであるから、ジャッジ環境に入っているライブラリにこだわらなくてもよい。

現在の aalpy-compro の実装では、それぞれの DFA のために Python ファイルを作らなければならない。  
そこで、配列 `P` 内に f-文字列のように `{A}`, `{B}`, `{C}`, `{D}` と記述している。  
そして、[run.py](./run.py) で学習の実行前に $A, B, C, D$ を埋め込んだ一時ファイルを生成する。  
もちろん 16 ファイルを手で作ってもよい。

なお、[property.py.tmpl](./property.py.tmpl) を Python ファイルとして見るとシンタックスエラーが発生している状態である。  
最初から property.py.tmpl を書こうとするよりも、たとえば property_1001.py を先に書き、後から汎用化した property.py.tmpl を作るほうがストレスが少ない。

### 学習を実行するスクリプトの記述
16 通りの学習をする必要があるため、スクリプトを用意している。
もちろん、全て手で実行してもよい。

丁寧に書いてあるが、参考にする際に変更すべき点は多くない。

まず、各 DFA に合わせて `key`、`context` を適切に書き換える必要がある。  
`key` は他の DFA の `key` と被らないような英数字とアンダースコアからなる文字列であれば自由である。  
`context` は [property.py.tmpl](./property.py.tmpl) における `{A}`, `{B}`, `{C}`, `{D}` の実際の値の辞書である。

また、`learn_args` 関数内の `["--max-states", str(7)]` の `7` は DFA の状態数の上界であり、適切に設定する必要がある。

> [!NOTE]
>デフォルトの設定で学習が上手くいかなければ `learn_args` 関数内の `["--oracle", "wp"]` を、`"random_wp"` または `"state_prefix"` に変更することも手である。  
> ただし、その場合は他のオプションも適切に追加・変更・削除する必要がある（上級者向け）。

C++ の記述の順序の関係から、必ず `write(learn_args(key=key, property_path=property_path))` よりも先に `write(common_args())` が呼び出されるようにすること。

### 学習の実行
shebang を書いているので、bash や zsh であればそのまま `./run.py` でよい。  
そうでない環境では、`uv run run.py` を推奨する。

[learned_dfa.cpp](./learned_dfa.cpp) が生成される。

### main 関数などの追加

learned_dfa.cpp には main 関数などがないため、ジャッジ環境に提出できるようにこちらで追加する必要がある。

`learned_dfa::dfas().get(key)` で `key` をキーとする DFA が得られる。

aalpy-compro は ABC418-G で使用できる `longest_accepted_substring_length` 関数および `count_accepted_substrings` 関数を既に用意しているので、それらを呼び出して出力するのみでよい。

learned_dfa.cpp に main 関数などを追加したのが [refined_solution.cpp](./refined_solution.cpp) である。

> [!NOTE]
> learned_dfa.cpp と比較すると、インクルードされているヘッダが増えていたり、clang-format によるフォーマットで微妙に改行位置などが異なっていたりするが、重要ではない。

### コンパイル・実行
GCC の場合、以下のようなコンパイルコマンドを想定している。
```bash
g++ -std=gnu++17 refined_solution.cpp
```

なお、[.gitignore](../../.gitignore) の都合上、実行ファイルの拡張子はなしにせず `.out` 等にするほうがよいかもしれない。  
もちろん PR などを出す気がなく、クローンして使いたいだけであれば特に問題はない。

### 提出
GCC または Clang で、C++17 以上を選択することを推奨する。  
C++17 ぴったりを選択する必要はない。

## 提出結果
[AC 提出 (C++23 (GCC 15.2.0), 81 ms)](https://atcoder.jp/contests/abc418/submissions/73990647)
