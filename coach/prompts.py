import json

def format_activities_for_prompt(activities):
    """Formats activities into a clean readable log for the LLM."""
    if not activities:
        return "No recent activities recorded in the database yet."

    lines = []
    for act in activities:
        meta = act.get("metadata", {})
        date_str = meta.get("start_time", "Unknown date")[:10]
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

def format_recovery_for_prompt(recovery):
    """Formats today's recovery metrics for the LLM."""
    if not recovery:
        return "No recovery data recorded for today yet."

    sleep = recovery.get("sleep", {})
    hrv = recovery.get("hrv", {})
    bio = recovery.get("biometrics", {})

    lines = [
        f"- Date: {recovery.get('calendar_date', 'Today')}",
        f"- Sleep: {sleep.get('sleep_score', 'N/A')}/100 ({sleep.get('sleep_duration_hours', 'N/A')} hours, qualifier: {sleep.get('sleep_qualifier', 'normal')})",
        f"- Overnight HRV Status: {hrv.get('hrv_status', 'N/A')} (Last night avg: {hrv.get('last_night_avg_ms', 'N/A')} ms, Weekly avg: {hrv.get('weekly_avg_ms', 'N/A')} ms)",
        f"- Resting Heart Rate: {bio.get('resting_hr', 'N/A')} bpm",
        f"- Average Daily Stress: {bio.get('avg_stress_level', 'N/A')}/100"
    ]
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

LATEST RECOVERY & BIOMETRICS:
{recovery_text}

RECENT GARMIN ACTIVITIES (Newest First):
{activities_text}

COACHING GUIDELINES:
1. Always factor in recent fatigue and recovery status: If HRV is low or sleep is poor, recommend dialing back intensity or taking an active recovery run.
2. Monitor training load: Be mindful of sudden mileage jumps (the 10% rule) and excessive high-intensity time in Zones 4/5.
3. Calibrate workouts to their Personal Bests: Use their 5K, 10K, or Half Marathon PBs to prescribe accurate training paces (e.g. threshold pace, VO2 max interval pace, and true easy/recovery pace).
4. Be conversational and direct: Do not produce giant walls of generic text. Give direct answers with specific recommendations (e.g. target paces, heart rate zones, distances, or rest instructions).
5. Reference their actual metrics: Mention their real runs, recent paces, and recovery scores when explaining the "why" behind your advice.
6. If the athlete mentions feeling pain or tightness, prioritize injury prevention over hitting a workout target.
"""
