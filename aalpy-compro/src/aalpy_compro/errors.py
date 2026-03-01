class LearningError(Exception):
    """
    オートマトン学習の途中で発生するエラーの基底クラス
    """


class ConstraintViolationError(LearningError, ValueError):
    """
    学習結果のオートマトンが
    指定された制約に違反している場合に
    送出されるエラー
    """

    def __init__(
        self,
        *,
        constraint: str,  # 制約の種類の説明
        required: str,  # 制約の文字列による説明
        actual: object,  # 実際に得られた値
        details: str | None = None,
    ):
        self.constraint = constraint
        self.required = required
        self.actual = actual

        msg = f"Constraint violated: {constraint}. Required: {required}. Actual: {actual!r}"
        if details:
            msg += f". Details: {details}"
        super().__init__(msg)
