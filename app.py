"""
app.py

Data4Impact Dashboard - an interactive Streamlit + Plotly dashboard for
exploring nonprofit program impact metrics: beneficiaries served, funding,
program performance, geographic reach, and target achievement.

Run:
    streamlit run app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Allow importing src/analysis.py regardless of the working directory the
# app is launched from.
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT / "src"))

from analysis import (  # noqa: E402
    beneficiaries_by_program,
    calculate_kpis,
    cost_efficiency,
    funding_distribution,
    funding_vs_expenses_by_program,
    generate_key_insights,
    geographic_impact,
    impact_over_time,
    load_data_from_db,
    success_rate_by_program,
    target_vs_actual,
)

DATABASE_PATH = PROJECT_ROOT / "database" / "data4impact.db"

st.set_page_config(
    page_title="Data4Impact Dashboard",
    page_icon="📊",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def get_data() -> pd.DataFrame:
    """Load the cleaned dataset from SQLite and cache it across reruns."""
    return load_data_from_db()


def format_currency(value: float) -> str:
    """Format a dollar amount as a compact, professional string, e.g.
    $2.4M, $850K, $1,200.
    """
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.1f}K"
    return f"${value:,.0f}"


def format_number(value: float) -> str:
    """Format a plain count with thousands separators."""
    return f"{value:,.0f}"


if not DATABASE_PATH.exists():
    st.error(
        "Database not found. Please run the following from the project "
        "root before launching the dashboard:\n\n"
        "```\npython src/generate_data.py\n"
        "python src/data_cleaning.py\n"
        "python src/database.py\n```"
    )
    st.stop()

df = get_data()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

st.sidebar.title("🔎 Filters")
st.sidebar.caption("Leave a filter empty to include all values.")

def reset_filters():
    """Reset all dashboard filters to their default 'All' state."""
    st.session_state["year_filter"] = []
    st.session_state["program_filter"] = []
    st.session_state["category_filter"] = []
    st.session_state["region_filter"] = []
    st.session_state["state_filter"] = []


st.sidebar.button(
    "Reset Filters",
    on_click=reset_filters,
    use_container_width=True,
)

years = sorted(df["year"].unique())
selected_years = st.sidebar.multiselect(
    "Year",
    options=years,
    placeholder="All years",
    key="year_filter",
)

programs = sorted(df["program_name"].unique())
selected_programs = st.sidebar.multiselect(
    "Program",
    options=programs,
    placeholder="All programs",
    key="program_filter",
)

categories = sorted(df["program_category"].unique())
selected_categories = st.sidebar.multiselect(
    "Program Category",
    options=categories,
    placeholder="All categories",
    key="category_filter",
)

regions = sorted(df["region"].unique())
selected_regions = st.sidebar.multiselect(
    "Region",
    options=regions,
    placeholder="All regions",
    key="region_filter",
)

# If specific regions are selected, only show states from those regions.
available_states = (
    sorted(df[df["region"].isin(selected_regions)]["state"].unique())
    if selected_regions
    else sorted(df["state"].unique())
)

selected_states = st.sidebar.multiselect(
    "State",
    options=available_states,
    placeholder="All states",
    key="state_filter",
)

# Start with the complete dataset.
filtered_df = df.copy()

# Apply a filter only when the user has selected one or more values.
if selected_years:
    filtered_df = filtered_df[filtered_df["year"].isin(selected_years)]

if selected_programs:
    filtered_df = filtered_df[
        filtered_df["program_name"].isin(selected_programs)
    ]

if selected_categories:
    filtered_df = filtered_df[
        filtered_df["program_category"].isin(selected_categories)
    ]

if selected_regions:
    filtered_df = filtered_df[
        filtered_df["region"].isin(selected_regions)
    ]

if selected_states:
    filtered_df = filtered_df[
        filtered_df["state"].isin(selected_states)
    ]

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("📊 Data4Impact Dashboard")
st.caption(
    "Interactive nonprofit impact analytics — beneficiaries, funding, program "
    "performance, and geographic reach. Dataset is synthetic and built for "
    "portfolio/demo purposes."
)

if filtered_df.empty:
    st.warning("No data matches the selected filters. Please adjust your filter selection.")
    st.stop()

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------

kpis = calculate_kpis(filtered_df)

# KPI row 1
kpi_row1 = st.columns(3)
kpi_row1[0].metric(
    "Total Beneficiaries Served",
    format_number(kpis["total_beneficiaries"]),
)
kpi_row1[1].metric(
    "Total Funding Received",
    format_currency(kpis["total_funding"]),
)
kpi_row1[2].metric(
    "Total Program Expenses",
    format_currency(kpis["total_expenses"]),
)

# KPI row 2
kpi_row2 = st.columns(3)
kpi_row2[0].metric(
    "Avg. Cost per Beneficiary",
    f"${kpis['avg_cost_per_beneficiary']:,.2f}",
)
kpi_row2[1].metric(
    "Overall Target Achievement",
    f"{kpis['overall_target_achievement']:.1f}%",
)
kpi_row2[2].metric(
    "Avg. Outcome Success Rate",
    f"{kpis['avg_outcome_success_rate']:.1f}%",
)

st.divider()

# ---------------------------------------------------------------------------
# Visualizations
# ---------------------------------------------------------------------------

row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.subheader("Beneficiaries by Program")
    data = beneficiaries_by_program(filtered_df)
    fig = px.bar(
        data,
        x="beneficiaries_served",
        y="program_name",
        orientation="h",
        labels={"beneficiaries_served": "Beneficiaries Served", "program_name": "Program"},
        text="beneficiaries_served",
        color="beneficiaries_served",
        color_continuous_scale="Blues",
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False, height=420)
    st.plotly_chart(fig, use_container_width=True)

with row1_col2:
    st.subheader("Funding vs. Expenses by Program")
    data = funding_vs_expenses_by_program(filtered_df)

    # Rename columns only for display in the chart.
    chart_data = data.rename(
        columns={
            "program_name": "Program",
            "funding_received": "Funding Received",
            "program_expenses": "Program Expenses",
        }
    )

    fig = px.bar(
        chart_data,
        x="Program",
        y=["Funding Received", "Program Expenses"],
        barmode="group",
        labels={
            "value": "Amount ($)",
            "variable": "Metric",
        },
    )

    fig.update_yaxes(
        tickprefix="$",
        tickformat=",.0f",
    )

    fig.update_xaxes(tickangle=-30)

    fig.update_layout(
        height=420,
        legend_title_text="",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.subheader("Impact Over Time")
    data = impact_over_time(filtered_df)
    fig = px.line(
        data,
        x="period",
        y="beneficiaries_served",
        markers=True,
        labels={"period": "Month", "beneficiaries_served": "Beneficiaries Served"},
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

with row2_col2:
    st.subheader("Program Success Rate")
    data = success_rate_by_program(filtered_df)
    fig = px.bar(
        data,
        x="program_name",
        y="outcome_success_rate",
        labels={"program_name": "Program", "outcome_success_rate": "Avg. Outcome Success Rate (%)"},
        color="outcome_success_rate",
        color_continuous_scale="Greens",
    )
    fig.update_yaxes(ticksuffix="%")
    fig.update_layout(coloraxis_showscale=False, height=420)
    st.plotly_chart(fig, use_container_width=True)

row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    st.subheader("Geographic Impact (by Region)")
    data = geographic_impact(filtered_df, level="region")
    fig = px.bar(
        data,
        x="region",
        y="beneficiaries_served",
        labels={"region": "Region", "beneficiaries_served": "Beneficiaries Served"},
        color="funding_received",
        color_continuous_scale="Purples",
        hover_data={"funding_received": ":$,.0f"},
    )
    fig.update_layout(height=420, coloraxis_colorbar_title="Funding ($)")
    st.plotly_chart(fig, use_container_width=True)

with row3_col2:
    st.subheader("Funding Distribution by Program")
    data = funding_distribution(filtered_df)

    fig = px.pie(
        data,
        names="program_name",
        values="funding_received",
        hole=0.45,
    )

    fig.update_traces(
        textinfo="percent",
        textposition="inside",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Funding: $%{value:,.0f}<br>"
            "Share: %{percent}"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=420,
        legend_title_text="Program",
        margin=dict(l=20, r=20, t=20, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

row4_col1, row4_col2 = st.columns(2)

with row4_col1:
    st.subheader("Target vs. Actual Beneficiaries")
    data = target_vs_actual(filtered_df)

    # Rename columns only for display in the chart.
    chart_data = data.rename(
        columns={
            "program_name": "Program",
            "target_beneficiaries": "Target Beneficiaries",
            "beneficiaries_served": "Beneficiaries Served",
        }
    )

    fig = px.bar(
        chart_data,
        x="Program",
        y=["Target Beneficiaries", "Beneficiaries Served"],
        barmode="group",
        labels={
            "value": "Beneficiaries",
            "variable": "Metric",
        },
    )

    fig.update_xaxes(tickangle=-30)

    fig.update_layout(
        height=420,
        legend_title_text="",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

with row4_col2:
    st.subheader("Cost Efficiency: Expenses vs. Beneficiaries Served")
    data = cost_efficiency(filtered_df)
    fig = px.scatter(
        data,
        x="program_expenses",
        y="beneficiaries_served",
        size="avg_cost_per_beneficiary",
        color="program_name",
        labels={
            "program_expenses": "Total Program Expenses ($)",
            "beneficiaries_served": "Beneficiaries Served",
            "avg_cost_per_beneficiary": "Avg. Cost / Beneficiary",
        },
        hover_data={"avg_cost_per_beneficiary": ":$,.2f"},
    )
    fig.update_xaxes(tickprefix="$", tickformat=",.0f")
    fig.update_layout(height=420, legend_title_text="Program")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Key insights
# ---------------------------------------------------------------------------

st.subheader("💡 Key Insights")
st.caption("Generated dynamically from the currently filtered data.")

insights = generate_key_insights(filtered_df)
if insights:
    for insight in insights:
        st.markdown(f"- {insight}")
else:
    st.info("Not enough data in the current filter selection to generate insights.")

with st.expander("View filtered data table"):
    st.dataframe(filtered_df, use_container_width=True)
