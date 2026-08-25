import datetime
import os
import re
import sys

from config_loader import BASE_DIR, CFG

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _is_configured():
    cfg = CFG.get("calendar", {})
    creds_path = os.path.join(BASE_DIR, cfg.get("credentials_file", "credentials.json"))
    return bool(cfg.get("enabled") and os.path.isfile(creds_path))


def _get_service():
    if not _is_configured():
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("[Calendar] Google libs install nahi hain: pip install google-api-python-client google-auth-oauthlib")
        return None

    cfg = CFG["calendar"]
    creds_path = os.path.join(BASE_DIR, cfg.get("credentials_file", "credentials.json"))
    token_path = os.path.join(BASE_DIR, cfg.get("token_file", "token.json"))

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    try:
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        print(f"[Calendar] Service error: {e}")
        return None


def get_today_events():
    service = _get_service()
    if service is None:
        return "Calendar setup nahi hua hai. SETUP.md mein steps dekho."
    now = datetime.datetime.utcnow()
    start = datetime.datetime(now.year, now.month, now.day)
    end = start + datetime.timedelta(days=1)
    body = {
        "timeMin": start.isoformat() + "Z",
        "timeMax": end.isoformat() + "Z",
        "singleEvents": True,
        "orderBy": "startTime",
    }
    events = service.events().list(calendarId="primary", **body).execute().get("items", [])
    if not events:
        return "Aaj koi event nahi hai. Poora din free hai!"
    lines = [f"Aaj {len(events)} events hain:"]
    for ev in events:
        title = ev.get("summary", "(bina naam)")
        st = ev["start"].get("dateTime", ev["start"].get("date"))
        time_str = st[11:16] if len(st) > 10 else "poore din"
        lines.append(f"- {time_str} baje: {title}")
    return "\n".join(lines)


def get_upcoming_events(days=7):
    days = max(1, min(30, int(days)))
    service = _get_service()
    if service is None:
        return "Calendar setup nahi hua hai. SETUP.md mein steps dekho."
    now = datetime.datetime.utcnow()
    body = {
        "timeMin": now.isoformat() + "Z",
        "timeMax": (now + datetime.timedelta(days=days)).isoformat() + "Z",
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": 15,
    }
    events = service.events().list(calendarId="primary", **body).execute().get("items", [])
    if not events:
        return f"Agale {days} din mein koi event nahi hai."
    lines = [f"Agale {days} din ke events:"]
    day_names = ["Somvaar", "Mangalvaar", "Budhvaar", "Guruvaar", "Shukravaar", "Shanivaar", "Ravivaar"]
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for ev in events:
        title = ev.get("summary", "(bina naam)")
        st = ev["start"].get("dateTime", ev["start"].get("date"))
        try:
            dt = datetime.datetime.fromisoformat(st.replace("Z", "+00:00"))
            label = f"{day_names[dt.weekday()]}, {dt.day} {month_names[dt.month-1]} ko {dt.hour}:{dt.minute:02d} baje"
        except Exception:
            label = st[:10]
        lines.append(f"- {label}: {title}")
    return "\n".join(lines)


def get_next_meeting():
    service = _get_service()
    if service is None:
        return "Calendar setup nahi hua hai. SETUP.md mein steps dekho."
    now = datetime.datetime.utcnow()
    body = {
        "timeMin": now.isoformat() + "Z",
        "maxResults": 1,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    events = service.events().list(calendarId="primary", **body).execute().get("items", [])
    if not events:
        return "Koi upcoming meeting nahi hai."
    ev = events[0]
    title = ev.get("summary", "(bina naam)")
    st = ev["start"].get("dateTime", ev["start"].get("date"))
    try:
        dt = datetime.datetime.fromisoformat(st.replace("Z", "+00:00"))
        diff = dt - now.replace(tzinfo=datetime.timezone.utc) if dt.tzinfo else dt - now
        mins = int(diff.total_seconds() / 60)
        when = f"{mins} minute baad" if 0 <= mins < 1440 else f"{dt.day}/{dt.month} ko {dt.hour}:{dt.minute:02d} baje"
    except Exception:
        when = st[:10]
    return f"Agla event '{title}' hai, {when}."


def add_event(title, date=None, time_str=None, duration_min=60):
    from dateutil import parser as dtparser

    title = str(title).strip()
    if not title:
        return "Event ka naam toh batao!"
    duration_min = max(5, min(600, int(duration_min)))
    service = _get_service()
    if service is None:
        return "Calendar setup nahi hua hai. SETUP.md mein steps dekho."

    tzname = CFG.get("calendar", {}).get("timezone", "Asia/Kolkata")
    now = datetime.datetime.now()
    try:
        if date:
            base = dtparser.parse(str(date))
        else:
            base = now
        if time_str:
            tm = str(time_str).strip().replace(".", ":")
            parts = re.split(r"[:h ]+", tm)
            nums = [p for p in parts if p.isdigit()]
            hour = int(nums[0]) if len(nums) >= 1 else now.hour
            minute = int(nums[1]) % 60 if len(nums) >= 2 else 0
            tl = tm.lower()
            if any(x in tl for x in ("pm", "shaam")) and hour < 12:
                hour += 12
            elif any(x in tl for x in ("am", "subah")) and hour == 12:
                hour = 0
            elif "baje" in tl and hour < 9:
                hour += 12
            base = base.replace(hour=min(23, hour), minute=minute)
        elif not date:
            base = base + datetime.timedelta(hours=1)
        start = base.replace(second=0, microsecond=0)
        end = start + datetime.timedelta(minutes=duration_min)
    except Exception as e:
        return f"Date/time samajh nahi aaya ({e}). Format: 'kal', '2026-08-25', '3:30 pm' jaisa likho."

    body = {
        "summary": title,
        "start": {"dateTime": start.isoformat(), "timeZone": tzname},
        "end": {"dateTime": end.isoformat(), "timeZone": tzname},
    }
    try:
        created = service.events().insert(calendarId="primary", body=body).execute()
        return f"'{title}' add kar diya: {start.day}/{start.month} ko {start.hour}:{start.minute:02d} baje."
    except Exception as e:
        return f"Event add nahi ho paya ({type(e).__name__})."
