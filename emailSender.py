import smtplib
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import ConfigParser
import logging
import inspect
from email.mime.application import MIMEApplication
from os.path import basename


class EmailConnection:
    TITLE = "email connection"
    USERNAME = "username"
    PASSWORD = "password"
    FROM = "from"

    def __init__(self, config=None, username=None, password=None, from_user=None):
        if config is None:
            self.username = username
            self.password = password
            self.from_user = from_user
        else:
            self.username = config.get(EmailConnection.TITLE, EmailConnection.USERNAME)
            self.password = config.get(EmailConnection.TITLE, EmailConnection.PASSWORD)
            self.from_user = config.get(EmailConnection.TITLE, EmailConnection.FROM)


class EmailSender:
    def __init__(self, email_connection):
        self.email_connection = email_connection

    def send(self, to_email, subject, message, cc=None, attach_file=None):
        logger = logging.getLogger(self.__class__.__name__ + "." + inspect.stack()[0][3])
        msg = MIMEMultipart('alternative')
        msg['From'] = self.email_connection.from_user
        recipients = [to_email]
        msg['To'] = to_email
        if cc is not None:
            msg['Cc'] = cc
            recipients.append(cc)
        else:
            msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, "html"))
        if attach_file is not None:
            with open (attach_file, "rb") as fp:
                part = MIMEApplication(fp.read(), Name=basename(attach_file))
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(attach_file)
            msg.attach(part)

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(self.email_connection.username, self.email_connection.password)
            server.sendmail(self.email_connection.username, recipients, msg.as_string())
            server.quit()
            logger.debug("Successfully sent mail to " + to_email)
        except smtplib.SMTPAuthenticationError as e:
            logger.warn("Failed to send mail to " + to_email)


if __name__ == "__main__":
    mail = EmailSender(EmailConnection(username="jorythompson@gmail.com", password="ftxsirhfclvmxkgp"))
    mail.send("jorythompson@gmail.com", "this is a test from emailSender", "Here is the message using parameters passed in")
    config = ConfigParser.ConfigParser()
    config.read("laptop-home.ini")
    mail = EmailSender(EmailConnection(config, logging.getLogger("emailSender_test")))
    mail.send("jorythompson@gmail.com", "this is a test from emailSender", "Here is the message using the configuration file")