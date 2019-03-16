import smtplib
import gzip
import io
import os
from configparser import ConfigParser
import thompco_utils

if os.name == 'nt' or os.name == "posix":
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
else:
    # noinspection PyUnresolvedReferences
    from email.MIMEMultipart import MIMEMultipart
    # noinspection PyUnresolvedReferences
    from email.MIMEText import MIMEText
    # noinspection PyUnresolvedReferences
    from email.MIMEApplication import MIMEApplication


class EmailConnection:
    TITLE = "email connection"
    USERNAME = "username"
    PASSWORD = "password"
    FROM = "from"

    def __init__(self, cfg_mgr=None, username=None, password=None, from_user=None, filename=None, create=None):
        if cfg_mgr is None:
            self.username = username
            self.password = password
            self.from_user = from_user
        else:
            self.username = cfg_mgr.read_entry(EmailConnection.TITLE, EmailConnection.USERNAME,
                                               "myname@google.com", str)
            self.password = cfg_mgr.read_entry(EmailConnection.TITLE, EmailConnection.PASSWORD,
                                               "mySecretPassword", str)
            self.from_user = cfg_mgr.read_entry(EmailConnection.TITLE, EmailConnection.FROM,
                                                "Mint Checker", str)


class EmailSender:
    def __init__(self, email_connection):
        self.email_connection = email_connection

    def send(self, to_email, subject, message, attach_file=None):
        logger = thompco_utils.get_logger()
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
    # mail = EmailSender(EmailConnection(config, logging.getLogger('emailSender_test')))
    # mail.send(['jorythompson@gmail.com', 'jordan@thompco.com'], 'this is a test from emailSender',
    #          'Here is the message using the configuration file')
