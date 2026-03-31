# examples/
## 分類
- [abc418_g](./abc418_g) : `--kind learn`, `--algorithm kv`, `--oracle wp`
- [tdpc_grid](./tdpc_grid) : `--kind learn`, `--algorithm lstar`, `--oracle wp`
- [OUPC2024_C](./OUPC2024_C) : `--kind regex`
- [tenka1_2019_C](./tenka1_2019_c) : `--kind regex`
- [abc424_d](./abc424_d) : `--kind learn`, `--algorithm lstar`, `iter_eq_words()` 関数を定義

## 各 learned_dfa.cpp について
- 生成されるソースコードに記述される関数などを増やした。
- AALpy で学習した DFA を C++ のソースコードに変換するロジックを変更した。

などの理由で、リポジトリ内の learned_dfa.cpp と現在の aalpy-compro が生成する learned_dfa.cpp が異なる場合がある。

ただし、その場合も現在の aalpy-compro が生成する learned_dfa.cpp に問題がないことを基本的に確認している。
