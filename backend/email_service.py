import smtplib
import random
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from backend.config import Config

logger = logging.getLogger(__name__)


def generate_otp():
    """Generate a 6-digit OTP as a string."""
    return str(random.randint(100000, 999999))


def send_verification_email(recipient_email, recipient_name, code):
    """Send a verification email with the OTP code via Gmail SMTP."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Verify your VerifyMesh account'
        msg['From'] = f"{Config.MAIL_SENDER_NAME} <{Config.MAIL_SENDER_EMAIL}>"
        msg['To'] = recipient_email

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background: #F8FAFC; padding: 40px 0;">
          <div style="max-width: 480px; margin: 0 auto; background: #fff; border-radius: 16px;
                      padding: 40px; border: 1px solid #e2e8f0;">
            <h2 style="color: #0F172A; margin-bottom: 8px;">Hi {recipient_name},</h2>
            <p style="color: #64748B; margin-bottom: 24px;">
              Thank you for signing up for <strong>VerifyMesh</strong>. 
              Use the code below to verify your email address.
            </p>
            <div style="text-align: center; background: #F1F5F9; border-radius: 12px;
                        padding: 28px; margin-bottom: 24px;">
              <p style="margin: 0; color: #64748B; font-size: 13px; letter-spacing: 1px;
                        text-transform: uppercase; margin-bottom: 12px;">Your verification code</p>
              <span style="font-size: 42px; font-weight: 800; letter-spacing: 14px;
                            color: #3B50BA;">{code}</span>
            </div>
            <p style="color: #94A3B8; font-size: 13px; text-align: center;">
              This code expires in <strong>10 minutes</strong>. Do not share it with anyone.
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
            <p style="color: #CBD5E1; font-size: 12px; text-align: center; margin: 0;">
              VerifyMesh &bull; If you didn't create an account, you can safely ignore this email.
            </p>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        # Connect to Gmail SMTP on Port 587 with STARTTLS
        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()  # CRITICAL: Re-establish EHLO capabilities post-TLS upgrade
            server.login(Config.MAIL_SENDER_EMAIL, Config.MAIL_SENDER_PASSWORD)
            server.sendmail(Config.MAIL_SENDER_EMAIL, recipient_email, msg.as_string())

        logger.info(f"Verification email sent successfully to {recipient_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        raise e