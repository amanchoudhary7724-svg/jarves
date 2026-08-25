import os
import sys
import json
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import CFG, open_browser

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False


SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

_youtube_service = None


def _get_credentials():
    cfg = CFG.get("youtube", {})
    creds_file = cfg.get("credentials_file", "credentials.json")
    token_file = cfg.get("token_file", "youtube_token.json")

    creds = None
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception:
            pass

    def _missing_scope(c):
        if c is None:
            return True
        have = set(getattr(c, "scopes", []) or [])
        need = set(SCOPES)
        return not need.issubset(have)

    if _missing_scope(creds):
        if not os.path.exists(creds_file):
            return None, f"Credentials file not found: {creds_file}. Download from Google Cloud Console."
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        return creds, None

    if not creds or not creds.valid:
        refreshed = False
        if creds and creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                refreshed = True
            except Exception as e:
                refreshed = False
        if not refreshed:
            if not os.path.exists(creds_file):
                return None, f"Credentials file not found: {creds_file}. Download from Google Cloud Console."
            try:
                flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(token_file, "w") as f:
                    f.write(creds.to_json())
                return creds, None
            except Exception as e:
                return None, (f"YouTube auth failed: {type(e).__name__}: {e}. "
                              f"If scope error, delete {token_file} and re-run 'youtube check auth'.")
        else:
            with open(token_file, "w") as f:
                f.write(creds.to_json())

    return creds, None


def _get_service():
    global _youtube_service
    if _youtube_service is not None:
        return _youtube_service, None

    if not YOUTUBE_API_AVAILABLE:
        return None, "Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib"

    cfg = CFG.get("youtube", {})
    if not cfg.get("enabled", False):
        return None, "YouTube API not enabled in config.json"

    creds, err = _get_credentials()
    if err:
        return None, err

    try:
        _youtube_service = build("youtube", "v3", credentials=creds)
        return _youtube_service, None
    except Exception as e:
        return None, f"Failed to create YouTube service: {type(e).__name__}: {e}"


_analytics_service = None


def _get_analytics_service():
    global _analytics_service
    if _analytics_service is not None:
        return _analytics_service, None

    if not YOUTUBE_API_AVAILABLE:
        return None, "Google API libraries not installed."

    cfg = CFG.get("youtube", {})
    if not cfg.get("enabled", False):
        return None, "YouTube API not enabled in config.json"

    creds, err = _get_credentials()
    if err:
        return None, err

    try:
        _analytics_service = build("youtubeAnalytics", "v2", credentials=creds)
        return _analytics_service, None
    except Exception as e:
        return None, f"Failed to create Analytics service: {type(e).__name__}: {e}"


def youtube_search(query, max_results=5):
    if not query or not query.strip():
        return "Search query khali hai."

    service, err = _get_service()
    if err:
        return f"YouTube search failed: {err}"

    try:
        request = service.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=min(max_results, 10),
            order="relevance"
        )
        response = request.execute()

        items = response.get("items", [])
        if not items:
            return f"'{query}' ke liye koi video nahi mili."

        lines = [f"YouTube search results for '{query}':"]
        for i, item in enumerate(items, 1):
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            channel = item["snippet"]["channelTitle"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            lines.append(f"{i}. {title} — {channel} ({url})")

        return "\n".join(lines)

    except HttpError as e:
        return f"YouTube API error: {e}"
    except Exception as e:
        return f"Search error: {type(e).__name__}: {e}"


def _extract_video_id(query_or_id):
    if "youtube.com/watch?v=" in query_or_id:
        return query_or_id.split("v=")[1].split("&")[0]
    if "youtu.be/" in query_or_id:
        return query_or_id.split("youtu.be/")[1].split("?")[0]
    if len(query_or_id) == 11 and all(c.isalnum() or c in "-_" for c in query_or_id):
        return query_or_id
    return None


def youtube_play_video(query_or_id):
    if not query_or_id or not query_or_id.strip():
        return "Video query ya ID khali hai."

    video_id = _extract_video_id(query_or_id)
    if video_id:
        url = f"https://www.youtube.com/watch?v={video_id}"
        open_browser(url)
        return f"Video chala raha hoon: {url}"

    service, err = _get_service()
    if service is not None:
        try:
            request = service.search().list(
                part="snippet",
                q=query_or_id,
                type="video",
                maxResults=1,
                order="relevance"
            )
            response = request.execute()

            items = response.get("items", [])
            if items:
                video = items[0]
                video_id = video["id"]["videoId"]
                title = video["snippet"]["title"]
                url = f"https://www.youtube.com/watch?v={video_id}"
                open_browser(url)
                return f"Chala raha hoon: {title} ({url})"
        except Exception:
            pass

    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query_or_id)}"
    open_browser(url)
    return f"YouTube par '{query_or_id}' search kar diya (browser mein khul gaya)."


def youtube_get_video_details(video_id):
    service, err = _get_service()
    if err:
        return f"YouTube details failed: {err}"

    try:
        request = service.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()

        items = response.get("items", [])
        if not items:
            return "Video nahi mili."

        video = items[0]
        snippet = video["snippet"]
        stats = video.get("statistics", {})
        content = video.get("contentDetails", {})

        return {
            "id": video_id,
            "title": snippet["title"],
            "description": snippet["description"][:500],
            "channel": snippet["channelTitle"],
            "published_at": snippet["publishedAt"],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "duration": content.get("duration", ""),
        }

    except HttpError as e:
        return f"YouTube API error: {e}"
    except Exception as e:
        return f"Details error: {type(e).__name__}: {e}"


def youtube_get_my_videos(max_results=10):
    service, err = _get_service()
    if err:
        return f"YouTube my videos failed: {err}"

    try:
        request = service.search().list(
            part="snippet",
            forMine=True,
            type="video",
            maxResults=min(max_results, 50),
            order="date"
        )
        response = request.execute()

        items = response.get("items", [])
        if not items:
            return "Aapke channel par koi video nahi hai."

        lines = ["Aapke latest videos:"]
        for i, item in enumerate(items, 1):
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            published = item["snippet"]["publishedAt"][:10]
            url = f"https://www.youtube.com/watch?v={video_id}"
            lines.append(f"{i}. {title} ({published}) — {url}")

        return "\n".join(lines)

    except HttpError as e:
        return f"YouTube API error: {e}"
    except Exception as e:
        return f"My videos error: {type(e).__name__}: {e}"


def youtube_check_auth():
    service, err = _get_service()
    if err:
        return f"Not authenticated: {err}"
    return "YouTube API authenticated successfully."


def youtube_upload_video(file_path, title, description="", tags=None, category_id="22", privacy_status="private", thumbnail_path=None):
    if not file_path or not os.path.exists(file_path):
        return f"File not found: {file_path}"

    if not title or not title.strip():
        return "Title khali hai."

    service, err = _get_service()
    if err:
        return f"YouTube upload failed: {err}"

    try:
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(file_path, chunksize=1024*1024, resumable=True)
        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"Upload progress: {progress}%")

        video_id = response.get("id")
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
            except Exception as e:
                print(f"Thumbnail upload failed: {e}")

        return f"Video uploaded successfully! Video ID: {video_id}\nURL: {video_url}"

    except HttpError as e:
        return f"YouTube API error: {e}"
    except Exception as e:
        return f"Upload error: {type(e).__name__}: {e}"


def youtube_update_video(video_id, title=None, description=None, tags=None, privacy_status=None):
    service, err = _get_service()
    if err:
        return f"YouTube update failed: {err}"

    try:
        request = service.videos().list(part="snippet,status", id=video_id)
        response = request.execute()
        items = response.get("items", [])
        if not items:
            return "Video nahi mili."

        video = items[0]
        snippet = video["snippet"]
        status = video["status"]

        if title:
            snippet["title"] = title[:100]
        if description is not None:
            snippet["description"] = description[:5000]
        if tags is not None:
            snippet["tags"] = tags
        if privacy_status:
            status["privacyStatus"] = privacy_status

        update_request = service.videos().update(
            part="snippet,status",
            body={"id": video_id, "snippet": snippet, "status": status}
        )
        update_request.execute()
        return f"Video {video_id} updated successfully."

    except HttpError as e:
        return f"YouTube API error: {e}"
    except Exception as e:
        return f"Update error: {type(e).__name__}: {e}"


def youtube_delete_video(video_id):
    if not video_id:
        return "Video ID khali hai."
    service, err = _get_service()
    if err:
        return f"YouTube delete failed: {err}"
    try:
        service.videos().delete(id=video_id).execute()
        return f"Video {video_id} delete ho gaya (permanently)."
    except HttpError as e:
        return f"YouTube API error: {e}"
    except Exception as e:
        return f"Delete error: {type(e).__name__}: {e}"


if __name__ == "__main__":
    print("Testing YouTube tools...")
    print(youtube_check_auth())
    print("\n--- Search Test ---")
    print(youtube_search("hanuman chalisa", 3))
    print("\n--- Play Test ---")
    print(youtube_play_video("hanuman chalisa"))