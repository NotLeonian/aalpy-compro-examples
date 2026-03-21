# examples/abc424_d
## 問題
[AtCoder × Engineer Guild オンサイトコンテスト ～集結！高レート人材～予選（AtCoder Beginner Contest 424） D - 2x2 Erasing 2](https://atcoder.jp/contests/abc424/tasks/abc424_d)

## 使用方法
### 素朴な accepts 判定関数などの記述
[property.py.tmpl](./property.py.tmpl) に `alphabet` と `accepts` 関数を Python で記述する。

> [!NOTE]
> 高速化のために、アルファベットは `(0,0,0,0,0,0,0)` や `(1,1,1,1,1,1,1)` などではなく `0` や `127` などのただの整数にすることをおすすめする。

`accepts` 関数では素朴に全ての $2\times 2$ 部分正方形に白いマスが存在するかを判定している。  
`__is_black` 関数や `__subtask` 関数のように別の関数を定義して使用してもよい。

また、この問題では、受理条件が非常に局所的であるため、全ての長さ 2 以下の文字列に対して正しく受理判定ができる DFA が求まればよいと予想できる。  
そこで、`iter_eq_words` 関数に全ての長さ 1 または 2 の文字列を生成するジェネレータ関数を記述する。  
なお、生成される文字列に空文字列を含める必要はない。

aalpy-compro が自前実装している `FixedWordsEqOracle` によるオートマトン学習（`eq_words` / `iter_eq_words` を使用するもの）では、一般には正しく学習が終了することは保証されない。  
ただし、この問題に対しては正しく学習が終了することが証明できると考えている（ただし、厳密に示すために正規言語と AALpy や `FixedWordsEqOracle` の性質に踏み込む必要がある可能性はある）。  
この問題においては、 $W=7$ の場合に `MAX_LEN` を `2` から `3` に変更しても状態数が変化しないため、コンテスト中であってもそれなりに確信は持てるだろう。

現在の aalpy-compro の実装では、それぞれの DFA のために Python ファイルを作らなければならない。  
そこで、 $W$ の値は f-文字列のように `{W}`と記述している。  
そして、[run.py](./run.py) で学習の実行前に $W$ を埋め込んだ一時ファイルを生成する。  
もちろん 6 ファイルを手で作ってもよい。

なお、[property.py.tmpl](./property.py.tmpl) を Python ファイルとして見るとシンタックスエラーが発生している状態である。  
最初から property.py.tmpl を書こうとするよりも、たとえば property_7.py を先に書き、後から汎用化した property.py.tmpl を作るほうがストレスが少ない。

### 学習を実行するスクリプトの記述
6 通りの学習をする必要があるため、スクリプト [run.py](./run.py) を用意している。  
もちろん、全て手で実行してもよい。

丁寧に書いてあるが、参考にする際に変更すべき点は多くない。

まず、各 DFA に合わせて `key`、`context`、`max_states` を適切に書き換える必要がある。  
`key` は他の DFA の `key` と被らないような英数字とアンダースコアからなる文字列であれば自由である。  
`context` は [property.py.tmpl](./property.py.tmpl) における `{W}` の実際の値の辞書である。

また、`--algorithm` として `kv` ではなく `lstar` を選択している。  
この問題では L* と KV で学習にかかる時間に大きく差があるわけではない。  
一方で、1 ステップで必ず 1 つの新たな状態が得られるか停止する KV と異なり、L* では 1 ステップで複数の新たな状態が得られることが多いため、`--print-level` を 1 以上にして実行させているときに安心感が大きい。

生成については、C++ の記述の順序の関係から、必ず `write(learn_args(key=key, property_path=property_path))` よりも先に `write(common_args())` が呼び出されるようにすること。

### 学習の実行
shebang を書いているので、bash や zsh などであればそのまま `./run.py` でよい。  
そうでない環境では、`uv run run.py` を推奨する。

[learned_dfa.cpp](./learned_dfa.cpp) が生成される。

### main 関数などの追加
learned_dfa.cpp には main 関数などがないため、ジャッジ環境に提出できるようにこちらで追加する必要がある。

`learned_dfa::dfas().get(key)` で `key` をキーとする DFA が得られる。

この問題では、各行について入力文字のうち最初から白であるマスが白のままであるもののみを考え、最初は黒であるマスが黒のままならコスト $0$ 、白に変わるならコスト $1$ としたときのコストの合計をその行における入力文字のコストとすればよい。  
そして、コストの合計の最小値を求める DP を行えばよい。

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
[AC 提出 (C++23 (GCC 15.2.0), 20 ms)](https://atcoder.jp/contests/abc424/submissions/74253726)
