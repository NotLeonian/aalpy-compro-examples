# examples/tenka1_2019_c
## 問題
[Tenka1 Programmer Beginner Contest 2019 C - Stones](https://atcoder.jp/contests/tenka1-2019-beginner/tasks/tenka1_2019_c)

## 使用方法
aalpy-compro では正規表現から最小 DFA を得られる。  
検索・置換などで使われる拡張された正規表現ではなく、正規言語を表す狭義の正規表現であることに注意。

正規表現の `.` とややこしいため、`'.'` を `0`、`'#'` を `1` と記述する。  
この問題の「黒い石のすぐ右に白い石があるような箇所がない」は明らかに `0*1*` という条件に言い換えられる。

ただし、aalpy-compro には `.` も補言語の最小 DFA の計算も機能として既にあるため、その考察すら必要ない。  
`.*10.*` で表される言語の補言語の最小 DFA を得られればよい。

### 正規表現の記述

[property.py](./property.py) に `alphabet` と `regex` を Python で記述する。

`from aalpy_compro import Regex` で `Regex` クラスを import できる。

1 語からなる言語の正規表現を得るには、`Regex.word` クラスメソッドを使用する。  
また、正規表現の `.` は `Regex.dot()` で得られる。  
アルファベットの情報を持たないため、型注釈に引っかかる可能性があることに注意。

連結は `+`、クリーネ閉包は `.star()` で得られる。  
また、補集合は `~` で得られる。

なお、補集合の `ComplementRegex` クラスには演算は定義されておらず、トップレベルで使用することが想定されている。  
ただし、 `~~` などのように `ComplementRegex` の補集合をとって `Regex` に戻すことは可能である。

これらを用いて、最小 DFA が欲しい言語の正規表現を `regex` に代入すればよい。

### 最小 DFA の計算を実行するスクリプトの記述
この問題では複数の最小 DFA を得る必要はないが、`common`, `regex` の順に aalpy-compro を実行してその結果を結合させる必要があるため、スクリプト [run.py](./run.py) を用意している。  
もちろん、手で実行してもよい。

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

この問題では、入力文字と $S$ の比較でコストの寄与が決まる場合のコストの合計の最小値を求める DP を行えばよい。

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
[AC 提出 (C++23 (GCC 15.2.0), 6 ms)](https://atcoder.jp/contests/tenka1-2019-beginner/submissions/74238504)
