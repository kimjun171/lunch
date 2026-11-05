import re
from collections import Counter
from itertools import combinations

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="급식 연관 규칙 분석기", layout="wide")

# 1. 데이터 로드 및 전처리
DATA_URL = "https://raw.githubusercontent.com/it-teacher-go/data-share-/main/songtan_meals_184.csv"


@st.cache_data
def load_and_process_data(url):
    df = pd.read_csv(url, encoding="utf-8")

    transactions = []
    all_items = set()

    for raw_menu in df["메뉴"].dropna():
        if not isinstance(raw_menu, str):
            continue
        # 괄호 및 괄호 안 내용 제거
        cleaned_text = re.sub(r"\(.*?\)", "", raw_menu)
        # 세로줄(|) 기준으로 메뉴 분리 및 공백 제거
        items = list(
            set([item.strip() for item in cleaned_text.split("|") if item.strip()])
        )

        if items:
            transactions.append(items)
            all_items.update(items)

    return df, transactions, sorted(list(all_items))


df, transactions, unique_items = load_and_process_data(DATA_URL)
total_days = len(transactions)
num_unique_items = len(unique_items)

# 2. 연관 규칙 및 동시 0일(함께 나온 적 없는 짝) 산출
item_counts = Counter()
pair_counts = Counter()

for tx in transactions:
    for item in tx:
        item_counts[item] += 1
    for p1, p2 in combinations(sorted(tx), 2):
        pair_counts[(p1, p2)] += 1

rules = []
# 전체 메뉴 쌍(combinations)에 대해 동시 출현 횟수를 파악 (동시 0회 포함)
for item_a, item_b in combinations(unique_items, 2):
    count_ab = pair_counts[(item_a, item_b)]
    supp_ab = count_ab / total_days
    supp_a = item_counts[item_a] / total_days
    supp_b = item_counts[item_b] / total_days

    # Direction 1: A -> B
    conf_a_b = count_ab / item_counts[item_a] if item_counts[item_a] > 0 else 0
    lift_a_b = conf_a_b / supp_b if supp_b > 0 else 0
    rules.append(
        {
            "조건": item_a,
            "결과":
