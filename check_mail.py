"""
Lecture boite Gmail — replies de Darkias (et autres).
Usage : python check_mail.py [--all] [--from darkias44@gmail.com] [--n 10]
"""

import imaplib
import email
from email.header import decode_header
import os
import sys
import argparse
from dotenv import load_dotenv
from datetime import datetime

# Force UTF-8 sur stdout (Windows cp1252 plante sur certains caractères Unicode)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
NOTIFY_EMAIL = os.getenv('NOTIFY_EMAIL', 'darkias44@gmail.com')

IMAP_HOST = 'imap.gmail.com'
IMAP_PORT = 993


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
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get('Content-Disposition', ''))
            if ct == 'text/plain' and 'attachment' not in cd:
                charset = part.get_content_charset() or 'utf-8'
                body = part.get_payload(decode=True).decode(charset, errors='replace')
                break
    else:
        charset = msg.get_content_charset() or 'utf-8'
        body = msg.get_payload(decode=True).decode(charset, errors='replace')
    return body.strip()


def fetch_mails(sender_filter=None, n=10, unread_only=False, folder='INBOX'):
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select(folder)

    criteria = []
    if unread_only:
        criteria.append('UNSEEN')
    if sender_filter:
        criteria.append(f'FROM "{sender_filter}"')

    search_str = '(' + ' '.join(criteria) + ')' if criteria else 'ALL'
    _, data = mail.search(None, search_str)

    ids = data[0].split()
    ids = ids[-n:]  # les N plus récents
    ids = list(reversed(ids))  # plus récent en premier

    results = []
    for uid in ids:
        _, msg_data = mail.fetch(uid, '(RFC822)')
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        subject = decode_str(msg.get('Subject', '(sans sujet)'))
        sender = decode_str(msg.get('From', ''))
        date_str = msg.get('Date', '')
        body = get_body(msg)

        results.append({
            'uid': uid.decode(),
            'msg_id': msg.get('Message-ID', ''),
            'from': sender,
            'subject': subject,
            'date': date_str,
            'body': body,
        })

    mail.logout()
    return results


def print_mails(mails):
    if not mails:
        print("Aucun mail trouvé.")
        return
    sep = '-' * 70
    for i, m in enumerate(mails):
        print(f"\n{sep}")
        print(f"  De      : {m['from']}")
        print(f"  Sujet   : {m['subject']}")
        print(f"  Date    : {m['date']}")
        print(f"  Msg-ID  : {m.get('msg_id', '')}")
        print(f"{sep}")
        # Tronque le body si trop long
        body = m['body']
        if len(body) > 1000:
            body = body[:1000] + '\n[... tronqué]'
        print(body)
    print(f"\n{sep}")
    print(f"  {len(mails)} mail(s) affiché(s)")


def send_reply(to, subject, body, reply_to_msg_id=None):
    """Envoie un mail de réponse via Gmail SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart as _MM
    msg = _MM('alternative')
    msg['From']    = GMAIL_USER
    msg['To']      = to
    msg['Subject'] = subject if subject.startswith('Re:') else f'Re: {subject}'
    if reply_to_msg_id:
        msg['In-Reply-To'] = reply_to_msg_id
        msg['References']  = reply_to_msg_id
    from email.mime.text import MIMEText as _MT
    msg.attach(_MT(body, 'plain', 'utf-8'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as srv:
        srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_USER, to, msg.as_string())


def mark_replied(msg_id):
    """Marque un Message-ID comme traité dans .mail_replied.json."""
    from pathlib import Path
    import json
    log = Path(__file__).parent / '.mail_replied.json'
    replied = set(json.loads(log.read_text())) if log.exists() else set()
    replied.add(msg_id)
    log.write_text(json.dumps(list(replied)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Lecture/envoi mails Gmail')
    parser.add_argument('--from', dest='sender', default=NOTIFY_EMAIL)
    parser.add_argument('--all', dest='all_senders', action='store_true')
    parser.add_argument('--n', type=int, default=5)
    parser.add_argument('--unread', action='store_true')
    parser.add_argument('--folder', default='INBOX')
    # Répondre à un mail existant
    parser.add_argument('--reply', metavar='MSG_ID')
    parser.add_argument('--reply-body', metavar='BODY')
    # Envoyer un nouveau mail sans fichier temp
    parser.add_argument('--send', action='store_true', help='Envoie un nouveau mail')
    parser.add_argument('--to', default=NOTIFY_EMAIL)
    parser.add_argument('--subject', metavar='SUBJECT')
    parser.add_argument('--body', metavar='BODY')
    parser.add_argument('--in-reply-to', metavar='MSG_ID')
    args = parser.parse_args()

    if args.send:
        if not args.subject or not args.body:
            print("--subject et --body requis avec --send")
            exit(1)
        send_reply(args.to, args.subject, args.body, reply_to_msg_id=args.in_reply_to)
        if args.in_reply_to:
            mark_replied(args.in_reply_to)
        print("Mail envoye")
    elif args.reply:
        if not args.reply_body:
            print("--reply-body requis avec --reply")
            exit(1)
        send_reply(NOTIFY_EMAIL, 'Re: message', args.reply_body, reply_to_msg_id=args.reply)
        mark_replied(args.reply)
        print("Reponse envoyee")
    else:
        sender = None if args.all_senders else args.sender
        print(f"Connexion Gmail ({GMAIL_USER})...")
        if sender:
            print(f"Filtre : mails de {sender}")
        mails = fetch_mails(sender_filter=sender, n=args.n, unread_only=args.unread, folder=args.folder)
        print_mails(mails)
