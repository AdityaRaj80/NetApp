import os, time, requests, pandas as pd
import streamlit as st
import plotly.express as px

# ---- Page + sidebar controls (no rerun here) ----
st.set_page_config(page_title="NetApp Data-in-Motion", layout="wide")
st.sidebar.header("⚙️ Live Settings")
auto_refresh = st.sidebar.checkbox("Auto-refresh dashboard", value=True)
refresh_rate = st.sidebar.slider("Refresh every (seconds)", 1, 10, 3)

# API discovery (unchanged)
def _try_json(url, timeout=2.5):
    try:
        r = requests.get(url, timeout=timeout)
        if r.ok: return r.json()
    except Exception:
        pass
    return None

def _discover_api():
    env = os.getenv("STREAM_API")
    candidates = []
    if env: candidates.append(env.rstrip("/"))
    candidates += ["http://stream-api:8001","http://localhost:8001","http://127.0.0.1:8001","http://host.docker.internal:8001"]
    seen = set()
    for base in candidates:
        if base in seen: continue
        seen.add(base)
        js = _try_json(f"{base}/health")
        if js and isinstance(js, dict) and js.get("ok"):
            return base
    return candidates[0]

API = _discover_api()
st.title("📊 NetApp Data-in-Motion — Live Ops")


tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Kafka", "ML Insights", "Actions", "Buckets"])

@st.cache_data(ttl=2.0)
def fetch_health():
    r = requests.get(f"{API}/health", timeout=3); r.raise_for_status()
    return r.json()

@st.cache_data(ttl=1.0)
def fetch_metrics():
    r = requests.get(f"{API}/metrics", timeout=3); r.raise_for_status()
    return r.json()

@st.cache_data(ttl=1.0)
def fetch_peek(n=100):
    r = requests.get(f"{API}/stream/peek?n={n}", timeout=3); r.raise_for_status()
    return r.json()

@st.cache_data(ttl=1.0)
def fetch_actions(n=100):
    r = requests.get(f"{API}/actions?n={n}", timeout=3); r.raise_for_status()
    return r.json()
    
@st.cache_data(ttl=1.0)
def fetch_tiers():
    r = requests.get(f"{API}/tiers", timeout=3); r.raise_for_status()
    return r.json()

@st.cache_data(ttl=1.0)
def fetch_tiers_series():
    r = requests.get(f"{API}/tiers/series", timeout=3); r.raise_for_status()
    return r.json()


with tab1:
    h = fetch_health()
    m = fetch_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Events (total)", m["events_total"])
    c2.metric("Active Devices", m["devices"])
    c3.metric("Anomaly Rate (recent)", f"{m['anomaly_rate_recent']*100:.1f}%")
    c4.metric("Current Minute Count", h["cur_min_count"])

    tp = m["throughput_per_min"]
    if tp:
        df_tp = pd.DataFrame(tp, columns=["minute", "count"])
        fig = px.bar(df_tp, x="minute", y="count", title="Events per Minute")
        st.plotly_chart(fig, use_container_width=True)

    df = pd.DataFrame(fetch_peek(200))
    if len(df):
        df["t"] = pd.to_datetime(df["ts"], unit="s")
        fig2 = px.line(df.sort_values("t"), x="t", y="temperature", color="device_id", title="Temperature by Device (recent)")
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(df[["t","device_id","temperature","z_temp","is_anomaly","bytes"]].tail(50), use_container_width=True)

with tab2:
    st.subheader("Kafka Health (derived)")
    st.write("Throughput is computed by the consumer and aggregated per minute by the API.")
    m = fetch_metrics()
    tp = m["throughput_per_min"]
    if tp:
        df_tp = pd.DataFrame(tp, columns=["minute","count"])
        fig3 = px.area(df_tp, x="minute", y="count", title="Kafka Throughput (events/min)")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No throughput yet — wait a few seconds after starting the stack.")

with tab3:
    st.subheader("ML Insights — Rolling Z-score")
    df = pd.DataFrame(fetch_peek(300))
    if len(df):
        df["t"] = pd.to_datetime(df["ts"], unit="s")
        fig4 = px.scatter(df, x="t", y="z_temp", color=df["is_anomaly"].map({True:"anomaly", False:"normal"}), title="Z-score vs Time")
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(df[["t","device_id","temperature","z_temp","is_anomaly"]].tail(50), use_container_width=True)
    st.caption("Tip: toggle USE_ISOFOREST=true in the backend later if you add a batch model.")

with tab4:
    acts = fetch_actions(100)
    if acts:
        df_a = pd.DataFrame(acts)
        df_a["t"] = pd.to_datetime(df_a["ts"], unit="s")
        st.dataframe(df_a[["t", "type"]], use_container_width=True)
    else:
        st.info("No actions yet.")
    # 🔄 Force page to reload at interval

with tab5:
    st.subheader("Tier Buckets — Hot / Warm / Cold")

    snap = fetch_tiers()
    scols = st.columns(4)
    scols[0].metric("Devices (total)", snap.get("devices", 0))
    scols[1].metric("Hot", snap.get("hot", 0))
    scols[2].metric("Warm", snap.get("warm", 0))
    scols[3].metric("Cold", snap.get("cold", 0))

    # Donut snapshot
    s_df = pd.DataFrame(
        [{"tier":"hot","count":snap.get("hot",0)},
         {"tier":"warm","count":snap.get("warm",0)},
         {"tier":"cold","count":snap.get("cold",0)}]
    )
    figd = px.pie(s_df, values="count", names="tier", hole=0.5, title="Current Tier Snapshot")
    st.plotly_chart(figd, use_container_width=True)

    # Stacked per-minute series
    ts = fetch_tiers_series()
    if ts:
        tdf = pd.DataFrame(ts).sort_values("minute")
        tdf["minute"] = tdf["minute"].astype(int)
        figstack = px.bar(
            tdf, x="minute",
            y=["hot","warm","cold"],
            title="Tier counts per minute (stacked)",
            barmode="stack"
        )
        st.plotly_chart(figstack, use_container_width=True)
    else:
        st.info("No tier data yet — wait for a few events to arrive.")

import time as _t
if auto_refresh:
    _t.sleep(refresh_rate)
    st.rerun()



