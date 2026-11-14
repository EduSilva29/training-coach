import streamlit as st
import datetime
from db import (
    get_chat_history,
    clear_chat_history,
    get_athlete_profile,
    update_athlete_profile,
    get_latest_recovery,
)
from coach import ask_coach

# 1. Page Configuration
st.set_page_config(
    page_title="AI Endurance Coach",
    page_icon="🏃",
    layout="wide"
)

# 2. Sidebar: Biometrics & Athlete Profile
with st.sidebar:
    st.title("🏃 Coach's Corner")
    
    # Section A: Today's Biometric Recovery
    st.subheader("📊 Today's Readiness")
    recovery = get_latest_recovery()
    
    if recovery:
        sleep = recovery.get("sleep", {})
        hrv = recovery.get("hrv", {})
        bio = recovery.get("biometrics", {})

        col1, col2 = st.columns(2)
        with col1:
            sleep_score = sleep.get("sleep_score")
            st.metric("Sleep Score", f"{sleep_score}/100" if sleep_score else "N/A")
            st.metric("Resting HR", f"{bio.get('resting_hr', 'N/A')} bpm")
        with col2:
            st.metric("HRV Status", hrv.get("hrv_status", "N/A"))
            st.metric("Sleep Hours", f"{sleep.get('sleep_duration_hours', 'N/A')}h")

        st.caption(f"Last synced for: **{recovery.get('calendar_date', 'Unknown')}**")
    else:
        st.info("No recovery data found yet. Run `python sync/sync_recovery.py` to fetch your metrics.")

    st.divider()

    # Section B: Athlete Objectives & Injury Tracking
    st.subheader("🎯 Athlete Goals & Status")
    current_profile = get_athlete_profile()

    with st.form("profile_form"):
        goal = st.text_input("Primary Goal", value=current_profile.get("goal", ""))
        races = st.text_input("Target Races", value=current_profile.get("target_races", ""))
        
        # Personal Bests section
        st.markdown("**⚡ Personal Bests (PRs)**")
        pbs = current_profile.get("personal_bests", {})
        pb_col1, pb_col2 = st.columns(2)
        with pb_col1:
            pb_5k = st.text_input("5K", value=pbs.get("5k", ""), placeholder="e.g. 21:30")
            pb_10k = st.text_input("10K", value=pbs.get("10k", ""), placeholder="e.g. 44:50")
        with pb_col2:
            pb_hm = st.text_input("Half Marathon", value=pbs.get("half_marathon", ""), placeholder="e.g. 1:40:00")
            pb_marathon = st.text_input("Marathon", value=pbs.get("marathon", ""), placeholder="e.g. 3:35:00")

        injuries = st.text_area("Aches / Injuries / Fatigue", value=current_profile.get("injuries_and_aches", ""), height=80)
        preferences = st.text_area("Preferences / Constraints", value=current_profile.get("preferences", ""), height=80)
        
        submitted = st.form_submit_button("💾 Save Profile")
        if submitted:
            updated = {
                "goal": goal,
                "target_races": races,
                "personal_bests": {
                    "5k": pb_5k,
                    "10k": pb_10k,
                    "half_marathon": pb_hm,
                    "marathon": pb_marathon
                },
                "injuries_and_aches": injuries,
                "preferences": preferences
            }
            update_athlete_profile(updated)
            st.success("Coach notes updated!")

    st.divider()

    # Section C: Chat Controls
    if st.button("🗑️ Clear Chat History"):
        clear_chat_history()
        st.session_state.messages = []
        st.rerun()

# 3. Main Area: Chat Interface
st.title("💬 Chat with Your Coach")
st.caption("Powered by Garmin Connect Biometrics + Google Gemini Flash (100% Free)")

# Load persistent conversation history from MongoDB
db_messages = get_chat_history(limit=50)

# If no messages in DB, display a welcoming prompt
if not db_messages:
    db_messages = [{
        "role": "assistant",
        "content": "👋 Hey! I'm your AI Training Coach. I have your recent Garmin workouts and recovery data loaded. What are we planning today?"
    }]

# Render all messages
for msg in db_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Chat Input Box
if user_prompt := st.chat_input("Ask your coach (e.g., 'What should my workout be today?' or 'How is my weekly mileage?')..."):
    # Display user's new message immediately
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Generate coach response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your fatigue, HR zones, and training history..."):
            reply = ask_coach(user_prompt)
            st.markdown(reply)
