from datetime import date, datetime, timedelta


def _activity_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def _is_cycling(metadata):
    sport = metadata.get("sport_category") or ""
    activity_type = (metadata.get("activity_type") or "").lower()
    return sport == "cycling" or "cycl" in activity_type or "bike" in activity_type


def format_activities_for_prompt(activities):
    """Formats five weeks of activity trends plus a few recent workout details."""
    if not activities:
        return "No recent activities recorded in the database yet."

    today = date.today()
    current_week = today - timedelta(days=today.weekday())
    first_week = current_week - timedelta(weeks=4)
    weeks = {}
    recent = []

    for act in activities:
        meta = act.get("metadata", {})
        activity_date = _activity_date(meta.get("start_time"))
        if activity_date is None or activity_date > today:
            continue

        week_start = activity_date - timedelta(days=activity_date.weekday())
        if week_start < first_week:
            continue

        weekly = weeks.setdefault(week_start, {
            "run_distance": 0.0,
            "run_count": 0,
            "longest_run": 0.0,
            "high_intensity_seconds": 0.0,
            "bike_count": 0,
            "bike_duration_seconds": 0.0,
        })
        distance = meta.get("total_distance_km") or 0
        duration = meta.get("duration_seconds") or 0

        if _is_cycling(meta):
            weekly["bike_count"] += 1
            weekly["bike_duration_seconds"] += duration
        else:
            weekly["run_count"] += 1
            weekly["run_distance"] += distance
            weekly["longest_run"] = max(weekly["longest_run"], distance)
            high_zone_share = sum(
                zone.get("percentage", 0)
                for zone in meta.get("hr_zones", [])
                if (zone.get("zone") or 0) >= 4
            )
            weekly["high_intensity_seconds"] += duration * high_zone_share / 100

        recent.append((activity_date, act))

    lines = ["--- WEEKLY TRAINING TREND (Five ISO weeks; bike kept separate from running) ---"]
    for week_start in (first_week + timedelta(weeks=i) for i in range(5)):
        weekly = weeks.get(week_start)
        if weekly is None:
            summary = "No activities recorded"
        elif weekly["run_count"] == 0:
            summary = (
                f"Run 0.0 km/0 runs | Bike {weekly['bike_count']} sessions/"
                f"{round(weekly['bike_duration_seconds'] / 60)} min"
            )
        else:
            run_summary = (
                f"Run {weekly['run_distance']:.1f} km/{weekly['run_count']} "
                f"(longest {weekly['longest_run']:.1f} km; "
                f"Z4-5 ~{round(weekly['high_intensity_seconds'] / 60)} min)"
            )
            bike_summary = f"Bike {weekly['bike_count']} sessions/{round(weekly['bike_duration_seconds'] / 60)} min"
            summary = f"{run_summary} | {bike_summary}"
        week_label = "current week to date" if week_start == current_week else f"week of {week_start.isoformat()}"
        lines.append(f"- [{week_label}] {summary}")

    lines.extend(["", "--- RECENT WORKOUTS (Up to 5; no duplicated summaries) ---"])
    for activity_date, act in sorted(recent, key=lambda item: item[0], reverse=True)[:5]:
        meta = act.get("metadata", {})
        distance = meta.get("total_distance_km") or 0
        duration = meta.get("duration_formatted", "--")
        avg_hr = meta.get("average_hr")
        hr_text = f", avg HR {avg_hr} bpm" if avg_hr else ""

        if _is_cycling(meta):
            details = f"{distance:g} km, {duration}, {meta.get('speed_kmh', 0)} km/h"
            power = meta.get("average_power_watts")
            if power:
                details += f", {power} W"
            label = "Bike"
        else:
            pace = meta.get("average_pace_min_km", "--")
            details = f"{distance:g} km, {duration}, {pace}/km"
            label = "Run"

        name = meta.get("activity_name", "Workout")
        lines.append(f"- [{activity_date.isoformat()}] {label} {name}: {details}{hr_text}")

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

GARMIN TRAINING HISTORY (Five-week trend + recent workout detail):
{activities_text}

COACHING GUIDELINES:
1. Compare completed weeks' running distance, long-run distance, and Zone 4/5 time to discuss training trends. The current week is incomplete; do not compare it directly with full weeks or claim a precise ACWR from these summaries.
2. Factor in fatigue & autonomic stress: If HRV is low or sleep has been consistently poor over recent days, recommend dialing back intensity or inserting a recovery run.
3. Monitor training load: Notice sudden mileage jumps and excessive high-intensity time in Zones 4/5; treat the 10% rule as a heuristic, not a strict cutoff.
4. Calibrate workouts to their Personal Bests: Use their 5K, 10K, or Half Marathon PBs to prescribe accurate training paces (e.g. threshold pace, VO2 max interval pace, and true easy/recovery pace).
5. Be conversational and direct: Do not produce giant walls of generic text. Give direct answers with specific recommendations (e.g. target paces, heart rate zones, distances, or rest instructions).
6. Reference their actual metrics: Mention their real runs, recent paces, and recovery scores when explaining the "why" behind your advice.
7. Long-term memory: Always remember past aches, ongoing niggles, and target races mentioned across the conversation history. If the athlete mentions feeling pain, prioritize injury prevention over hitting a workout target.
8. Cross-Training & Indoor Cycling: Treat indoor bike/trainer sessions as non-impact aerobic conditioning and active recovery. Cycling builds mitochondrial density, capillary beds, and aerobic base with zero bone/tendon pounding. NEVER combine cycling kilometers directly into running mileage when assessing weekly running progression (the 10% rule), but DO consider the heart rate zones and cardiovascular fatigue when planning upcoming running workouts.
"""
