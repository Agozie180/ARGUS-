"""Demo Mode — the six built-in scenarios and the signature WOW moment."""
import argus_client as ac
import streamlit as st

from dashboard import components as ui
from render import render_analysis

st.set_page_config(page_title="Demo Mode — Argus", page_icon="🎬", layout="wide")
ui.inject_theme()
st.markdown("# 🎬 Demo Mode")
st.caption("Deterministic scenarios that show how Argus thinks — including the moment most bots get wrong.")

argus = ac.get_argus()

st.markdown("### ⭐ The WOW moment")
st.write(ac.WOW_NARRATIVE)
if st.button("Run the WOW moment", type="primary"):
    res = argus.wow_moment(mode=ac.Mode.PROFESSIONAL)
    render_analysis(res)

st.divider()
st.markdown("### Scenario library")
labels = {k: f"{k} — {v['name']}" for k, v in ac.SCENARIOS.items()}
choice = st.selectbox("Choose a scenario", list(ac.SCENARIOS.keys()),
                      format_func=lambda k: labels[k])
mode_label = st.radio("Explain mode", ["Professional", "Beginner"], horizontal=True)

meta = ac.SCENARIOS[choice]
st.info(f"**{meta['name']}** — teaches: {meta['teaches']}")
res = argus.demo(choice, mode=ac.mode_from_label(mode_label))
render_analysis(res)
