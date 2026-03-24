import math
import os
import re

import numpy as np
import pandas as pd
import pykakasi


def to_roman_str(ja_str):
    """日本語をローマ字に変換する"""
    kakasi = pykakasi.kakasi()
    converted = kakasi.convert(ja_str)
    roman_str = "".join([i["passport"] for i in converted])
    return roman_str


def parse_log_file(file_path, obj_priority_dic):
    with open(file_path, "r") as file:
        lines = file.readlines()

    max_priority = int(max(list(obj_priority_dic.values())))
    dic_priority_obj_name = {}
    for priority in range(1, max_priority + 1):
        keys = [k for k, v in obj_priority_dic.items() if v == priority]
        if keys:
            dic_priority_obj_name[priority] = ", ".join(keys)
    num_objective = len(dic_priority_obj_name)
    data = []
    candidate_id = 1
    for line in lines:
        if re.match(r"\[\s*\d+ sec,.\s*(\d+) itr\]", line):
            template = (
                r"\[\s*(\d+) sec,.\s*(\d+) itr\]:"
                + r"\s*([-+]?\d*\.?\d+(?:e[-+]?\d+)?)\s*\|" * (num_objective - 1)
                + r"\s*([-+]?\d*\.?\d+(?:e[-+]?\d+)?)"
            )
            match = re.search(template, line)
            if match:
                time_sec = int(match.group(1))
                iteration = int(match.group(2))
                vales = []
                for i in range(num_objective):
                    vales.append(float(match.group(i + 3)))
                data.append((candidate_id, time_sec, iteration, *vales))
            else:
                match = re.match(r"\[\s*(\d+) sec,.\s*(\d+) itr\]:", line)
                time_sec = int(match.group(1))
                iteration = int(match.group(2))
                data.append((candidate_id, time_sec, iteration, *([None] * num_objective)))
        elif re.match(r"^\d+ iterations performed in \d+ seconds", line):
            candidate_id += 1
    columns = ["candidate", "time", "iteration"] + list(dic_priority_obj_name.values())
    log_df = pd.DataFrame(data, columns=columns).drop_duplicates()
    return log_df


def roman_sort_key(s):
    """五十音とアルファベット順にソートする関数"""
    # 五十音順＋アルファベット順の順序を定義
    kakasi = pykakasi.kakasi()
    sort_order = "aiueokstnhmyrw"
    order_dict = {char: idx for idx, char in enumerate(sort_order)}

    # 漢字をローマ字に変換
    result = kakasi.convert(s)

    # ローマ字を取得（変換できない場合はそのままの文字列を使用）
    reading = result[0]["passport"] if result else s

    # ローマ字をソートキーに変換
    return [order_dict.get(char, float("inf")) for char in reading]

