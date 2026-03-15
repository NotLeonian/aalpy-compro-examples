# aalpy-compro
Libraries to solve competitive programming problems with automata learning using AALpy

## bash / zsh / tcsh での Tab 補完
以下のコマンドで、オプションの Tab 補完が行われるようになります。

bash:
```sh
eval "$(aalpy-compro --print-completion bash)"
```

zsh:
```sh
eval "$(aalpy-compro --print-completion zsh)"
```

tcsh:
```sh
eval "$(aalpy-compro --print-completion tcsh)"
```

このコマンドは現在のセッションにのみ影響します。  
永続化できる他の方法もありますが、このドキュメントでは説明しません。
