"""
Email service — Gmail SMTP for registration OTP only.
Other notification methods remain no-ops (historically handled by EmailJS / unused).
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger('email_service')


class EmailService:
    def __init__(self):
        self.enabled = os.getenv('SMTP_ENABLED', 'false').lower() in ('1', 'true', 'yes')
        self.host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.port = int(os.getenv('SMTP_PORT', '587'))
        self.username = os.getenv('SMTP_USERNAME', '')
        self.password = os.getenv('SMTP_PASSWORD', '')
        self.from_addr = os.getenv('SMTP_FROM', self.username)
        self.use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
        self.timeout = int(os.getenv('SMTP_TIMEOUT_SECONDS', '10'))

    def _smtp_ready(self) -> bool:
        if not self.enabled:
            return False
        if not self.username or not self.password or not self.from_addr:
            logger.warning('SMTP enabled but SMTP_USERNAME / SMTP_PASSWORD / SMTP_FROM incomplete')
            return False
        return True

    def send_registration_otp(self, email: str, full_name: str, otp: str) -> bool:
        """
        Send a six-digit registration OTP via Gmail SMTP.
        Returns True on success, False on any failure.
        Never logs the OTP or SMTP password.
        """
        if not self._smtp_ready():
            logger.error('SMTP not configured or disabled; cannot send registration OTP')
            return False

        subject = 'Your FaceAttend verification code'
        body = (
            f'Hello {full_name},\n\n'
            f'Your FaceAttend registration verification code is:\n\n'
            f'    {otp}\n\n'
            f'This code expires in {os.getenv("OTP_EXPIRES_MINUTES", "10")} minutes.\n'
            f'If you did not request this, you can ignore this email.\n\n'
            f'— FaceAttend\n'
        )

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.from_addr
        msg['To'] = email
        msg.set_content(body)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            logger.info('Registration OTP email accepted by SMTP for %s', email)
            return True
        except smtplib.SMTPException as e:
            logger.error('SMTP error sending registration OTP to %s: %s', email, type(e).__name__)
            return False
        except OSError as e:
            logger.error('Network/OS error sending registration OTP to %s: %s', email, type(e).__name__)
            return False
        except Exception as e:
            logger.error('Unexpected error sending registration OTP to %s: %s', email, type(e).__name__)
            return False


    def send_password_reset_otp(self, email: str, full_name: str, otp: str) -> bool:
        """Send a 4-digit password-reset OTP via Gmail SMTP. Never logs the OTP."""
        if not self._smtp_ready():
            logger.error('SMTP not configured or disabled; cannot send password-reset OTP')
            return False

        mins = os.getenv('OTP_EXPIRES_MINUTES', '10')
        lines = [
            f'Hello {full_name},',
            '',
            'Your FaceAttend password recovery code is:',
            '',
            f'    {otp}',
            '',
            f'This code expires in {mins} minutes.',
            'If you did not request a password reset, you can ignore this email. Your password will stay the same.',
            '',
            '— FaceAttend',
            '',
        ]
        msg = EmailMessage()
        msg['Subject'] = 'Your FaceAttend password recovery code'
        msg['From'] = self.from_addr
        msg['To'] = email
        msg.set_content('\n'.join(lines).replace('\\n', '\n'))
        # real newlines:
        msg.set_content(chr(10).join(lines))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            logger.info('Password-reset OTP email accepted by SMTP for %s', email)
            return True
        except smtplib.SMTPException as e:
            logger.error('SMTP error sending password-reset OTP to %s: %s', email, type(e).__name__)
            return False
        except OSError as e:
            logger.error('Network/OS error sending password-reset OTP to %s: %s', email, type(e).__name__)
            return False
        except Exception as e:
            logger.error('Unexpected error sending password-reset OTP to %s: %s', email, type(e).__name__)
            return False


    # ── Legacy / unused notification stubs (do not enable accidentally) ──

    def send_email(self, *args, **kwargs):
        return True

    def send_attendance_marked_email(self, *args, **kwargs):
        return True

    def send_absent_notification(self, *args, **kwargs):
        return True

    def send_daily_summary(self, *args, **kwargs):
        return True


# global instance
email_service = EmailService()
