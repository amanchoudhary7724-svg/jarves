# JARVIS Setup Guide

## Installation Steps

### Step 1: Activate environment
```bash
cd "C:\Users\soura\Documents\Default Project"
jarvis_env\Scripts\activate
cd jarvis
```

### Step 2: Ollama (Offline Backup) - DONE ✓
Already installed with qwen2.5:1.5b model.

### Step 3: Run Jarvis

**Text mode (testing):**
```bash
python main.py --text
```

**Voice mode (Hindi + English auto-detect):**
```bash
python main.py
```
Phir "Hey Jarvis" bolo aur Hindi ya English mein baat karo!

---

## Email Setup (Gmail)

1. Google Account kholo: https://myaccount.google.com
2. **Security** → **2-Step Verification** enable karo (agar nahi hai)
3. Search karo "**App Passwords**" → ya direct jaao:
   https://myaccount.google.com/apppasswords
4. App name likho "Jarvis" → **Create**
5. Jo 16-letter password mile, usse copy karo
6. `config.json` mein daalo:

```json
"email": {
    "enabled": true,
    "email_address": "tumhara@gmail.com",
    "app_password": "abcd efgh ijkl mnop"
}
```

**Commands:**
- "Email check karo" / "Check emails" → Unread emails
- "Email padho" / "Read email" → Latest email poora
- "Rahul se email dhundo" / "Search email rahul" → Sender/subject search

---

## Calendar Setup (Google Calendar)

1. https://console.cloud.google.com kholo
2. Naya project banao (ya existing select karo)
3. **APIs & Services** → **Library** → "**Google Calendar API**" search → **Enable**
4. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
5. Application type: **Desktop app** → Create
6. **Download JSON** → file ko `jarvis` folder mein `credentials.json` naam se save karo
7. `config.json` mein set karo:

```json
"calendar": {
    "enabled": true,
    "credentials_file": "credentials.json",
    "token_file": "token.json",
    "timezone": "Asia/Kolkata"
}
```

8. Pehli baar calendar command bolne par browser khulega → apna Google account se authorize karo

**Commands:**
- "Aaj kya schedule hai" / "Today's events" → Aaj ke events
- "Agla meeting kab hai" / "Next meeting" → Agla event
- "Calendar events dikhao" / "Upcoming events" → Agle 7 din
- "Event add karo: meeting rahul se kal 3 baje" → Event create

---

## Multi-Language (Auto-Detect)

Kuch karne ki zaroorat nahi — Jarvis khud detect karta hai:
- **Hindi/Hinglish** bologe → Madhur voice mein jawab dega
- **English** bologe → Guy voice mein jawab dega

---

## Troubleshooting

**TTS nahi bol raha?** → Internet chahiye edge-tts ke liye. Offline mode automatically use hoga.

**STT kaam nahi kar raha?** → Mic permission check karo Windows Settings mein.

**LLM slow hai?** → Ollama local model CPU pe chalta hai, thoda wait karo. NVIDIA key dalne se speed + quality badhegi.

**Email login fail?** → Regular password nahi chalega, sirf App Password (16 letters).

**Calendar OAuth error?** → credentials.json sahi jagah par hai? Google Cloud project mein Calendar API enabled hai?
