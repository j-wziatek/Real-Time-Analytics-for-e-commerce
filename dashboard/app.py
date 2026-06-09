import streamlit as st
from streamlit_autorefresh import st_autorefresh

from spark import (
    get_peak_session_starts,
    get_peak_active_sessions
)

from functions import (
    get_events_df,
    get_latest_event,
    get_active_sessions,
    get_finished_sessions,
    get_max_active_sessions,
    get_active_sessions_over_time,
    get_sales_kpis,
    get_recommendation_kpis,
    get_association_rules_by_category,
    get_recommendation_product_stats
)

from charts import (
    render_active_sessions_chart,
    render_sales_dimension_treemap,
    render_sales_product_bar_chart,
    render_sales_value_bar_chart
)


st.set_page_config(
    page_title="Shop statistics",
    layout="wide"
)


if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False


col_title, col_nav, col_buttons = st.columns([4, 3, 2])

with col_title:
    st.title("Shop statistics")

with col_nav:
    page = st.radio(
        "",
        [
            "Overview",
            "Sales",
            "Recommendations",
            "Events"
        ],
        horizontal=True,
        label_visibility="collapsed"
    )

with col_buttons:
    col_auto, col_refresh = st.columns(2)

    with col_auto:
        st.toggle(
            "Auto refresh",
            key="auto_refresh"
        )

    with col_refresh:
        if st.button("Refresh"):
            st.rerun()

st.divider()


if st.session_state.auto_refresh:
    st_autorefresh(
        interval=1000,
        key="dashboard_refresh"
    )


events_df = get_events_df()
latest_event = get_latest_event()
active_sessions = get_active_sessions()
max_active_sessions = get_max_active_sessions(events_df)
finished_sessions = get_finished_sessions()

if page == "Overview":

    st.header("Overview")

    st.subheader("Active sessions")
    overview_active_col, overview_max_col, overview_finished_col = st.columns(3)

    with overview_active_col:
        st.metric("Active sessions",active_sessions)
    with overview_max_col:
        st.metric("Max active sessions", max_active_sessions)
    with overview_finished_col:
        st.metric("Finished sessions", finished_sessions)

    render_active_sessions_chart(events_df)
    

    st.subheader("Peak sessions")
    
    window_label = st.selectbox(
        "Time window",
        ["15 min", "30 min", "1 h"]
    )
    
    window_minutes = {
        "15 min": 15,
        "30 min": 30,
        "1 h": 60
    }[window_label]
    
    peak_starts = get_peak_session_starts(events_df, window_minutes)
    active_sessions_df = get_active_sessions_over_time(events_df)
    
    peak_active = get_peak_active_sessions(active_sessions_df,window_minutes)
    
    overview_peak_starts, overview_peak_active = st.columns(2)
    
    with overview_peak_starts:
    
        if peak_starts is None:
            st.info("No data available")
        else:
            st.metric("Peak Session Starts", peak_starts["session_starts"])
            st.caption(
                f"{peak_starts['window_start'].strftime('%d.%m %H:%M')} - "
                f"{peak_starts['window_end'].strftime('%d.%m %H:%M')}"
            )
    
    with overview_peak_active:
    
        if peak_active is None or peak_active["active_sessions"]==0:
            st.info("No data available")
        else:
            st.metric("Peak Active Sessions", peak_active["active_sessions"])
            st.caption(
                f"{peak_active['window_start'].strftime('%d.%m %H:%M')} - "
                f"{peak_active['window_end'].strftime('%d.%m %H:%M')}"
            )

elif page == "Sales":

    st.header("Sales")
    st.subheader("KPIs")
    sales_kpis = get_sales_kpis(events_df)

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(
            "Finalized transactions",
            sales_kpis["finished_transactions"]
        )
    
    with col2:
        st.metric(
            "Purchase rate",
            f"{sales_kpis['purchase_rate']}%"
        )
    
    with col3:
        st.metric(
            "Sales value",
            f"${sales_kpis['sales_value']:,.2f}"
        )
    
    with col4:
        st.metric(
            "Products sold",
            sales_kpis["products_sold"]
        )
    
    with col5:
        st.metric(
            "Profit",
            f"${sales_kpis['profit']:,.2f}"
        )
    
    with col6:
        st.metric(
            "Avg margin (%)",
            f"{sales_kpis['avg_margin_pct']}%"
        )

    st.subheader("All sales")
    chart_col1, chart_col2, chart_col3 = st.columns(3)

    
    with chart_col1:
        selected_category = render_sales_dimension_treemap(
                events_df,
                dimension="category_name",
                title="category",
                state_key="selected_category"
            )
    
    with chart_col2:
        render_sales_product_bar_chart(
            events_df,
            dimension="category_name",
            selection=selected_category
        )
    
    with chart_col3:
        render_sales_value_bar_chart(
            events_df,
            dimension="category_name",
            selection=selected_category)

    st.subheader("Brand sales")
    chart_brand_tree, chart_brand_products, chart_brand_value = st.columns(3)

    
    with chart_brand_tree:
        selected_brand = render_sales_dimension_treemap(
                events_df,
                dimension="brand",
                title="brand",
                state_key="selected_brand"
            )
    
    with chart_brand_products:
        render_sales_product_bar_chart(
            events_df,
            dimension="brand",
            selection=selected_brand,
            require_selection = True
        )
    
    with chart_brand_value:
        render_sales_value_bar_chart(
            events_df,
            dimension="brand",
            selection=selected_brand,
            require_selection = True
        )


elif page == "Recommendations":

    st.header("Recommendations")
    st.subheader("KPIs")

    recommendation_kpis = get_recommendation_kpis(events_df)

    rec_shown_col, rec_accepted_col, rec_rate_col, rec_value_col, rec_profit_col, rec_popular_col = st.columns(6)

    with rec_shown_col:
        st.metric(
            "Recommendations shown",
            recommendation_kpis["recommendations_shown"]
        )

    with rec_accepted_col:
        st.metric(
            "Recommendations accepted",
            recommendation_kpis["recommendations_accepted"]
        )

    with rec_rate_col:
        st.metric(
            "Acceptance rate",
            f"{recommendation_kpis['acceptance_rate']:.2f}%"
        )

    with rec_value_col:
        st.metric(
            "Sales value",
            f"${recommendation_kpis['sales_value']:,.2f}"
        )

    with rec_profit_col:
        st.metric(
            "Profit",
            f"${recommendation_kpis['profit']:,.2f}"
        )

    with rec_popular_col:
        st.metric(
            "Most popular product type",
            recommendation_kpis["most_popular_product_type"]
        )

    st.subheader("All recommendations")
    st.dataframe(
        get_recommendation_product_stats(events_df),
        use_container_width=True,
        hide_index=True
    )
    
    st.subheader("Association rules")

    rules_df = get_association_rules_by_category()

    if rules_df.empty:
        st.info("No data available")
    else:
        categories = (
            rules_df["category_name"]
            .dropna()
            .sort_values()
            .unique()
            .tolist()
        )

        cols = st.columns(len(categories))

        for col, category_name in zip(cols, categories):

            with col:
            
                st.markdown(
                    f"""
                    <div style="
                        font-size:18px;
                        font-weight:bold;
                        margin-bottom:6px;
                    ">
                        {category_name}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
                category_rules_df = rules_df[rules_df["category_name"] == category_name
                ].sort_values(
                    "confidence",
                    ascending=False
                )
            
                for _, rule in category_rules_df.iterrows():
            
                    st.markdown(
                        f"""
                        <div style="
                            font-size:14px;
                            line-height:1.3;
                            margin-bottom:5px;
                        ">
                            <b>{rule["rule_text"]}</b><br>
                            conf: {rule["confidence"]:.2f}<br>
                            lift: {rule["lift"]:.2f}
                        </div>
            
                        <hr style="
                            margin-top:2px;
                            margin-bottom:2px;
                            border:0;
                            border-top:1px solid rgba(255,255,255,0.15);
                        ">
                        """,
                        unsafe_allow_html=True
                    )

elif page == "Events":

    st.header("Events")

    if events_df.empty:
        st.info("No data available")
    else:
        events_latest_col, events_all_col = st.columns([1, 2])
        
        with events_latest_col:
            st.subheader("Latest event")
            st.json(latest_event)

        with events_all_col:
            st.subheader("All events")
            st.dataframe(
                events_df,
                use_container_width=True
            )