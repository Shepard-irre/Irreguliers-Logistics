"""
Daemon de notification raffinerie.
Vérifie toutes les 5 minutes si des jobs sont terminés et envoie un email au mineur.
Usage : python refinery_notifier.py
"""
import sys
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).parent))
from uex_library import UEXManager

CHECK_INTERVAL = 300  # 5 minutes

cfg = dotenv_values(Path(__file__).parent / '.env')
GMAIL_USER = cfg.get('GMAIL_USER')
GMAIL_APP_PASSWORD = cfg.get('GMAIL_APP_PASSWORD')

# Mapping username → email (à compléter si besoin)
USER_EMAILS = {
    'Shepard40': 'yann.manchon@gmail.com',
    'Darkias':   'darkias44@gmail.com',
}

def send_email(to, subject, body):
    msg = MIMEMultipart('alternative')
    msg['From']    = GMAIL_USER
    msg['To']      = to
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as srv:
        srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_USER, to, msg.as_string())

def check_and_notify(uex):
    jobs = uex.get_jobs_due_for_notification()
    if jobs.empty:
        return
    for _, job in jobs.iterrows():
        username = job['user']
        email = USER_EMAILS.get(username)
        if not email:
            print(f"[NOTIF] Pas d'email pour {username}, job {job['id']} ignoré")
            uex.mark_job_notified(int(job['id']))
            continue
        subject = f"[Les Irréguliers] Raffinage terminé — {job['commodity_name']}"
        body = (
            f"Yo {username},\n\n"
            f"Ton job de raffinage est probablement terminé !\n\n"
            f"  Minerai   : {job['commodity_name']}\n"
            f"  Quantité  : {job['quantity_raw']} SCU brut → ~{job['quantity_estimated']} SCU raffiné\n"
            f"  Station   : {job['terminal_name']}\n"
            f"  Méthode   : {job['method']}\n\n"
            f"N'oublie pas de confirmer le job dans l'app une fois récupéré en jeu.\n\n"
            f"— Les Irréguliers Hub Logistique"
        )
        try:
            send_email(email, subject, body)
            print(f"[NOTIF] Email envoyé à {email} pour job {job['id']} ({job['commodity_name']})")
        except Exception as e:
            print(f"[NOTIF] Erreur envoi email : {e}")
        uex.mark_job_notified(int(job['id']))

if __name__ == '__main__':
    print(f"[NOTIF] Daemon démarré — check toutes les {CHECK_INTERVAL//60} min")
    uex = UEXManager()
    while True:
        try:
            check_and_notify(uex)
        except Exception as e:
            print(f"[NOTIF] Erreur : {e}")
        time.sleep(CHECK_INTERVAL)
