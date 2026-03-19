from aalpy_compro import Regex

alphabet = ["B", "Y", "K"]

B_plus = Regex.symbol("B").plus()
Y_plus = Regex.symbol("Y").plus()
K_plus = Regex.symbol("K").plus()

BYK = B_plus + Y_plus + K_plus
KYB = K_plus + Y_plus + B_plus

regex = BYK | KYB
