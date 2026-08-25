import json
import urllib.parse
import urllib.request

from config_loader import open_browser

WMO_CODES = {
    0: "saaf aasman", 1: "mostly saaf", 2: "thode baadal", 3: "baadal chhaye hue",
    45: "kohra", 48: "kohra", 51: "halki phuhaar", 53: "phuhaar", 55: "tez phuhaar",
    61: "halki baarish", 63: "baarish", 65: "tez baarish", 71: "halki barfbari",
    73: "barfbari", 75: "tez barfbari", 80: "baarish ke chhintsay", 81: "baarish",
    82: "tez baarish", 95: "toofan aur badal garaj", 96: "olon ke saath toofan",
    99: "olon ke saath khatarnak toofan",
}


def _fetch_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "JarvisAssistant/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def web_search(query):
    from ddgs import DDGS

    results = DDGS().text(query, max_results=4)
    if not results:
        return f"'{query}' par kuch nahi mila."
    lines = [f"Search results for '{query}':"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        body = (r.get("body", "") or "")[:250]
        lines.append(f"{i}. {title}: {body}")
    return "\n".join(lines)


def youtube_play(query):
    from ddgs import DDGS

    results = DDGS().videos(query, max_results=3)
    if not results:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        open_browser(url)
        return f"YouTube par '{query}' search kar diya, par direct video nahi mili."
    first = results[0]
    title = first.get("title", query)
    url = first.get("content") or first.get("url")
    if url and "youtube.com" not in url and "youtu.be" not in url:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        open_browser(url)
        return f"Video nahi mila, YouTube par '{query}' search kar diya."
    open_browser(url)
    return f"Chala raha hoon: {title}"


def wikipedia_summary(topic):
    import wikipedia

    topic = topic.strip()
    try:
        wikipedia.set_lang("hi")
        return wikipedia.summary(topic, sentences=3, auto_suggest=True)
    except Exception:
        pass
    try:
        wikipedia.set_lang("en")
        summary_text = wikipedia.summary(topic, sentences=3, auto_suggest=True)
        return summary_text
    except wikipedia.DisambiguationError as e:
        return f"'{topic}' kai cheezon ka naam hai, jaise: {', '.join(e.options[:5])}. Kaunsi bataiye?"
    except Exception:
        return f"'{topic}' ke baare mein jaankari nahi mil payi."


def get_weather(city="Delhi"):
    try:
        geo_url = (
            "https://geocoding-api.open-meteo.com/v1/search?name="
            + urllib.parse.quote(city)
            + "&count=1&language=en&format=json"
        )
        geo = _fetch_json(geo_url)
        results = geo.get("results")
        if not results:
            return f"{city} naam ki jagah nahi mil payi."
        loc = results[0]
        lat, lon, name = loc["latitude"], loc["longitude"], loc["name"]
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
        )
        data = _fetch_json(weather_url)["current"]
        temp = int(data["temperature_2m"])
        desc = WMO_CODES.get(int(data["weather_code"]), "mausam saamanya hai")
        humidity = data["relative_humidity_2m"]
        wind = int(data["wind_speed_10m"])
        return (
            f"{name} mein abhi temperature {temp} degree hai, {desc}. "
            f"Nummi {humidity} percent aur hawa {wind} kilometre prati ghanta hai."
        )
    except Exception as e:
        return f"Mausam ki jaankari nahi mil payi ({type(e).__name__})."
