import math
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import streamlit as st
import plotly.express as px


from functions import (
    get_active_sessions_over_time,
    get_max_active_sessions,
    get_sales_by_dimension,
    get_sales_by_product,
    get_sales_value_by_product
)

def render_active_sessions_chart(events_df):
    active_sessions_df = get_active_sessions_over_time(events_df)
    max_active_sessions = get_max_active_sessions(events_df)

    if active_sessions_df.empty:
        st.info("No data available")
        return

    min_time = active_sessions_df["event_time"].min().floor("15min")
    max_time = active_sessions_df["event_time"].max().ceil("15min")

    max_y = max_active_sessions + 1
    y_step = math.ceil(max_y / 5)
    y_ticks = list(range(0, max_y + y_step, y_step))

    total_minutes = (max_time - min_time).total_seconds() / 60

    max_x_ticks = 15

    raw_interval = math.ceil(total_minutes / max_x_ticks)

    possible_intervals = [
        15,
        30,
        60,
        120,
        180,
        240,
        360,
        720
    ]

    x_interval_minutes = next(
        (
            interval
            for interval in possible_intervals
            if interval >= raw_interval
        ),
        720
    )

    fig, ax = plt.subplots(
        figsize=(10, 3),
        facecolor="none"
    )

    ax.set_facecolor("none")

    ax.plot(
        active_sessions_df["event_time"],
        active_sessions_df["active_sessions"],
        linewidth=2,
        color="lightskyblue"
    )

    ax.set_title(
        "Active sessions over time",
        color="white"
    )

    ax.set_xlabel(
        "Event time",
        color="white"
    )

    ax.set_ylabel(
        "Active sessions",
        color="white"
    )

    ax.set_xlim(
        min_time,
        max_time
    )

    ax.set_ylim(
        0,
        max_y
    )

    ax.set_yticks(
        y_ticks
    )

    ax.tick_params(
        axis="both",
        colors="white"
    )

    for spine in ax.spines.values():
        spine.set_color("white")

    if x_interval_minutes < 60:
        ax.xaxis.set_major_locator(
            mdates.MinuteLocator(interval=x_interval_minutes)
        )
    else:
        ax.xaxis.set_major_locator(
            mdates.HourLocator(interval=x_interval_minutes // 60)
        )

    if total_minutes <= 24 * 60:
        ax.xaxis.set_major_formatter(
            mdates.DateFormatter("%H:%M")
        )
    else:
        ax.xaxis.set_major_formatter(
            mdates.DateFormatter("%d.%m %H:%M")
        )

    ax.grid(
        True,
        axis="y",
        alpha=0.25,
        color="white"
    )

    fig.autofmt_xdate()

    st.pyplot(
        fig,
        transparent=True
    )

    plt.close(fig)


def render_sales_dimension_treemap(events_df, dimension, title, state_key):

    st.markdown(f"#### Sales by {title}")
    
    if events_df.empty:
        st.info("No data available")
        return None

    sales_by_dimension_df = get_sales_by_dimension(events_df,dimension)

    if sales_by_dimension_df.empty:
        st.info("No data available")
        return None

    if state_key not in st.session_state:
        st.session_state[state_key] = None

    fig = px.treemap(
        sales_by_dimension_df,
        path=[dimension],
        values="sales_value",
        custom_data=["products_sold"]
    )

    fig.update_traces(
        texttemplate="%{label}<br>$%{value:,.2f}<br>%{customdata[0]}",
        hovertemplate="%{label}<br>$%{value:,.2f}<br>%{customdata[0]}<extra></extra>"
    )

    fig.update_layout(
        margin=dict(
            t=10,
            l=10,
            r=10,
            b=10
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color="white"
        )
    )

    selected = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode="points",
        key=f"{state_key}_treemap"
    )

    if selected and selected.selection.points:

        point = selected.selection.points[0]

        clicked_value = (
            point.get("label")
            or point.get("id")
        )

        current_path = point.get("current_path")

        if current_path is None:
            st.session_state[state_key] = None
        else:
            st.session_state[state_key] = clicked_value

    st.write(f"Selected {title}:", st.session_state[state_key] or "—")

    return st.session_state[state_key]


def render_sales_product_bar_chart(events_df, dimension, selection=None, require_selection = False):

    st.markdown("#### Sales by product")
    
    if require_selection and selection==None:
        st.info("Select filter to display")
        return
        
    sales_by_product_df = get_sales_by_product(
        events_df,
        dimension,
        selection
    )

    if sales_by_product_df.empty:
        st.info("No data available")
        return

    plot_df = (
        sales_by_product_df
        .sort_values(
            "products_sold",
            ascending=True
        )
        .tail(15)
        .copy()
    )

    plot_df["product_label"] = (
        plot_df["product_name"]
        + " (id: "
        + plot_df["product_id"].astype(str)
        + ")"
    )

    fig = px.bar(
        plot_df,
        x="products_sold",
        y="product_label",
        orientation="h",
        text="products_sold"
    )

    fig.update_traces(
        marker_color="lightskyblue",
        textposition="outside",
        hovertemplate="<extra></extra>"
    )

    fig.update_layout(
        height=620,
        showlegend=False,
        margin=dict(
            t=10,
            l=30,
            r=60,
            b=10
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color="white"
        ),
        xaxis_title=None,
        yaxis_title=None
    )

    max_value = plot_df["products_sold"].max()

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.15)",
        color="white",
        range=[0, max_value + 1],
        dtick=1
    )

    fig.update_yaxes(
        color="white"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"sales_product_{dimension}",
        config={
            "displayModeBar": False,
            "staticPlot": True
        }
    )


def render_sales_value_bar_chart(events_df, dimension, selection=None, require_selection = False):

    st.markdown("#### Sales by value")
    if require_selection and selection==None:
        st.info("Select filter to display")
        return

    sales_value_df = get_sales_value_by_product(
        events_df,
        dimension,
        selection
    )


    if sales_value_df.empty:
        st.info("No data available")
        return

    plot_df = (
        sales_value_df
        .sort_values(
            "sales_value",
            ascending=True
        )
        .tail(15)
        .copy()
    )

    plot_df["product_label"] = (
        plot_df["product_name"]
        + " (id: "
        + plot_df["product_id"].astype(str)
        + ")"
    )

    fig = px.bar(
        plot_df,
        x="sales_value",
        y="product_label",
        orientation="h"
    )

    max_value = plot_df["sales_value"].max()
    
    fig.update_traces(
        marker_color="lightskyblue",
        text=plot_df["sales_value"].round(2),
        textposition="outside",
        texttemplate="$%{text:,.2f}",
        cliponaxis=False,
        hovertemplate="<extra></extra>"
    )

    fig.update_layout(
        height=620,
        showlegend=False,
        margin=dict(
            t=10,
            l=30,
            r=120,
            b=10
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color="white"
        ),
        xaxis_title=None,
        yaxis_title=None
    )

    max_value = sales_value_df["sales_value"].max()
    max_value = plot_df["sales_value"].max()
    raw_step = max_value / 6
    magnitude = 10 ** math.floor(math.log10(raw_step))
    
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.15)",
        color="white",
        range=[
            0,
            max_value * 1.25
        ],
        dtick = math.ceil(raw_step / magnitude) * magnitude
    )

    fig.update_yaxes(
        color="white"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"sales_values_{dimension}",
        config={
            "displayModeBar": False,
            "staticPlot": True
        }
    )