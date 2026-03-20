from aalpy_compro import Regex

alphabet = [0, 1]  # 0: 白, 1: 黒

black_white = Regex.symbol(1) + Regex.symbol(0)
dot_star: Regex[int] = Regex.dot().star()

regex = ~(dot_star + black_white + dot_star)
