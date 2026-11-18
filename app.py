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
            hrv_ms = hrv.get("last_night_avg_ms")
            hrv_status = hrv.get("hrv_status", "N/A")
            st.metric("Overnight HRV", f"{hrv_ms} ms" if hrv_ms else "N/A", help=f"Garmin HRV Status: {hrv_status}")
            st.metric("Sleep Hours", f"{sleep.get('sleep_duration_hours', 'N/A')}h")

        st.caption(f"HRV Status: **{hrv_status}** • Synced: **{recovery.get('calendar_date', 'Unknown')}**")
    else:
        st.info("No recovery data found yet. Run `python sync/sync_recovery.py` to fetch your metrics.")

    st.divider()

    # Section B: Athlete Objectives & Injury Tracking
    st.subheader("🎯 Athlete Profile & Status")
    current_profile = get_athlete_profile()

    # 1. Clean Display View (Text wraps naturally, no cut-offs!)
    with st.container():
        st.markdown(f"**🎯 Goal:** {current_profile.get('goal', 'None')}")
        st.markdown(f"**🏁 Target Races:** {current_profile.get('target_races', 'None')}")

        pbs = current_profile.get("personal_bests", {})
        pb_items = []
        if pbs.get("5k"): pb_items.append(f"**5K:** {pbs['5k']}")
        if pbs.get("10k"): pb_items.append(f"**10K:** {pbs['10k']}")
        if pbs.get("half_marathon"): pb_items.append(f"**HM:** {pbs['half_marathon']}")
        if pbs.get("marathon"): pb_items.append(f"**M:** {pbs['marathon']}")
        
        if pb_items:
            st.markdown(f"⚡ **PRs:** {' • '.join(pb_items)}")

        st.markdown(f"**🩹 Aches / Status:** {current_profile.get('injuries_and_aches', 'None')}")
        st.markdown(f"**👟 Gear:** {current_profile.get('gear', 'None')}")
        st.markdown(f"**🗓️ Preferences:** {current_profile.get('preferences', 'None')}")

    # 2. Collapsible Edit Form (Expands only when you want to change something)
    with st.expander("✏️ Edit Profile Manually"):
        with st.form("profile_form"):
            goal = st.text_area("Primary Goal", value=current_profile.get("goal", ""), height=68)
            races = st.text_area("Target Races", value=current_profile.get("target_races", ""), height=68)
            
            # Personal Bests section
            st.markdown("**⚡ Personal Bests (PRs)**")
            pb_col1, pb_col2 = st.columns(2)
            with pb_col1:
                pb_5k = st.text_input("5K", value=pbs.get("5k", ""), placeholder="e.g. 18:39")
                pb_10k = st.text_input("10K", value=pbs.get("10k", ""), placeholder="e.g. 37:54")
            with pb_col2:
                pb_hm = st.text_input("Half Marathon", value=pbs.get("half_marathon", ""), placeholder="e.g. 1:24:22")
                pb_marathon = st.text_input("Marathon", value=pbs.get("marathon", ""), placeholder="e.g. 3:14:25")

            injuries = st.text_area("Aches / Injuries / Fatigue", value=current_profile.get("injuries_and_aches", ""), height=75)
            gear = st.text_area("Gear & Shoes", value=current_profile.get("gear", ""), height=68, placeholder="e.g. Novablast 5")
            preferences = st.text_area("Preferences / Constraints", value=current_profile.get("preferences", ""), height=80)
            
            submitted = st.form_submit_button("💾 Save Changes")
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
                    "gear": gear,
                    "preferences": preferences
                }
                update_athlete_profile(updated)
                st.success("Profile updated!")
                st.rerun()

    st.divider()

    # Section C: Chat Controls
    if st.button("🗑️ Clear Chat History"):
        clear_chat_history()
        st.session_state.messages = []
        st.rerun()

# 3. Main Area: Chat Interface
st.title("💬 Chat with Your Coach")
st.caption("Powered by Garmin Connect biometrics + Google Gemini")

# Load persistent conversation history from MongoDB (Last 100 messages)
db_messages = get_chat_history(limit=100)

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
        if msg.get("model"):
            st.caption(f"Model: {msg['model']}")

# User Chat Input Box
if user_prompt := st.chat_input("Ask your coach (e.g., 'What should my workout be today?' or 'How is my weekly mileage?')..."):
    # Display user's new message immediately
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Generate coach response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your fatigue, HR zones, and training history..."):
            reply, model = ask_coach(user_prompt)
            st.markdown(reply)
            if model:
                st.caption(f"Model: {model}")
