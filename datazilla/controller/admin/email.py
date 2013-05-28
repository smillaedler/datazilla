# Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.
from datetime import datetime

import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from model.utils import getDatabaseConnection, error, nvl
import settings


#if there are emails, then send them
def send_mails(project):


    ## GET DB CONNECTION
    db = getDatabaseConnection(project, "perftest")


    ##VERIFY self SHOULD BE THE ONE PERFORMING OPS (TO PREVENT MULTIPLE INSTANCES NEEDLESSLY RUNNING)

    db.begin()

    try:

        ## TEST IF ANY MAILS TO SEND
        hasMail = db.query("SELECT max(new_mail) FROM email.notify")
        if hasMail[0]["new_mail"]==0:
            return

        ## GET LIST OF MAILS TO SEND
        emails = db.query("""
            SELECT
                d.deliver_to to,
                c.subject,
                c.body
            FROM
                email_content c
            LEFT JOIN
                email_delivery d ON d.content=c.id
            WHERE
                c.date_sent IS NULL
            """)

        ## SEND MAILS
        for email in emails:
            sendemail(
                from_addr=settings.DATAZILLA_EMAIL_FROM,
                to_addrs=email.to,
                subject=email.subject,
                text_data=None,
                html_data=email.body,
                server=settings.DATAZILLA_EMAIL_HOST,
                port=nvl(settings.DATAZILLA_EMAIL_PORT, 465),
                username=settings.DATAZILLA_EMAIL_USER,
                password=settings.DATAZILLA_EMAIL_PASSWORD,
                use_ssl=True
            )

        db.execute("UPDATE email_content SET date_sent=%s",datetime.utcnow())
        db.execute("UPDATE email_notify SET new_mail=0")

        db.commit()
    except Exception, e:
        db.rollback()
        error("Could not send emails", e)


    ##RETURN CONNECTION TO POOL


## SNAGGED FROM http://hg.mozilla.org/automation/orangefactor/file/8bb01b4aa231/sendemail.py

if sys.hexversion < 0x020603f0:
    # versions earlier than 2.6.3 have a bug in smtplib when sending over SSL:
    #     http://bugs.python.org/issue4066
    
    # Unfortunately the stock version of Python in Snow Leopard is 2.6.1, so
    # we patch it here to avoid having to install an updated Python version.
    import socket
    import ssl

    def _get_socket_fixed(self, host, port, timeout):
        if self.debuglevel > 0: print>>stderr, 'connect:', (host, port)
        new_socket = socket.create_connection((host, port), timeout)
        new_socket = ssl.wrap_socket(new_socket, self.keyfile, self.certfile)
        self.file = smtplib.SSLFakeFile(new_socket)
        return new_socket

    smtplib.SMTP_SSL._get_socket = _get_socket_fixed


def sendemail(
    from_addr=None,
    to_addrs=None,
    subject='No Subject',
    text_data=None,
    html_data=None,
    server='mail.mozilla.com',
    port=465,
    username=None,
    password=None,
    use_ssl=True
):
    """Sends an email.

    from_addr is an email address; to_addrs is a list of email adresses.
    Addresses can be plain (e.g. "jsmith@example.com") or with real names
    (e.g. "John Smith <jsmith@example.com>").

    text_data and html_data are both strings.  You can specify one or both.
    If you specify both, the email will be sent as a MIME multipart
    alternative, i.e., the recipient will see the HTML content if his
    viewer supports it; otherwise he'll see the text content.
    """

    if not from_addr or not to_addrs:
        raise Exception("Both from_addr and to_addrs must be specified")
    if not text_data and not html_data:
        raise Exception("Must specify either text_data or html_data")

    if use_ssl:
        server = smtplib.SMTP_SSL(server, port)
    else:
        server = smtplib.SMTP(server, port)

    if username and password:
        server.login(username, password)

    if not html_data:
        msg = MIMEText(text_data)
    elif not text_data:
        msg = MIMEMultipart()
        msg.preamble = subject
        msg.attach(MIMEText(html_data, 'html'))
    else:
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(text_data, 'plain'))
        msg.attach(MIMEText(html_data, 'html'))

    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)

    server.sendmail(from_addr, to_addrs, msg.as_string())

    server.quit()
