"""最適化の入出力データクラスを定義するモジュール
"""
import datetime
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel


class OptimizeInputData(BaseModel):
    """最適化のための入力クラス
    """


class OptimizeOutputData(BaseModel):
    """最適化の出力クラス
    """
