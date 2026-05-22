"""
Daemon mail — vérifie les mails de Darkias et répond automatiquement.
Lancement : python mail_daemon.py
Via Task Scheduler : toutes les 5 min

Modes :
  - ANTHROPIC_API_KEY présente → réponse IA (Claude Haiku)
  - Sinon → accusé de réception automatique
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER        = os.getenv('GMAIL_USER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
NOTIFY_EMAIL      = os.getenv('NOTIFY_EMAIL', 'darkias44@gmail.com')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

IMAP_HOST = 'imap.gmail.com'
IMAP_PORT = 993
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 465

# Fichier de suivi des mails déjà traités
REPLIED_LOG = Path(__file__).parent / '.mail_replied.json'

PROJECT_CONTEXT = """
Tu es Claudius, l'IA de développement du projet "Les Irréguliers - Hub Logistique".
C'est une application Streamlit de gestion logistique pour l'organisation Star Citizen "Les Irréguliers".

Ton rôle : assistant technique du projet, tu réponds aux mails de Darkias (co-dev et chef de Yann).
Stack : Python, Streamlit, SQLite, API UEX Corp, WordPress (migration en cours).

Règles de réponse :
- Sois direct et concis
- Si Darkias pose une question technique, réponds précisément
- Si c'est une info (ex: URL de la copie WP), confirme que tu as bien reçu et ce que ça débloque
- Ton de la conversation : décontracté, on se tutoie
- Signe toujours "Claudius"
- Langue : français
"""


def load_replied():
    if REPLIED_LOG.exists():
        return set(json.loads(REPLIED_LOG.read_text()))
    return set()


def save_replied(replied_set):
    REPLIED_LOG.write_text(json.dumps(list(replied_set)))


def decode_str(s):
    if s is None:
        return ''
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or 'utf-8', errors='replace'))
        else:
            result.append(part)
    return ''.join(result)


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get('Content-Disposition', ''))
            if ct == 'text/plain' and 'attachment' not in cd:
                charset = part.get_content_charset() or 'utf-8'
                return part.get_payload(decode=True).decode(charset, errors='replace').strip()
    else:
        charset = msg.get_content_charset() or 'utf-8'
        return msg.get_payload(decode=True).decode(charset, errors='replace').strip()
    return ''


def generate_ai_reply(mail_body, mail_subject):
    """Génère une réponse via Claude Haiku."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""Mail reçu de Darkias :
Sujet : {mail_subject}
---
{mail_body}
---
Rédige une réponse courte et pertinente. Signe "Claudius"."""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=PROJECT_CONTEXT,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


def generate_ack_reply(mail_subject):
    """Réponse automatique simple si pas d'API key."""
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    return f"""Salut Darkias,

Mail bien reçu ({now}).
Yann sera au courant au prochain check-in avec Claudius.

À plus,
Claudius"""


def send_reply(to, subject, body, reply_to_msg=None):
    """Envoie un mail via Gmail SMTP."""
    msg = MIMEMultipart('alternative')
    msg['From']    = GMAIL_USER
    msg['To']      = to
    msg['Subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
    if reply_to_msg:
        msg['In-Reply-To'] = reply_to_msg
        msg['References']  = reply_to_msg

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as srv:
        srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_USER, to, msg.as_string())


def check_and_reply():
    replied = load_replied()
    new_replies = []

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select('INBOX')

    _, data = mail.search(None, f'(FROM "{NOTIFY_EMAIL}" UNSEEN)')
    ids = data[0].split()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(ids)} mail(s) non lu(s) de {NOTIFY_EMAIL}")

    for uid in ids:
        uid_str = uid.decode()
        _, msg_data = mail.fetch(uid, '(RFC822 UID)')
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        msg_id   = msg.get('Message-ID', uid_str)
        subject  = decode_str(msg.get('Subject', ''))
        body     = get_body(msg)
        sender   = decode_str(msg.get('From', ''))

        if msg_id in replied:
            print(f"  → Déjà traité : {subject}")
            continue

        print(f"  → Traitement : {subject}")

        # Génère la réponse
        if ANTHROPIC_API_KEY:
            try:
                reply_body = generate_ai_reply(body, subject)
                mode = "IA"
            except Exception as e:
                print(f"  ! Erreur API Claude : {e}")
                reply_body = generate_ack_reply(subject)
                mode = "ACK"
        else:
            reply_body = generate_ack_reply(subject)
            mode = "ACK"

        # Envoie la réponse
        try:
            send_reply(NOTIFY_EMAIL, subject, reply_body, reply_to_msg=msg_id)
            print(f"  ✓ Réponse envoyée ({mode})")
            replied.add(msg_id)
            new_replies.append({'subject': subject, 'mode': mode})
            # Marque comme lu
            mail.store(uid, '+FLAGS', '\\Seen')
        except Exception as e:
            print(f"  ! Erreur envoi : {e}")

    mail.logout()
    save_replied(replied)
    return new_replies


if __name__ == '__main__':
    results = check_and_reply()
    if results:
        print(f"\n✓ {len(results)} réponse(s) envoyée(s)")
    else:
        print("✓ Rien à traiter")
