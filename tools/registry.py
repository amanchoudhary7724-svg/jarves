import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import offline_tools as off
from tools import online_tools as onl
from tools import email_tools as eml
from tools import calendar_tools as cal
import screen_reader as sr
from tools import youtube_tools as yt
from tools import video_creator as vc
from tools import thumbnail_maker as tm
from tools import youtube_analytics as ya
from tools import video_optimizer as vo
from tools import dev_tools as dv
from tools import project_builder as pb
from tools import pc_control as pc

TOOLS = [
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "open_app",
                "description": "Koi bhi app ya website kholo. name: app ka naam ya website jaise chrome, youtube, notepad, vs code",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string", "description": "App/website ka naam"}},
                    "required": ["name"],
                },
            },
        },
        "func": off.open_app,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "close_app",
                "description": "Chalu app band karo. name: app ka naam",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        "func": off.close_app,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "set_volume",
                "description": "Speaker volume ek specific level par set karo (0-100)",
                "parameters": {
                    "type": "object",
                    "properties": {"percent": {"type": "integer", "description": "0 se 100"}},
                    "required": ["percent"],
                },
            },
        },
        "func": off.set_volume,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "change_volume",
                "description": "Volume badhao ya kam karo. delta: positive badhane ke liye, negative kam karne ke liye (jaise 10 ya -10)",
                "parameters": {
                    "type": "object",
                    "properties": {"delta": {"type": "integer"}},
                    "required": ["delta"],
                },
            },
        },
        "func": off.change_volume,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "toggle_mute",
                "description": "Sound mute ya unmute karo",
                "parameters": {
                    "type": "object",
                    "properties": {"mute": {"type": "boolean", "description": "true= mute, false= unmute"}},
                    "required": ["mute"],
                },
            },
        },
        "func": off.toggle_mute,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "media_control",
                "description": "Music/media control. action: play, pause, next, previous, stop",
                "parameters": {
                    "type": "object",
                    "properties": {"action": {"type": "string", "enum": ["play", "pause", "next", "previous", "stop"]}},
                    "required": ["action"],
                },
            },
        },
        "func": off.media_control,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "take_screenshot",
                "description": "Screen ka screenshot lo aur Pictures folder mein save karo",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: off.take_screenshot(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "lock_pc",
                "description": "PC ko lock karo",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: off.lock_pc(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "battery_status",
                "description": "Battery level aur charging status batao",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: off.battery_status(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Current time ya date batao. kind: time ya date",
                "parameters": {
                    "type": "object",
                    "properties": {"kind": {"type": "string", "enum": ["time", "date"]}},
                    "required": ["kind"],
                },
            },
        },
        "func": off.get_time,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "shutdown_pc",
                "description": "PC shutdown/restart karo (60 second delay ke saath). mode: shutdown ya restart",
                "parameters": {
                    "type": "object",
                    "properties": {"mode": {"type": "string", "enum": ["shutdown", "restart"]}},
                    "required": ["mode"],
                },
            },
        },
        "func": off.shutdown_pc,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "abort_shutdown",
                "description": "Pending shutdown/restart cancel karo",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: off.abort_shutdown(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Internet par search karo aur latest jaankari lao (news, facts, current affairs)",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        "func": onl.web_search,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "wikipedia_summary",
                "description": "Kisi topic/vyakti/jagah ke baare mein Wikipedia se jaankari do",
                "parameters": {
                    "type": "object",
                    "properties": {"topic": {"type": "string"}},
                    "required": ["topic"],
                },
            },
        },
        "func": onl.wikipedia_summary,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Kisi shehar ka current mausam batao",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string", "description": "Shehar ka naam, default Delhi"}},
                    "required": [],
                },
            },
        },
        "func": lambda city="Delhi": onl.get_weather(city),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "check_emails",
                "description": "Unread emails check karo aur latest emails ki list do",
                "parameters": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "description": "Kitne emails dikhane hain (1-10), default 5"}},
                    "required": [],
                },
            },
        },
        "func": lambda limit=5: eml.check_emails(limit),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "read_latest_email",
                "description": "Sabse naya email poora padho (from, subject, body)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: eml.read_latest_email(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "search_emails",
                "description": "Emails mein koi naam, subject ya sender dhundo",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search word - naam ya subject"}},
                    "required": ["query"],
                },
            },
        },
        "func": eml.search_emails,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "get_today_events",
                "description": "Aaj ke calendar events dikhao",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: cal.get_today_events(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "get_upcoming_events",
                "description": "Agale kuch dino ke calendar events dikhao",
                "parameters": {
                    "type": "object",
                    "properties": {"days": {"type": "integer", "description": "Kitne din tak (default 7)"}},
                    "required": [],
                },
            },
        },
        "func": lambda days=7: cal.get_upcoming_events(days),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "get_next_meeting",
                "description": "Agla upcoming event/meeting batao",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: cal.get_next_meeting(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "add_event",
                "description": "Calendar mein naya event add karo. date format: 'kal' ya '2026-08-25', time jaise '3:30 pm'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Event ka naam"},
                        "date": {"type": "string", "description": "Date (optional, default aaj)"},
                        "time_str": {"type": "string", "description": "Time jaise 3:30 pm (optional)"},
                        "duration_min": {"type": "integer", "description": "Duration minutes mein (default 60)"},
                    },
                    "required": ["title"],
                },
            },
        },
        "func": cal.add_event,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "read_screen",
                "description": "Screen ka text padho. mode: active (default), full, ya selection",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string", "enum": ["active", "full", "selection"], "description": "active=current window, full=poora screen, selection=selected text"}
                    },
                    "required": [],
                },
            },
        },
        "func": lambda mode="active": sr.read_screen(mode),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_search",
                "description": "YouTube par video search karo. query: search keywords",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search keywords"},
                        "max_results": {"type": "integer", "description": "Max results (1-10), default 5"}
                    },
                    "required": ["query"],
                },
            },
        },
        "func": lambda query, max_results=5: yt.youtube_search(query, max_results),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_play_video",
                "description": "YouTube video play karo. query_or_id: video name ya YouTube URL/ID",
                "parameters": {
                    "type": "object",
                    "properties": {"query_or_id": {"type": "string", "description": "Video name, URL, ya video ID"}},
                    "required": ["query_or_id"],
                },
            },
        },
        "func": yt.youtube_play_video,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_get_video_details",
                "description": "YouTube video ki details nikalo (views, likes, duration). video_id: 11-char YouTube ID",
                "parameters": {
                    "type": "object",
                    "properties": {"video_id": {"type": "string", "description": "YouTube video ID"}},
                    "required": ["video_id"],
                },
            },
        },
        "func": yt.youtube_get_video_details,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_get_my_videos",
                "description": "Apne channel ke latest videos ki list do",
                "parameters": {
                    "type": "object",
                    "properties": {"max_results": {"type": "integer", "description": "Max videos (1-50), default 10"}},
                    "required": [],
                },
            },
        },
        "func": lambda max_results=10: yt.youtube_get_my_videos(max_results),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_check_auth",
                "description": "YouTube API authentication status check karo",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: yt.youtube_check_auth(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_upload_video",
                "description": "YouTube par video upload karo. file_path: video file ka path, title: video title, description: optional, tags: list, privacy: private/unlisted/public",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Video file ka full path"},
                        "title": {"type": "string", "description": "Video title"},
                        "description": {"type": "string", "description": "Video description (optional)"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags list (optional)"},
                        "privacy": {"type": "string", "enum": ["private", "unlisted", "public"], "description": "Privacy status (default private)"},
                        "thumbnail_path": {"type": "string", "description": "Thumbnail image path (optional)"}
                    },
                    "required": ["file_path", "title"],
                },
            },
        },
        "func": lambda file_path, title, description="", tags=None, privacy="private", thumbnail_path=None: yt.youtube_upload_video(file_path, title, description, tags, "22", privacy, thumbnail_path),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_create_video",
                "description": "Topic se video banao (script->slides->TTS->FFmpeg). topic: video topic, duration_min: minutes, language: hi/en",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Video topic"},
                        "duration_min": {"type": "integer", "description": "Duration in minutes (default 2)"},
                        "language": {"type": "string", "enum": ["hi", "en"], "description": "Language (default hi)"}
                    },
                    "required": ["topic"],
                },
            },
        },
        "func": lambda topic, duration_min=2, language="hi": vc.create_video_from_topic(topic, duration_min, language),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_generate_thumbnail",
                "description": "Video ke liye thumbnail banao. title: thumbnail text, style: modern/minimal/bold",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Thumbnail text"},
                        "style": {"type": "string", "enum": ["modern", "minimal", "bold"], "description": "Style (default modern)"},
                        "language": {"type": "string", "enum": ["hi", "en"], "description": "Language (default hi)"}
                    },
                    "required": ["title"],
                },
            },
        },
        "func": lambda title, style="modern", language="hi": tm.generate_thumbnail(title, style=style, language=language),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_update_video",
                "description": "Uploaded video update karo (title, description, tags, privacy). video_id: YouTube video ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string", "description": "YouTube video ID"},
                        "title": {"type": "string", "description": "New title (optional)"},
                        "description": {"type": "string", "description": "New description (optional)"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "New tags (optional)"},
                        "privacy": {"type": "string", "enum": ["private", "unlisted", "public"], "description": "New privacy (optional)"}
                    },
                    "required": ["video_id"],
                },
            },
        },
        "func": lambda video_id, title=None, description=None, tags=None, privacy=None: yt.youtube_update_video(video_id, title, description, tags, privacy),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_delete_video",
                "description": "YouTube video permanently delete karo. video_id: jo delete karna hai",
                "parameters": {
                    "type": "object",
                    "properties": {"video_id": {"type": "string", "description": "Delete karne wala video ID"}},
                    "required": ["video_id"],
                },
            },
        },
        "func": lambda video_id: yt.youtube_delete_video(video_id),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_get_video_stats",
                "description": "YouTube video ki analytics do (views, watch time, retention). video_id: optional, blank = all videos",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string", "description": "YouTube video ID (optional)"},
                        "days": {"type": "integer", "description": "Last N days (default 30)"}
                    },
                    "required": [],
                },
            },
        },
        "func": lambda video_id=None, days=30: ya.get_video_stats(video_id, days),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_get_channel_stats",
                "description": "Channel ki analytics do (views, subs, watch time).",
                "parameters": {
                    "type": "object",
                    "properties": {"days": {"type": "integer", "description": "Last N days (default 30)"}},
                    "required": [],
                },
            },
        },
        "func": lambda days=30: ya.get_channel_stats(days),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_get_traffic_sources",
                "description": "Video/channel par traffic kahan se aa raha hai (search, suggested, etc).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string", "description": "YouTube video ID (optional)"},
                        "days": {"type": "integer", "description": "Last N days (default 30)"}
                    },
                    "required": [],
                },
            },
        },
        "func": lambda video_id=None, days=30: ya.get_traffic_sources(video_id, days),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_get_demographics",
                "description": "Audience ka data do (age, gender, geography).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string", "description": "YouTube video ID (optional)"},
                        "days": {"type": "integer", "description": "Last N days (default 30)"}
                    },
                    "required": [],
                },
            },
        },
        "func": lambda video_id=None, days=30: ya.get_audience_demographics(video_id, days),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_optimize",
                "description": "Video/channel analyze karo aur behtar karne ke suggestions do (AI).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string", "description": "YouTube video ID (optional)"},
                        "days": {"type": "integer", "description": "Last N days (default 30)"},
                        "language": {"type": "string", "enum": ["hi", "en"], "description": "Language (default hi)"}
                    },
                    "required": [],
                },
            },
        },
        "func": lambda video_id=None, days=30, language="hi": vo.optimize_video(video_id, days, language),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "youtube_full_report",
                "description": "Poora analytics report do (stats + traffic + demographics + retention).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string", "description": "YouTube video ID (optional)"},
                        "days": {"type": "integer", "description": "Last N days (default 30)"}
                    },
                    "required": [],
                },
            },
        },
        "func": lambda video_id=None, days=30: vo.get_full_report(video_id, days),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Kisi bhi file ka content padho. path: file ka full path",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "File path"}},
                    "required": ["path"],
                },
            },
        },
        "func": dv.read_file,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Nayi file likho ya overwrite karo. path + content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path (kahan save karna hai)"},
                        "content": {"type": "string", "description": "File ka content"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        "func": dv.write_file,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "File mein specific text replace karo. path + old_str + new_str",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "old_str": {"type": "string", "description": "Jo text replace karna hai"},
                        "new_str": {"type": "string", "description": "Naya text"},
                    },
                    "required": ["path", "old_str", "new_str"],
                },
            },
        },
        "func": dv.edit_file,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "Folder ke andar ki files dikhao. path: folder path",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Folder path (default current)"}},
                    "required": [],
                },
            },
        },
        "func": lambda path=".": dv.list_files(path),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "System command chalao (autonomous). command: jo bhi command hai",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string", "description": "Shell command"}},
                    "required": ["command"],
                },
            },
        },
        "func": dv.run_command,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "create_project",
                "description": "Ek saath multiple files banao. name + structure_json (path:content map)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Project name"},
                        "structure_json": {"type": "string", "description": "JSON: {relative/path: content}"},
                        "base_path": {"type": "string", "description": "Base folder (optional)"},
                    },
                    "required": ["name", "structure_json"],
                },
            },
        },
        "func": lambda name, structure_json, base_path=None: dv.create_project(name, structure_json, base_path),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "explain_code",
                "description": "Code file samjhao (Hindi/English). path: file path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Code file path"},
                        "language": {"type": "string", "description": "Language (default auto)"},
                    },
                    "required": ["path"],
                },
            },
        },
        "func": lambda path, language="auto": dv.explain_code(path, language),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "debug_code",
                "description": "Code file mein bug fix karo. path + error_msg (optional)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Code file path"},
                        "error_msg": {"type": "string", "description": "Error message (optional)"},
                    },
                    "required": ["path"],
                },
            },
        },
        "func": lambda path, error_msg="": dv.debug_code(path, error_msg),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "generate_code",
                "description": "Description se code generate karo. description + language",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "Kya banana hai"},
                        "language": {"type": "string", "description": "Language (python/js/etc)"},
                    },
                    "required": ["description"],
                },
            },
        },
        "func": lambda description, language="python": dv.generate_code(description, language),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "build_project",
                "description": "Command se complete project banao (website, app, game - kuch bhi). description + name (optional)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "Project ka description"},
                        "name": {"type": "string", "description": "Project name (optional)"},
                    },
                    "required": ["description"],
                },
            },
        },
        "func": lambda description, name=None: pb.build_project(description, name),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "build_website",
                "description": "Complete website banao (HTML/CSS/JS). description + name (optional) + framework (html/react/etc)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "Website ka description"},
                        "name": {"type": "string", "description": "Project name (optional)"},
                        "framework": {"type": "string", "description": "html (default) ya react/etc"},
                    },
                    "required": ["description"],
                },
            },
        },
        "func": lambda description, name=None, framework="html": pb.build_website(description, name, framework),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "build_game",
                "description": "Complete game banao. description + name (optional) + kind (pygame/html5)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "Game ka description"},
                        "name": {"type": "string", "description": "Project name (optional)"},
                        "kind": {"type": "string", "description": "pygame (default) ya html5"},
                    },
                    "required": ["description"],
                },
            },
        },
        "func": lambda description, name=None, kind="pygame": pb.build_game(description, name, kind),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "build_android_app",
                "description": "Android app banao (PWA - mobile installable). description + name (optional)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "App ka description"},
                        "name": {"type": "string", "description": "Project name (optional)"},
                    },
                    "required": ["description"],
                },
            },
        },
        "func": lambda description, name=None: pb.build_android_app(description, name),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "build_android_native",
                "description": "Native Android app banao (Kivy + Buildozer se asli .apk). Toolchain ho to compile bhi karega. description + name (optional)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "App ka description"},
                        "name": {"type": "string", "description": "Project name (optional)"},
                    },
                    "required": ["description"],
                },
            },
        },
        "func": lambda description, name=None: pb.build_android_native(description, name),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "minimize_window",
                "description": "Current window minimize karo",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.minimize_window(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "maximize_window",
                "description": "Current window maximize/fullscreen karo",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.maximize_window(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "close_window",
                "description": "Current focused window band karo (Alt+F4)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.close_window(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "switch_window",
                "description": "Alt+Tab se agle windows pe jao. n: kitne window aage jana hai (default 1)",
                "parameters": {
                    "type": "object",
                    "properties": {"n": {"type": "integer", "description": "Kitne windows aage"}},
                    "required": [],
                },
            },
        },
        "func": lambda n=1: pc.switch_window(n),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "show_desktop",
                "description": "Sab windows minimize karke desktop dikhao",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.show_desktop(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "focus_app",
                "description": "Kisi khule app/window pe focus jao. name: app/window ka naam (jaise chrome, notepad)",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string", "description": "App ya window title ka naam"}},
                    "required": ["name"],
                },
            },
        },
        "func": pc.focus_app,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "press_key",
                "description": "Keyboard shortcut press karo. combo: jaise 'ctrl+s', 'alt+f4', 'win+l', 'ctrl+shift+t'",
                "parameters": {
                    "type": "object",
                    "properties": {"combo": {"type": "string", "description": "Key combo (+ se separated)"}},
                    "required": ["combo"],
                },
            },
        },
        "func": pc.press_key,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "type_text",
                "description": "Keyboard se text type karo (jaise kisi app/document mein)",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string", "description": "Jo text type karna hai"}},
                    "required": ["text"],
                },
            },
        },
        "func": pc.type_text,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "mouse_click",
                "description": "Mouse click karo. button: left ya right",
                "parameters": {
                    "type": "object",
                    "properties": {"button": {"type": "string", "enum": ["left", "right"]}},
                    "required": [],
                },
            },
        },
        "func": lambda button="left": pc.mouse_click(button),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "mouse_move",
                "description": "Mouse ko screen ke x,y position pe le jao",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                    },
                    "required": ["x", "y"],
                },
            },
        },
        "func": pc.mouse_move,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "scroll",
                "description": "Scroll karo. amount: positive = up, negative = down (jaise 3 ya -3)",
                "parameters": {
                    "type": "object",
                    "properties": {"amount": {"type": "integer"}},
                    "required": ["amount"],
                },
            },
        },
        "func": pc.scroll,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "set_brightness",
                "description": "Screen brightness set karo (0-100 percent)",
                "parameters": {
                    "type": "object",
                    "properties": {"percent": {"type": "integer", "description": "0 se 100"}},
                    "required": ["percent"],
                },
            },
        },
        "func": pc.set_brightness,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "brightness_up",
                "description": "Brightness 20% badhao (current se)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.brightness_change(20),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "brightness_down",
                "description": "Brightness 20% kam karo (current se)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.brightness_change(-20),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "clipboard_write",
                "description": "Text ko clipboard pe copy karo",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string", "description": "Copy karne wala text"}},
                    "required": ["text"],
                },
            },
        },
        "func": pc.clipboard_write,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "clipboard_read",
                "description": "Clipboard mein kya copied hai wo padho",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.clipboard_read(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "system_info",
                "description": "PC ki health batao: CPU %, RAM %, disk space, battery",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.system_info(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "list_processes",
                "description": "Sabse zyada CPU/RAM khane wale processes dikhao. sort_by: cpu ya ram",
                "parameters": {
                    "type": "object",
                    "properties": {"sort_by": {"type": "string", "enum": ["cpu", "ram"]}},
                    "required": [],
                },
            },
        },
        "func": lambda sort_by="cpu": pc.list_processes(sort_by),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "kill_process",
                "description": "Process/app force band karo. target: process ka naam (jaise chrome) ya PID number",
                "parameters": {
                    "type": "object",
                    "properties": {"target": {"type": "string", "description": "Process name ya PID"}},
                    "required": ["target"],
                },
            },
        },
        "func": pc.kill_process,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "network_info",
                "description": "WiFi network ka naam aur PC ka IP address batao",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.network_info(),
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "PC par file/folder dhundo. name: file ka naam ya part, location: optional folder path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "File naam ya uska hissa"},
                        "location": {"type": "string", "description": "Kahan dhundhna hai (optional)"},
                    },
                    "required": ["name"],
                },
            },
        },
        "func": pc.search_files,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "create_folder",
                "description": "Naya folder banao. path: folder ka poora path",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Folder path"}},
                    "required": ["path"],
                },
            },
        },
        "func": pc.create_folder,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "open_folder",
                "description": "File Explorer mein folder kholo. path: folder ka path",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Folder path"}},
                    "required": ["path"],
                },
            },
        },
        "func": pc.open_folder,
    },
    {
        "schema": {
            "type": "function",
            "function": {
                "name": "empty_recycle_bin",
                "description": "Recycle bin permanently khali karo",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "func": lambda: pc.empty_recycle_bin(),
    },
]

_REGISTRY = {t["schema"]["function"]["name"]: t["func"] for t in TOOLS}


def get_schemas():
    return [t["schema"] for t in TOOLS]


def execute(name, args):
    import logging
    log = logging.getLogger(__name__)
    fn = _REGISTRY.get(name)
    if fn is None:
        return f"Tool '{name}' exist nahi karta."
    try:
        result = fn(**(args or {}))
        # If result is already a string, return as-is
        if isinstance(result, str):
            return result
        # If result is a dict, return JSON
        try:
            import json
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception:
            return str(result)
    except TypeError as e:
        log.error("Tool %s argument error: %s args=%s", name, e, args)
        return f"Error in {name}: galat arguments - {e}"
    except Exception as e:
        log.error("Tool %s failed: %s", name, e, exc_info=True)
        return f"Error in {name}: {type(e).__name__}: {e}"


if __name__ == "__main__":
    print(f"{len(TOOLS)} tools registered")
    print(execute("get_time", {"kind": "time"}))
    print(execute("battery_status", {}))
