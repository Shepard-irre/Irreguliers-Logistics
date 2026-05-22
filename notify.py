import smtplib
import os
import sys
import subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_notification(subject, body):
    gmail_user = os.getenv('GMAIL_USER')
    gmail_password = os.getenv('GMAIL_APP_PASSWORD')
    to_email = os.getenv('NOTIFY_EMAIL')

    if not all([gmail_user, gmail_password, to_email]):
        print("Credentials manquants dans .env")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"Claudius <{gmail_user}>"
    msg['To'] = to_email

    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())
        print(f"Mail envoyé à {to_email}")
        return True
    except Exception as e:
        print(f"Erreur envoi mail : {e}")
        return False

if __name__ == "__main__":
    # Récupère les infos du dernier commit
    try:
        commit_msg = subprocess.check_output(['git', 'log', '-1', '--pretty=%s'], text=True).strip()
        commit_hash = subprocess.check_output(['git', 'log', '-1', '--pretty=%h'], text=True).strip()
        commit_author = subprocess.check_output(['git', 'log', '-1', '--pretty=%an'], text=True).strip()
        commit_date = subprocess.check_output(['git', 'log', '-1', '--pretty=%ci'], text=True).strip()
        diff_stat = subprocess.check_output(['git', 'diff', 'HEAD~1', '--stat'], text=True).strip()
    except:
        commit_msg = sys.argv[1] if len(sys.argv) > 1 else "Mise à jour"
        commit_hash = "?"
        commit_author = "Claudius"
        commit_date = ""
        diff_stat = ""

    subject = f"[Irréguliers] {commit_msg}"

    body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: #e0e0e0; padding: 20px; border-radius: 8px;">
            <h2 style="color: #00d4ff;">🚀 Les Irréguliers — Hub Logistique</h2>
            <hr style="border-color: #333;">
            <h3 style="color: #fff;">{commit_msg}</h3>
            <table style="width:100%; color: #ccc;">
                <tr><td style="padding: 4px 0;"><b>Commit</b></td><td><code style="color:#00d4ff">{commit_hash}</code></td></tr>
                <tr><td style="padding: 4px 0;"><b>Auteur</b></td><td>{commit_author}</td></tr>
                <tr><td style="padding: 4px 0;"><b>Date</b></td><td>{commit_date}</td></tr>
            </table>
            <hr style="border-color: #333;">
            <pre style="background: #0d0d1a; padding: 12px; border-radius: 4px; color: #aaa; font-size: 12px;">{diff_stat}</pre>
            <hr style="border-color: #333;">
            <p style="color: #666; font-size: 11px;">— Claudius 🤖</p>
        </div>
    </body></html>
    """

    send_notification(subject, body)
