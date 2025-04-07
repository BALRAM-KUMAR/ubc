import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings

async def send_credentials_email(email: str, username: str, password: str):
    subject = "Your Login Credentials"
    body = f"""
    Hello {username},
    
    Your account has been created successfully.
    
    Email: {email}
    Password: {password}
    
    Please change your password after logging in.
    """

    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_SENDER
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_SENDER, email, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")