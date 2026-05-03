import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FRONTEND_URL = os.getenv("FRONTEND_URL")

PRIMARY_COLOR = "#113d9e"
SECONDARY_COLOR = "#eeaa55"

LOGO_URL = f"{FRONTEND_URL}/static/images/logo_neon.png"


def _send_email(to_email: str, subject: str, html_content: str, text_content: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

# VERIFY EMAIL

def send_verification_email(to_email: str, token: str):
    verify_url = f"{FRONTEND_URL}/verify?token={token}"

    subject = "Confirma a tua conta - CountLight"

    text = f"""
Olá!

Confirma a tua conta:

{verify_url}

Se não foste tu, ignora este email.
"""

    html = f"""
    <html>
    <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,sans-serif;">
        <div style="max-width:520px;margin:40px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 5px 20px rgba(0,0,0,0.05);">
            
            <!-- HEADER -->
            <div style="background:{PRIMARY_COLOR};padding:20px;text-align:center;">
                <img src="{LOGO_URL}" alt="CountLight" style="height:40px;">
            </div>

            <!-- CONTENT -->
            <div style="padding:30px;text-align:center;">
                <h2 style="margin-bottom:10px;color:{PRIMARY_COLOR};">
                    Confirma a tua conta
                </h2>

                <p style="color:#555;font-size:15px;line-height:1.5;">
                    Obrigado por te registares no CountLight.<br>
                    Clica no botão abaixo para ativar a tua conta.
                </p>

                <a href="{verify_url}" 
                   style="display:inline-block;margin-top:25px;padding:14px 28px;background:{SECONDARY_COLOR};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">
                   Confirmar Conta
                </a>

                <p style="margin-top:25px;font-size:13px;color:#888;">
                    Ou utiliza este link:<br>
                    <a href="{verify_url}" style="color:{PRIMARY_COLOR};">
                        {verify_url}
                    </a>
                </p>
            </div>

            <!-- FOOTER -->
            <div style="padding:20px;text-align:center;font-size:12px;color:#999;border-top:1px solid #eee;">
                Se não criaste esta conta, podes ignorar este email.
            </div>
        </div>
    </body>
    </html>
    """

    _send_email(to_email, subject, html, text)

# RESET PASSWORD

def send_reset_email(to_email: str, token: str):
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"

    subject = "Reset da palavra-passe - CountLight"

    text = f"""
Olá!

Redefine a tua palavra-passe:

{reset_url}

Se não foste tu, ignora este email.
"""

    html = f"""
    <html>
    <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,sans-serif;">
        <div style="max-width:520px;margin:40px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 5px 20px rgba(0,0,0,0.05);">
            
            <!-- HEADER -->
            <div style="background:{PRIMARY_COLOR};padding:20px;text-align:center;">
                <img src="{LOGO_URL}" alt="CountLight" style="height:40px;">
            </div>

            <!-- CONTENT -->
            <div style="padding:30px;text-align:center;">
                <h2 style="margin-bottom:10px;color:{PRIMARY_COLOR};">
                    Redefinir palavra-passe
                </h2>

                <p style="color:#555;font-size:15px;line-height:1.5;">
                    Recebemos um pedido para redefinir a tua password.
                </p>

                <a href="{reset_url}" 
                   style="display:inline-block;margin-top:25px;padding:14px 28px;background:{SECONDARY_COLOR};color:#ffffff;text-decoration:none;border-radius:8px;font-weight:bold;">
                   Redefinir Password
                </a>

                <p style="margin-top:25px;font-size:13px;color:#888;">
                    Ou utiliza este link:<br>
                    <a href="{reset_url}" style="color:{PRIMARY_COLOR};">
                        {reset_url}
                    </a>
                </p>
            </div>

            <!-- FOOTER -->
            <div style="padding:20px;text-align:center;font-size:12px;color:#999;border-top:1px solid #eee;">
                Se não pediste esta alteração, ignora este email.
            </div>
        </div>
    </body>
    </html>
    """

    _send_email(to_email, subject, html, text)

# LOGIN 2FA CODE

def send_login_code_email(to_email: str, code: str):
    subject = "Código de verificação - CountLight"

    text = f"""
Olá!

O teu código de verificação é:

{code}

Este código expira em 5 minutos.

Se não foste tu, ignora este email.
"""

    html = f"""
    <html>
    <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,sans-serif;">
        <div style="max-width:520px;margin:40px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 5px 20px rgba(0,0,0,0.05);">
            
            <!-- HEADER -->
            <div style="background:{PRIMARY_COLOR};padding:20px;text-align:center;">
                <img src="{LOGO_URL}" alt="CountLight" style="height:40px;">
            </div>

            <!-- CONTENT -->
            <div style="padding:30px;text-align:center;">
                <h2 style="margin-bottom:10px;color:{PRIMARY_COLOR};">
                    Código de verificação
                </h2>

                <p style="color:#555;font-size:15px;line-height:1.5;">
                    Introduz este código para concluir o login:
                </p>

                <div style="margin-top:25px;font-size:32px;font-weight:bold;color:{SECONDARY_COLOR};letter-spacing:5px;">
                    {code}
                </div>

                <p style="margin-top:20px;font-size:13px;color:#888;">
                    Este código expira em 5 minutos.
                </p>
            </div>

            <!-- FOOTER -->
            <div style="padding:20px;text-align:center;font-size:12px;color:#999;border-top:1px solid #eee;">
                Se não foste tu a tentar iniciar sessão, ignora este email.
            </div>
        </div>
    </body>
    </html>
    """

    _send_email(to_email, subject, html, text)
