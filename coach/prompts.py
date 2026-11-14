import json

def format_activities_for_prompt(activities):
    """Formats up to 30 activities into a rich chronological training log."""
    if not activities:
        return "No recent activities recorded in the database yet."

    total_km = round(sum(a.get("metadata", {}).get("total_distance_km", 0) for a in activities), 1)

    lines = [
        f"TOTAL RECORDED MILEAGE (Across last {len(activities)} activities): {total_km} km",
        "--- ACTIVITIES LOG (Newest to Oldest) ---"
    ]
    for act in activities:
        meta = act.get("metadata", {})
        date_str = (meta.get("start_time") or "Unknown date")[:10]
        name = meta.get("activity_name", "Run")
        dist = meta.get("total_distance_km", 0)
        pace = meta.get("average_pace_min_km", "--:--")
        duration = meta.get("duration_formatted", "--:--")
        avg_hr = meta.get("average_hr", "--")
        
        # Dominant zone
        zones = meta.get("hr_zones", [])
        top_zone_str = ""
        if zones:
            top_z = max(zones, key=lambda z: z.get("percentage", 0))
            if top_z.get("percentage", 0) > 0:
                top_zone_str = f" | Top: Zone {top_z.get('zone')} ({top_z.get('percentage')}%)"

        lines.append(f"- [{date_str}] {name}: {dist}km in {duration} (Pace: {pace}/km, Avg HR: {avg_hr} bpm{top_zone_str})")
        if act.get("llm_summary"):
            lines.append(f"  Summary: {act['llm_summary']}")
    
    return "\n".join(lines)

def format_recovery_for_prompt(recovery_input):
    """Formats up to 30 days of recovery and biometrics history for trend analysis."""
    if not recovery_input:
        return "No recovery data recorded in the database yet."

    # Normalize to a list in case a single day doc is passed
    recovery_list = recovery_input if isinstance(recovery_input, list) else [recovery_input]
    if not recovery_list:
        return "No recovery data recorded in the database yet."

    today = recovery_list[0]
    today_sleep = today.get("sleep", {})
    today_hrv = today.get("hrv", {})
    today_bio = today.get("biometrics", {})

    lines = [
        "--- TODAY'S LATEST READINESS ---",
        f"- Date: {today.get('calendar_date', 'Most Recent')}",
        f"- Sleep: {today_sleep.get('sleep_score', 'N/A')}/100 ({today_sleep.get('sleep_duration_hours', 'N/A')} hours, qualifier: {today_sleep.get('sleep_qualifier', 'normal')})",
        f"- Overnight HRV: {today_hrv.get('hrv_status', 'N/A')} (Last night: {today_hrv.get('last_night_avg_ms', 'N/A')} ms, 7-day baseline: {today_hrv.get('weekly_avg_ms', 'N/A')} ms)",
        f"- Resting Heart Rate: {today_bio.get('resting_hr', 'N/A')} bpm",
        f"- Daily Stress: {today_bio.get('avg_stress_level', 'N/A')}/100",
        "",
        f"--- 30-DAY BIOMETRIC & RECOVERY LOG (Last {len(recovery_list)} Days, Newest to Oldest) ---"
    ]

    for rec in recovery_list:
        date = rec.get("calendar_date", "Unknown")
        s = rec.get("sleep", {})
        h = rec.get("hrv", {})
        b = rec.get("biometrics", {})
        
        score = s.get("sleep_score", "--")
        hours = s.get("sleep_duration_hours", "--")
        hrv_st = h.get("hrv_status", "--")
        last_night_hrv = h.get("last_night_avg_ms", "--")
        rhr = b.get("resting_hr", "--")
        lines.append(f"- [{date}] Sleep: {score}/100 ({hours}h) | HRV: {hrv_st} ({last_night_hrv}ms) | Resting HR: {rhr} bpm")

    return "\n".join(lines)

def format_profile_for_prompt(profile):
    """Formats athlete goals, personal bests, current status, and preferences."""
    if not profile or not isinstance(profile, dict):
        return "Standard endurance fitness training."

    # Format personal bests (PRs)
    pbs = profile.get("personal_bests", {})
    pb_items = []
    if pbs.get("5k"):
        pb_items.append(f"5K: {pbs['5k']}")
    if pbs.get("10k"):
        pb_items.append(f"10K: {pbs['10k']}")
    if pbs.get("half_marathon"):
        pb_items.append(f"Half Marathon: {pbs['half_marathon']}")
    if pbs.get("marathon"):
        pb_items.append(f"Marathon: {pbs['marathon']}")
    
    pb_text = ", ".join(pb_items) if pb_items else "None recorded yet"

    return (
        f"- Primary Goal: {profile.get('goal', 'Improve aerobic fitness')}\n"
        f"- Target Races: {profile.get('target_races', 'None specified')}\n"
        f"- Personal Bests (PRs): {pb_text}\n"
        f"- Aches & Injury History: {profile.get('injuries_and_aches', 'None')}\n"
        f"- Gear & Shoes: {profile.get('gear', 'Standard gear')}\n"
        f"- Preferences & Constraints: {profile.get('preferences', 'None')}"
    )

def build_coach_system_instruction(profile, recovery, recent_activities):
    """Assembles the complete system prompt for the AI Coach."""
    profile_text = format_profile_for_prompt(profile)
    recovery_text = format_recovery_for_prompt(recovery)
    activities_text = format_activities_for_prompt(recent_activities)

    return f"""You are an elite endurance running coach and sports scientist.
You are coaching an athlete on a 1-on-1 basis. Your coaching style is encouraging, scientifically grounded, highly attentive to injury prevention, and actionable.

ATHLETE PROFILE & OBJECTIVES:
{profile_text}

RECOVERY & BIOMETRICS (Today + 30-Day Trends):
{recovery_text}

GARMIN ACTIVITIES LOG (Up to Last 30 Workouts):
{activities_text}

COACHING GUIDELINES:
1. Multi-week trend analysis: Use the 30-day activity log and biometric recovery history to assess acute vs. chronic training load (ACWR), overall weekly mileage progression, and resting heart rate baseline shifts.
2. Factor in fatigue & autonomic stress: If HRV is low or sleep has been consistently poor over recent days, recommend dialing back intensity or inserting a recovery run.
3. Monitor training load: Be mindful of sudden mileage jumps (the 10% rule) and excessive high-intensity time in Zones 4/5.
4. Calibrate workouts to their Personal Bests: Use their 5K, 10K, or Half Marathon PBs to prescribe accurate training paces (e.g. threshold pace, VO2 max interval pace, and true easy/recovery pace).
5. Be conversational and direct: Do not produce giant walls of generic text. Give direct answers with specific recommendations (e.g. target paces, heart rate zones, distances, or rest instructions).
6. Reference their actual metrics: Mention their real runs, recent paces, and recovery scores when explaining the "why" behind your advice.
7. Long-term memory: Always remember past aches, ongoing niggles, and target races mentioned across the conversation history. If the athlete mentions feeling pain, prioritize injury prevention over hitting a workout target.
"""
