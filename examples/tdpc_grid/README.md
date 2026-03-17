# examples/tdpc_grid
## 問題
[Typical DP Contest S - マス目](https://atcoder.jp/contests/tdpc/tasks/tdpc_grid)

以降、このドキュメントではこの問題を「TDPC-S」と呼ぶ。

## 使用方法
### 素朴な accepts 判定関数の記述
[property.py.tmpl](./property.py.tmpl) に `alphabet` と `accepts` 関数を Python で記述する。

> [!NOTE]
> 特に $H=5,6$ に対する学習は時間がかかることが予想されるため、アルファベットは `(0,0,0,0,0,0)` や `(1,1,1,1,1,1)` などではなく `0` や `63` などのただの整数にすることをおすすめする。

`accepts` 関数は一般的な DFS で実装している。  
`__is_black` 関数のように別の関数を定義して使用してもよい。

現在の aalpy-compro の実装では、それぞれの DFA のために Python ファイルを作らなければならない。  
そこで、 $H$ の値は f-文字列のように `{H}`と記述している。  
そして、[run.py](./run.py) で学習の実行前に $H$ を埋め込んだ一時ファイルを生成する。  
もちろん 5 ファイルを手で作ってもよい。

なお、[property.py.tmpl](./property.py.tmpl) を Python ファイルとして見るとシンタックスエラーが発生している状態である。  
最初から property.py.tmpl を書こうとするよりも、たとえば property_6.py を先に書き、後から汎用化した property.py.tmpl を作るほうがストレスが少ない。  
また、この問題は明らかに $H=5,6$ の学習の難易度が高いため、 $H=5,6$ は手で行うのもよい。

### 学習を実行するスクリプトの記述
5 通りの学習をする必要があるため、スクリプト [run.py](./run.py) を用意している。  
もちろん、全て手で実行してもよい。

丁寧に書いてあるが、参考にする際に変更すべき点は多くない。

まず、各 DFA に合わせて `key`、`context`、`max_states` を適切に書き換える必要がある。  
`key` は他の DFA の `key` と被らないような英数字とアンダースコアからなる文字列であれば自由である。  
`context` は [property.py.tmpl](./property.py.tmpl) における `{H}` の実際の値の辞書である。

そして、`max_states` は各最小 DFA の状態数の上界である。  
実際の最小 DFA の状態数よりも小さい値を指定すると、DFA は正しく学習されない。  
この [run.py](./run.py) では実際の最小 DFA の状態数を指定しているが、もしコンテスト中に使うのであれば実際の最小 DFA の状態数はわからないと考えたほうがよい。  

TDPC-S は数え上げなので、正しい DFA が得られているかどうかはわかりやすい。  
したがって、特に $H=5,6$ については正しい DFA が得られるまで徐々に `max_states` を大きくしていくことも考えられる。  
ただし、少し大きくしただけでも学習にかかる時間が増大するので、少しずつ値を大きくして試す必要がありそうである。

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

aalpy-compro では、状態 $i$ から状態 $j$ に遷移する入力文字の個数を $(i,j)$ 成分とする行列を返す関数を用意している。  
この問題に対して得られる DFA の状態数と文字集合の要素数の差は小さいが、状態数が文字集合の要素数より大きい場合は疎行列に対するアルゴリズムを使用したほうが計算量が良い可能性がある。  
例示も兼ねて、`sparse_transition_count_matrix` 関数を使用している。

この行列を $A$ とし、 $i$ が受理状態であれば $i$ 番目の成分は $1$ となり、そうでなければ $i$ 番目の成分は $0$ となる列ベクトルを $b$ とする。  
また、初期状態を $\mathrm{ini}$ とする。  
このとき、答えは $(A^W b)_{\mathrm{ini}}$ である。

状態数を $N$ とする。  
疎行列の場合、 $W$ が大きければ $(A^0 b)_{\mathrm{ini}}, \,(A^1 b)_{\mathrm{ini}}, \,(A^2 b)_{\mathrm{ini}}, \,\ldots, \,(A^{2N-1} b)_{\mathrm{ini}}$ (最初の $2N$ 項) を素朴に求めて Berlekamp–Massey / Bostan–Mori アルゴリズムを使用するのが高速である。

ただし、この問題では $W$ の上限が大きくないので、全て素朴に計算するとして問題ない。

これらを踏まえ、learned_dfa.cpp に main 関数などを追加したのが [refined_solution.cpp](./refined_solution.cpp) である。

> [!NOTE]
> refined_solution.cpp では、learned_dfa.cpp に `main` 関数などを追加するだけでなく、標準ライブラリの追加のインクルードや clang-format によるフォーマットも行っている。

### コンパイル・実行
GCC の場合、以下のようなコンパイルコマンドを想定している。
```bash
g++ -std=gnu++17 -I ../../ac-library refined_solution.cpp
```

なお、[.gitignore](../../.gitignore) の都合上、実行ファイルの名前を指定する場合も拡張子はなしにせず `.out` 等にするほうがよいかもしれない。  
もちろん PR などを出す気がなく、クローンして使いたいだけであれば特に問題はない。

### 提出
GCC または Clang で、C++17 以上を選択することを推奨する。  
C++17 ぴったりを選択する必要はない。

## 提出結果
[AC 提出 (C++23 (GCC 15.2.0), 2 ms)](https://atcoder.jp/contests/tdpc/submissions/74190550)
