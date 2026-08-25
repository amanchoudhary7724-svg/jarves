import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import CFG

from tools import youtube_analytics as ya


def _gather_data(video_id=None, days=30):
    data = {}
    data["stats"] = ya.get_video_stats(video_id, days)
    data["traffic"] = ya.get_traffic_sources(video_id, days)
    data["demographics"] = ya.get_audience_demographics(video_id, days)
    if video_id:
        data["retention"] = ya.get_retention_curve(video_id, days)
    return data


def _build_prompt(data, video_id, language):
    stats = data.get("stats", "")
    traffic = data.get("traffic", "")
    demo = data.get("demographics", "")
    retention = data.get("retention", "N/A")

    if language == "hi":
        instruction = """Tum ek YouTube growth expert ho. Neeche di gayi analytics data analyse karo
aur Hindi/Hinglish mein 3-5 actionable suggestions do taaki video ka performance improve ho.

Focus karo:
- Title optimization (better CTR)
- Thumbnail ideas
- Tag suggestions
- Posting time (audience demographics se)
- Content/retention improvement (drop-off points)
- Traffic source optimization

Format: Har suggestion ek line mein, bullet points mein."""
    else:
        instruction = """You are a YouTube growth expert. Analyze the analytics data below
and give 3-5 actionable suggestions in English to improve video performance.

Focus on:
- Title optimization (better CTR)
- Thumbnail ideas
- Tag suggestions
- Posting time (from demographics)
- Content/retention improvement (drop-off points)
- Traffic source optimization

Format: Each suggestion one line, bullet points."""

    context = f"""VIDEO ID: {video_id or 'CHANNEL'}
STATS:
{stats}

TRAFFIC SOURCES:
{traffic}

DEMOGRAPHICS:
{demo}

RETENTION:
{retention}

Give suggestions:"""
    return instruction + "\n\n" + context


def optimize_video(video_id=None, days=30, language="hi"):
    cfg = CFG.get("youtube", {}).get("analytics", {}).get("optimization", {})
    if cfg.get("enabled", True) is False:
        return "Optimization disabled in config."

    data = _gather_data(video_id, days)
    prompt = _build_prompt(data, video_id, language)

    try:
        import llm
        resp, _ = llm.chat([
            {"role": "system", "content": "You are a YouTube growth expert. Be concise, actionable."},
            {"role": "user", "content": prompt},
        ], tools=None, tier="cloud_heavy")
        suggestions = resp.get("content", "")
        if not suggestions:
            return "Analysis complete but no suggestions generated.\n\n" + "\n".join(data.values())
        header = f"YouTube Optimization Report ({days} days):\n"
        return header + suggestions
    except Exception as e:
        return f"Optimization failed: {type(e).__name__}: {e}\n\nRaw data:\n" + "\n".join(str(v) for v in data.values())


def get_full_report(video_id=None, days=30, language="hi"):
    lines = []
    if video_id:
        lines.append(ya.get_video_stats(video_id, days))
    else:
        lines.append(ya.get_channel_stats(days))
    lines.append("")
    lines.append(ya.get_traffic_sources(video_id, days))
    lines.append("")
    lines.append(ya.get_audience_demographics(video_id, days))
    if video_id:
        lines.append("")
        lines.append(ya.get_retention_curve(video_id, days))
    return "\n".join(lines)


if __name__ == "__main__":
    print("Testing optimizer...")
    print(optimize_video(days=7, language="hi"))
