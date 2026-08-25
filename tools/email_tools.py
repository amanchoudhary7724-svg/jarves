import email
import imaplib
import re
from email.header import decode_header

from config_loader import CFG


def _is_configured():
    cfg = CFG.get("email", {})
    return bool(cfg.get("enabled") and cfg.get("email_address") and cfg.get("app_password"))


def _connect():
    if not _is_configured():
        return None, "Email setup nahi hua hai. SETUP.md mein steps dekho: Gmail app password banao aur config.json mein daalo."
    cfg = CFG["email"]
    try:
        mail = imaplib.IMAP4_SSL(cfg["imap_server"], cfg["imap_port"])
        mail.login(cfg["email_address"], cfg["app_password"])
        mail.select("inbox")
        return mail, None
    except imaplib.IMAP4.error as e:
        return None, f"Gmail login fail hua. App password check karo ({e})."
    except Exception as e:
        return None, f"Email server se connect nahi ho paya ({type(e).__name__})."


def _decode_subject(raw):
    if not raw:
        return "(No subject)"
    parts = decode_header(raw)
    out = []
    for data, charset in parts:
        if isinstance(data, bytes):
            out.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(data)
    return "".join(out).strip()


def _extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            text = re.sub(r"<[^>]+>", " ", text)
            return re.sub(r"\s+", " ", text)
    return ""


def check_emails(limit=5):
    limit = max(1, min(10, int(limit)))
    mail, err = _connect()
    if err:
        return err
    try:
        status, data = mail.search(None, "UNSEEN")
        if status != "OK":
            return "Emails fetch nahi ho paye."
        ids = data[0].split()
        if not ids:
            return "Koi naya email nahi hai. Sab padh liya hai!"
        recent = list(reversed(ids))[:limit]
        lines = [f"{len(ids)} unread emails hain, latest {len(recent)}:"]
        for i, eid in enumerate(recent, 1):
            _, msg_data = mail.fetch(eid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            frm = _decode_subject(msg.get("From", ""))
            sender_match = re.search(r"<(.+?)>", frm)
            sender = sender_match.group(1) if sender_match else frm
            subject = _decode_subject(msg.get("Subject"))
            date = (msg.get("Date") or "")[:16]
            lines.append(f"{i}. {sender} ne likha '{subject}' ({date})")
        return "\n".join(lines)
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def read_latest_email():
    mail, err = _connect()
    if err:
        return err
    try:
        status, data = mail.search(None, "ALL")
        if status != "OK":
            return "Emails fetch nahi ho paye."
        ids = data[0].split()
        if not ids:
            return "Inbox khali hai."
        latest = ids[-1]
        _, msg_data = mail.fetch(latest, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        frm = _decode_subject(msg.get("From", ""))
        subject = _decode_subject(msg.get("Subject"))
        body = _extract_body(msg)
        snippet = body[:300].strip()
        return f"From: {frm}\nSubject: {subject}\n\n{snippet}"
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def search_emails(query, limit=3):
    query = str(query).strip()
    if not query:
        return "Kya dhundhna hai batao."
    limit = max(1, min(5, int(limit)))
    mail, err = _connect()
    if err:
        return err
    try:
        status, data = mail.search(None, f'(OR SUBJECT "{query}" FROM "{query}")')
        if status != "OK" or not data[0].split():
            return f"'{query}' se related koi email nahi mila."
        matched = list(reversed(data[0].split()))[:limit]
        lines = [f"'{query}' ke {len(matched)} emails mile:"]
        for i, eid in enumerate(matched, 1):
            _, msg_data = mail.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            frm = _decode_subject(msg.get("From", ""))
            subject = _decode_subject(msg.get("Subject"))
            lines.append(f"{i}. {frm} - '{subject}'")
        return "\n".join(lines)
    except Exception:
        return f"Search fail hua. Query simple rakho, jaise sirf naam ya subject word."
    finally:
        try:
            mail.logout()
        except Exception:
            pass
