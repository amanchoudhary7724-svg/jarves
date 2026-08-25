import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import CFG

try:
    from googleapiclient.errors import HttpError
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

from tools import youtube_tools as yt


def _date_ndays_ago(n):
    d = datetime.date.today() - datetime.timedelta(days=n)
    return d.isoformat()


def _call_analytics(metrics, dimensions=None, filters=None, days=30, sort=None):
    service, err = yt._get_analytics_service()
    if err:
        return None, err
    try:
        start = _date_ndays_ago(days)
        end = datetime.date.today().isoformat()
        body = {
            "ids": "channel==MINE",
            "startDate": start,
            "endDate": end,
            "metrics": ",".join(metrics),
        }
        if dimensions:
            body["dimensions"] = ",".join(dimensions)
        if filters:
            body["filters"] = filters
        if sort:
            body["sort"] = ",".join(sort)
        request = service.reports().query(**body)
        response = request.execute()
        return response, None
    except HttpError as e:
        return None, f"YouTube Analytics API error: {e}"
    except Exception as e:
        return None, f"Analytics error: {type(e).__name__}: {e}"


def get_video_stats(video_id=None, days=30):
    if video_id:
        filters = f"video=={video_id}"
    else:
        filters = None
    metrics = ["views", "estimatedMinutesWatched", "averageViewDuration", "averageViewPercentage",
               "likes", "comments", "shares", "subscribersGained"]
    resp, err = _call_analytics(metrics, filters=filters, days=days)
    if err:
        return f"Video stats failed: {err}"

    rows = resp.get("rows")
    if not rows:
        return "Koi data nahi mila. Video abhi naya hai ya analytics enable nahi hai."

    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    row = rows[0]
    data = dict(zip(headers, row))

    lines = ["Video Analytics (last {0} days):".format(days)]
    lines.append(f"  Views: {int(data.get('views', 0)):,}")
    lines.append(f"  Watch time (hours): {float(data.get('estimatedMinutesWatched', 0)) / 60:.1f}")
    lines.append(f"  Avg view duration: {int(data.get('averageViewDuration', 0))} sec")
    lines.append(f"  Avg view %: {float(data.get('averageViewPercentage', 0)):.1f}%")
    lines.append(f"  Likes: {int(data.get('likes', 0)):,}")
    lines.append(f"  Comments: {int(data.get('comments', 0)):,}")
    lines.append(f"  Shares: {int(data.get('shares', 0)):,}")
    lines.append(f"  Subscribers gained: {int(data.get('subscribersGained', 0)):,}")
    return "\n".join(lines)


def get_channel_stats(days=30):
    metrics = ["views", "estimatedMinutesWatched", "subscribersGained", "subscribersLost", "likes", "comments"]
    resp, err = _call_analytics(metrics, days=days)
    if err:
        return f"Channel stats failed: {err}"

    rows = resp.get("rows")
    if not rows:
        return "Koi channel data nahi mila."

    headers = [h["name"] for h in resp.get("columnHeaders", [])]
    row = rows[0]
    data = dict(zip(headers, row))

    lines = ["Channel Analytics (last {0} days):".format(days)]
    lines.append(f"  Views: {int(data.get('views', 0)):,}")
    lines.append(f"  Watch time (hours): {float(data.get('estimatedMinutesWatched', 0)) / 60:.1f}")
    lines.append(f"  Subs gained: {int(data.get('subscribersGained', 0)):,}")
    lines.append(f"  Subs lost: {int(data.get('subscribersLost', 0)):,}")
    lines.append(f"  Likes: {int(data.get('likes', 0)):,}")
    lines.append(f"  Comments: {int(data.get('comments', 0)):,}")
    return "\n".join(lines)


def get_traffic_sources(video_id=None, days=30):
    metrics = ["views", "estimatedMinutesWatched"]
    dimensions = ["insightTrafficSourceType"]
    if video_id:
        filters = f"video=={video_id}"
    else:
        filters = None
    resp, err = _call_analytics(metrics, dimensions=dimensions, filters=filters, days=days)
    if err:
        return f"Traffic sources failed: {err}"

    rows = resp.get("rows")
    if not rows:
        return "Traffic source data nahi mila."

    lines = ["Traffic Sources (last {0} days):".format(days)]
    source_labels = {
        "YOUTUBE_SEARCH": "YouTube Search",
        "SUGGESTED_VIDEO": "Suggested Videos",
        "EXT_APP": "External App",
        "EXT_URL": "External URL",
        "BROWSE": "Browse Features",
        "PLAYLIST": "Playlist",
        "NOTIFICATION": "Notifications",
        "CHANNEL": "Channel Pages",
        "OTHER": "Other",
    }
    total = sum(r[1] if len(r) > 1 else r[0] for r in rows)
    for row in rows:
        src = row[0]
        views = row[1] if len(row) > 1 else 0
        pct = (views / total * 100) if total else 0
        label = source_labels.get(src, src)
        lines.append(f"  {label}: {int(views):,} views ({pct:.1f}%)")
    return "\n".join(lines)


def get_audience_demographics(video_id=None, days=30):
    metrics = ["viewerPercentage"]
    dimensions = ["ageGroup", "gender"]
    if video_id:
        filters = f"video=={video_id}"
    else:
        filters = None
    resp, err = _call_analytics(metrics, dimensions=dimensions, filters=filters, days=days)
    if err:
        return f"Demographics failed: {err}"

    rows = resp.get("rows")
    if not rows:
        return "Demographics data nahi mila."

    lines = ["Audience Demographics (last {0} days):".format(days)]
    for row in sorted(rows, key=lambda x: x[2] if len(x) > 2 else 0, reverse=True):
        age = row[0]
        gender = row[1]
        pct = float(row[2]) if len(row) > 2 else 0
        lines.append(f"  {age} {gender}: {pct:.1f}%")
    return "\n".join(lines)


def get_retention_curve(video_id, days=30):
    metrics = ["audienceWatchRatio"]
    dimensions = ["elapsedVideoTimeRatio"]
    filters = f"video=={video_id}"
    resp, err = _call_analytics(metrics, dimensions=dimensions, filters=filters, days=days)
    if err:
        return f"Retention failed: {err}"

    rows = resp.get("rows")
    if not rows:
        return "Retention data nahi mila. Video ko kuch views aane chahiye."

    total = len(rows)
    lines = ["Audience Retention Curve:"]
    sample_points = [0, total // 4, total // 2, (3 * total) // 4, total - 1]
    for i in sample_points:
        if 0 <= i < total:
            ratio = float(rows[i][0])
            time_label = f"{int(ratio * 100)}% mark"
            retention = float(rows[i][1])
            lines.append(f"  {time_label}: {retention * 100:.1f}% viewers remaining")
    return "\n".join(lines)


if __name__ == "__main__":
    print("Testing analytics...")
    print(get_channel_stats(7))
    print()
    print(get_traffic_sources())
    print()
    print(get_audience_demographics())
