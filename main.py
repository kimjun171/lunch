import re
from collections import Counter, defaultdict
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

# 2. 연관 규칙 산출 (단일 아이템 지지도 및 쌍 빈도 측정)
item_counts = Counter()
pair_counts = Counter()

for tx in transactions:
    for item in tx:
        item_counts[item] += 1
    for p1, p2 in combinations(sorted(tx), 2):
        pair_counts[(p1, p2)] += 1

rules = []
for (item_a, item_b), count_ab in pair_counts.items():
    supp_ab = count_ab / total_days
    supp_a = item_counts[item_a] / total_days
    supp_b = item_counts[item_b] / total_days

    # Direction 1: A -> B
    conf_a_b = count_ab / item_counts[item_a]
    lift_a_b = conf_a_b / supp_b if supp_b > 0 else 0
    rules.append(
        {
            "조건": item_a,
            "결과": item_b,
            "동시": count_ab,
            "지지도": supp_ab,
            "신뢰도": conf_a_b,
            "향상도": lift_a_b,
        }
    )

    # Direction 2: B -> A
    conf_b_a = count_ab / item_counts[item_b]
    lift_b_a = conf_b_a / supp_a if supp_a > 0 else 0
    rules.append(
        {
            "조건": item_b,
            "결과": item_a,
            "동시": count_ab,
            "지지도": supp_b_a if "supp_b_a" in locals() else supp_ab,
            "신뢰도": conf_b_a,
            "향상도": lift_b_a,
        }
    )

rules_df = pd.DataFrame(rules)

# UI 구성
st.title("🍽️ 송탄고 급식 메뉴 연관 규칙 분석기")

# 메인 UI 상단 컨트롤
col_filter, col_sort = st.columns([2, 1])

with col_filter:
    selected_menu = st.selectbox(
        "메뉴 선택 (선택한 메뉴가 포함된 규칙만 검색):",
        options=["전체"] + unique_items,
    )

with col_sort:
    sort_option = st.selectbox(
        "정렬 기준:", options=["향상도", "신뢰도", "동시"]
    )

# 데이터 필터링
if selected_menu != "전체":
    filtered_df = rules_df[
        (rules_df["조건"] == selected_menu)
        | (rules_df["결과"] == selected_menu)
    ].copy()
else:
    filtered_df = rules_df.copy()

# 정렬 수행
filtered_df = filtered_df.sort_values(by=sort_option, ascending=False).reset_index(
    drop=True
)

# 메트릭 표시 (급식 일수, 메뉴 종류 수, 함께 나온 적이 있는 메뉴 쌍의 수)
unique_pairs_count = len(pair_counts)
st.write(
    f"**급식 일수:** {total_days}일 | **메뉴 종류 수:** {num_unique_items}개 | **함께 나온 메뉴 쌍 수:** {unique_pairs_count}개"
)

# 상위 10개 향상도 그래프
st.subheader("📊 향상도 상위 10개 규칙")
top10_df = filtered_df.sort_values(by="향상도", ascending=False).head(10)

if not top10_df.empty:
    top10_df["규칙"] = top10_df["조건"] + " ➔ " + top10_df["결과"]
    fig = px.bar(
        top10_df.sort_values(by="향상도", ascending=True),
        x="향상도",
        y="규칙",
        orientation="h",
        text=top10_df.sort_values(by="향상도", ascending=True)["향상도"].apply(
            lambda x: f"{x:.2f}"
        ),
        title="향상도(Lift) Top 10",
    )
    fig.update_layout(xaxis_title="향상도", yaxis_title="규칙", height=400)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("조건에 해당하는 규칙이 없습니다.")

# 연관 규칙 표 출력
st.subheader("📋 연관 규칙 결과 표")
st.dataframe(
    filtered_df.style.format(
        {"지지도": "{:.4f}", "신뢰도": "{:.4f}", "향상도": "{:.4f}"}
    ),
    use_container_width=True,
)
