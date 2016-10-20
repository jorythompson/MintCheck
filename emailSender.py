import smtplib
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText


class EmailSender:

    def __init__(self, username, password, from_email):
        self.username = username
        self.password = password
        self.from_email = from_email

    def send(self, to_email, subject, message):
        msg = MIMEMultipart()
        msg['From'] = self.from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, to_email, msg.as_string())
            server.quit()
            print "Successfully sent mail to " + to_email
        except smtplib.SMTPAuthenticationError as e:
            print "Failed to send mail to " + to_email


if __name__ == "__main__":
    mail = EmailSender("jorythompson@gmail.com", "ftxsirhfclvmxkgp")
    mail.send("Jordan@ThompCo.com", "jorythompson@gmail.com", "this is a test from emailSender", "Here is the message")