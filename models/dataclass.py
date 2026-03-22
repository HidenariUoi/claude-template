"""最適化への入出力データの境界条件を定義
"""
from pydantic import BaseModel


class OptimizeInputData(BaseModel):
    """最適化入力クラス
    """


class OptimizeOutputData(BaseModel):
    """最適化出力クラス
    """