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
    sep = '─' * 70
    for i, m in enumerate(mails):
        print(f"\n{sep}")
        print(f"  De      : {m['from']}")
        print(f"  Sujet   : {m['subject']}")
        print(f"  Date    : {m['date']}")
        print(f"{sep}")
        # Tronque le body si trop long
        body = m['body']
        if len(body) > 1000:
            body = body[:1000] + '\n[... tronqué]'
        print(body)
    print(f"\n{sep}")
    print(f"  {len(mails)} mail(s) affiché(s)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Lecture mails Gmail')
    parser.add_argument('--from', dest='sender', default=NOTIFY_EMAIL,
                        help=f'Filtre expéditeur (défaut: {NOTIFY_EMAIL})')
    parser.add_argument('--all', dest='all_senders', action='store_true',
                        help='Tous les expéditeurs')
    parser.add_argument('--n', type=int, default=5,
                        help='Nombre de mails à afficher (défaut: 5)')
    parser.add_argument('--unread', action='store_true',
                        help='Uniquement les non lus')
    parser.add_argument('--folder', default='INBOX',
                        help='Dossier IMAP (défaut: INBOX)')
    args = parser.parse_args()

    sender = None if args.all_senders else args.sender
    print(f"Connexion Gmail ({GMAIL_USER})...")
    if sender:
        print(f"Filtre : mails de {sender}")
    mails = fetch_mails(sender_filter=sender, n=args.n, unread_only=args.unread, folder=args.folder)
    print_mails(mails)
