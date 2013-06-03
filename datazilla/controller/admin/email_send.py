# Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.
from datetime import datetime

import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from datazilla.model.debug import D
from datazilla.model.utils import nvl, datazilla


#if there are emails, then send them
def email_send(env):
    assert env.db is not None

    db = env.db
    db.debug=env.debug

    ##VERIFY self SHOULD BE THE ONE PERFORMING OPS (TO PREVENT MULTIPLE INSTANCES NEEDLESSLY RUNNING)
    db.begin()

    try:

        ## EXIT EARLY IF THERE ARE NO EMAILS TO SEND
        has_mail = db.query("SELECT max(new_mail) new_mail FROM email_notify")
        if has_mail[0]["new_mail"]==0:
            return

        ## GET LIST OF MAILS TO SEND
        emails = db.query("""
            SELECT
                c.id,
                group_concat(d.deliver_to SEPARATOR ',') `to`,
                c.subject,
                c.body
            FROM
                email_content c
            LEFT JOIN
                email_delivery d ON d.content=c.id
            WHERE
                c.date_sent IS NULL
            GROUP BY
                c.id

            """)

        ## SEND MAILS
        not_done=0   ##SET TO ONE IF THERE ARE MAIL FAILURES, AND THERE ARE MAILS STILL LEFT TO SEND
        for email in emails:
            try:
                sendemail(
                    from_addr=datazilla.settings.EMAIL_FROM,
                    to_addrs=email.to.split(','),
                    subject=email.subject,
                    text_data=None,
                    html_data=email.body,
                    server=datazilla.settings.EMAIL_HOST,
                    port=nvl(datazilla.settings.EMAIL_PORT, 465),
                    username=datazilla.settings.EMAIL_USER,
                    password=datazilla.settings.EMAIL_PASSWORD,
                    use_ssl=True
                )

                db.execute("UPDATE email_content SET date_sent=${now} WHERE id=${id}",{"id":email.id, "now":datetime.utcnow()})
            except Exception, e:
                D.warning("Problem sending email", e)
                not_done=1

        db.execute("UPDATE email_notify SET new_mail=${not_done}", {"not_done":not_done})

        db.commit()
        db.close()
    except Exception, e:
        db.rollback()
        db.close()
        D.error("Could not send emails", e)





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
