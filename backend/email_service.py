import smtplib
import secrets
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from backend.config import Config

logger = logging.getLogger(__name__)


def generate_otp():
    """Generate a cryptographically secure 6-digit OTP as a string using OS CSPRNG."""
    return str(secrets.randbelow(900000) + 100000)


def send_verification_email(recipient_email, recipient_name, code):
    """Send a verification email with the OTP code via configured SMTP server."""
    if not Config.MAIL_SENDER_EMAIL or not Config.MAIL_SENDER_PASSWORD:
        logger.error("SMTP sender credentials are not configured in environment.")
        raise RuntimeError("Email service is not configured. Please contact the administrator.")

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

        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=10) as server:
            server.ehlo()
            if Config.MAIL_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(Config.MAIL_SENDER_EMAIL, Config.MAIL_SENDER_PASSWORD)
            server.sendmail(Config.MAIL_SENDER_EMAIL, recipient_email, msg.as_string())

        logger.info(f"Verification email sent successfully to {recipient_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email to {recipient_email}: {type(e).__name__}")
        raise e


def send_supervisor_verification_email(
    supervisor_email,
    supervisor_name,
    agent_name,
    company,
    job_title,
    start_date,
    end_date_str,
    verification_link
):
    """
    Dispatch an automated employment verification request to a candidate's supervisor/manager.
    If SMTP credentials are not configured or email sending fails, logs the link gracefully.
    """
    if not Config.MAIL_SENDER_EMAIL or not Config.MAIL_SENDER_PASSWORD:
        logger.warning(
            f"[Supervisor Verification Mock] SMTP credentials not set. Simulated link dispatched to {supervisor_email}:\n"
            f"  Link: {verification_link}"
        )
        return True

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Action Required: Employment Verification for {agent_name} - VerifyMesh"
        msg['From'] = f"{Config.MAIL_SENDER_NAME} <{Config.MAIL_SENDER_EMAIL}>"
        msg['To'] = supervisor_email

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #F8FAFC; padding: 40px 16px; margin: 0;">
          <div style="max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 36px; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(15,23,42,0.05);">
            <div style="display: flex; align-items: center; margin-bottom: 24px;">
              <span style="font-size: 20px; font-weight: 800; color: #1E293B; letter-spacing: -0.5px;">Verify<span style="color: #3B50BA;">Mesh</span></span>
            </div>
            
            <h2 style="color: #0F172A; font-size: 20px; font-weight: 700; margin-top: 0; margin-bottom: 8px;">
              Employment Verification Request
            </h2>
            <p style="color: #64748B; font-size: 14px; line-height: 1.6; margin-bottom: 24px;">
              Hello {supervisor_name or 'Hiring Manager / Supervisor'},<br/>
              <strong>{agent_name}</strong> has submitted work experience on the <strong>VerifyMesh Workforce Platform</strong> and listed you as their former supervisor/manager for employment verification.
            </p>

            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-bottom: 28px;">
              <p style="margin: 0 0 10px; font-size: 13px; color: #64748B; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Submitted Record Details</p>
              <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <tr>
                  <td style="color: #64748B; padding: 6px 0; width: 35%;">Organization:</td>
                  <td style="color: #0F172A; font-weight: 600; padding: 6px 0;">{company}</td>
                </tr>
                <tr>
                  <td style="color: #64748B; padding: 6px 0;">Role / Title:</td>
                  <td style="color: #0F172A; font-weight: 600; padding: 6px 0;">{job_title}</td>
                </tr>
                <tr>
                  <td style="color: #64748B; padding: 6px 0;">Employment Period:</td>
                  <td style="color: #0F172A; font-weight: 600; padding: 6px 0;">{start_date} &ndash; {end_date_str}</td>
                </tr>
              </table>
            </div>

            <p style="color: #475569; font-size: 14px; line-height: 1.5; margin-bottom: 24px;">
              Please take 30 seconds to confirm whether the job title and employment tenure provided above are accurate:
            </p>

            <div style="text-align: center; margin-bottom: 28px;">
              <a href="{verification_link}" style="display: inline-block; background: #3B50BA; color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-weight: 600; font-size: 14px; box-shadow: 0 4px 8px rgba(59,80,186,0.25);">
                Review & Confirm Experience &rarr;
              </a>
            </div>

            <p style="color: #94A3B8; font-size: 12px; text-align: center; margin: 0 0 8px;">
              This secure link expires in 7 days. No sign-up or password required.
            </p>
            <p style="color: #94A3B8; font-size: 12px; text-align: center; margin: 0; word-break: break-all;">
              Or copy this URL into your browser: <br/>
              <span style="color: #3B50BA;">{verification_link}</span>
            </p>
            
            <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;" />
            <p style="color: #CBD5E1; font-size: 11px; text-align: center; margin: 0;">
              VerifyMesh Workforce Authentication Engine &bull; Automated Verification Service
            </p>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=10) as server:
            server.ehlo()
            if Config.MAIL_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(Config.MAIL_SENDER_EMAIL, Config.MAIL_SENDER_PASSWORD)
            server.sendmail(Config.MAIL_SENDER_EMAIL, supervisor_email, msg.as_string())

        logger.info(f"Supervisor verification email sent successfully to {supervisor_email}")
        return True

    except Exception as e:
        logger.warning(
            f"Could not deliver email to {supervisor_email} via SMTP ({type(e).__name__}: {e}). "
            f"Generated verification link: {verification_link}"
        )
        return False