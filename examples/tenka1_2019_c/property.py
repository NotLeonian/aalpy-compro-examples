from aalpy_compro import Regex

alphabet = [0, 1]  # 0: 白, 1: 黒

black_white = Regex.symbol(1) + Regex.symbol(0)
dot: Regex[int] = Regex.dot().star()

regex = ~(dot + black_white + dot)
