# examples/OUPC2024_C
## 問題
[OUPC2024 Day 1 Problem C - Handai Color](https://onlinejudge.u-aizu.ac.jp/beta/room.html#OUPC2024/problems/C)

## 使用方法
aalpy-compro では正規表現から最小 DFA を得られる。  
検索・置換などで使われる拡張された正規表現ではなく、正規言語を表す狭義の正規表現であることに注意。

この問題を解くために、`B+Y+K+|K+Y+B+` という正規表現で記述される言語の最小 DFA を得ることにする。

### 正規表現の記述

[property.py](./property.py) に `alphabet` と `regex` を Python で記述する。

`from aalpy_compro import Regex` で `Regex` クラスを import できる。

`Regex.symbol` クラスメソッドで、引数に指定した 1 文字のみを含む言語を表す表現が得られる。  
この問題では不要だが、一般の 1 語からなる言語であれば `Regex.word` クラスメソッドを使用する。

連結は `+`、和集合は `|`、クリーネ閉包は `.star()` で得られる。  
また、正規表現の `+` にあたる表現は `.plus()` で得られる。  
そして、正規表現の `?` にあたる表現も `.optional()` で得られる。

これらを用いて、最小 DFA が欲しい言語の正規表現を `regex` に代入すればよい。

### 最小 DFA の計算を実行するスクリプトの記述
この問題では複数の最小 DFA を得る必要はないが、`common`, `regex` の順に aalpy-compro を実行してその結果を結合させる必要があるため、スクリプト [run.py](./run.py) を用意している。  
もちろん、全て手で実行してもよい。

この問題では複数の最小 DFA を得る必要がないため、[run.py](./run.py) を参考にする際に変更すべき点は多くない。  
逆に、複数の最小 DFA を得る必要がある問題では、そのような別の問題の run.py を参考にしたほうがよい。

変更する可能性があるのは主に `key` に入れた文字列である。  
`result` のままでよければ、これも変更する必要はない。

### 学習の実行
shebang を書いているので、bash や zsh などであればそのまま `./run.py` でよい。  
そうでない環境では、`uv run run.py` を推奨する。

[learned_dfa.cpp](./learned_dfa.cpp) が生成される。

### main 関数などの追加

learned_dfa.cpp には main 関数などがないため、ジャッジ環境に提出できるようにこちらで追加する必要がある。

`learned_dfa::dfas().get(key)` で `key` をキーとする DFA が得られる。  
また、それとは別に、状態数や文字集合の要素数を `constexpr` で得ることもできる。

この問題は条件を満たす区間の長さの**合計**の最大値であるため工夫が必要であるが、DP で求めることができる。

learned_dfa.cpp に main 関数などを追加したのが [refined_solution.cpp](./refined_solution.cpp) である。

> [!NOTE]
> refined_solution.cpp では、learned_dfa.cpp に `main` 関数を追加するだけでなく、標準ライブラリの追加のインクルードや clang-format によるフォーマットも行っている。

### コンパイル・実行
GCC の場合、以下のようなコンパイルコマンドを想定している。
```bash
g++ -std=gnu++17 refined_solution.cpp
```

なお、[.gitignore](../../.gitignore) の都合上、実行ファイルの名前を指定する場合も拡張子はなしにせず `.out` 等にするほうがよいかもしれない。  
もちろん PR などを出す気がなく、クローンして使いたいだけであれば特に問題はない。

### 提出
GCC または Clang で、C++17 以上を選択することを推奨する。  
C++17 ぴったりを選択する必要はない。

## 提出結果
[AC 提出 (C++23, 0.02 s)](https://onlinejudge.u-aizu.ac.jp/beta/review.html#OUPC2024/11377904)
