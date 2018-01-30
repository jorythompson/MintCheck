import smtplib
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
import gzip
import io
import os
import ConfigParser
import logging
import inspect
from email.mime.application import MIMEApplication


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
        server = None
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(self.email_connection.username, self.email_connection.password)
            msg = MIMEMultipart('alternative')
            sender = self.email_connection.from_user
            recipients = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, "html"))
            msg['From'] = self.email_connection.from_user
            if isinstance(recipients, list):
                msg['To'] = ", ".join(recipients)
            else:
                msg['To'] = recipients
            if attach_file is not None:
                with open(attach_file, 'rb') as f, io.BytesIO() as b:
                    g = gzip.GzipFile(mode='wb', fileobj=b)
                    g.writelines(f)
                    g.close()
                    attachment = MIMEApplication(b.getvalue(), 'x-gzip')
                    file_name = os.path.split(attach_file)[1]
                    attachment['Content-Disposition'] = 'attachment; filename={}.gz'.format(file_name)
                msg.attach(attachment)
            server.sendmail(sender, recipients, msg.as_string())
            logger.debug("Successfully sent mail to " + str(recipients))
        except Exception as e:
            logger.warn("Failed to send mail to {} because {}".format(to_email, str(e)))
        finally:
            if server is not None:
                server.quit()


if __name__ == '__main__':
    mail = EmailSender(EmailConnection(username='jorythompson@gmail.com', password='ftxsirhfclvmxkgp'))
    mail.send(to_email=['jorythompson@gmail.com', 'jordan@thompco.com'],
              subject='this is a test from emailSender',
              message='Here is the message using parameters passed in')
    config = ConfigParser.ConfigParser()
    config.read('laptop-home.ini')
    #mail = EmailSender(EmailConnection(config, logging.getLogger('emailSender_test')))
    #mail.send(['jorythompson@gmail.com', 'jordan@thompco.com'], 'this is a test from emailSender',
    #          'Here is the message using the configuration file')