# Source Code is subject to the terms of the Mozilla Public License
# version 2.0 (the "License"). You can obtain a copy of the License at
# http://mozilla.org/MPL/2.0/.
from datetime import datetime

import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datazilla.model.utils import nvl
from datazilla.util.debug import D


#if there are emails, then send them
from datazilla.util.map import Map

def email_send(env):
    assert env.db is not None               #EXPECTING db WITH EMAIL SCHEMA
    assert env.settings.email is not None   #EXPECTING SMTP CONNECTION INFO

    db = env.db
    db.debug=env.debug


    ##VERIFY self SHOULD BE THE ONE PERFORMING OPS (TO PREVENT MULTIPLE INSTANCES NEEDLESSLY RUNNING)
    db.begin()

    try:

        ## EXIT EARLY IF THERE ARE NO EMAILS TO SEND
        has_mail = db.query("SELECT max(new_mail) new_mail FROM email_notify")
        if has_mail[0]["new_mail"]==0:
            D.println("No emails to send")
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
        num_done=0
        for email in emails:
            try:
                sendemail(
                    to_addrs=email.to.split(','),
                    subject=email.subject,
                    html_data=email.body,
                    settings=env.settings.email
                )

                db.execute("UPDATE email_content SET date_sent=${now} WHERE id=${id}",{"id":email.id, "now":datetime.utcnow()})
                num_done+=len(email.to.split(','))
            except Exception, e:
                D.warning("Problem sending email", e)
                not_done=1

        db.execute("UPDATE email_notify SET new_mail=${not_done}", {"not_done":not_done})

        D.println(str(num_done)+" emails have been sent")
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
    from_address=None,
    to_addrs=None,
    subject='No Subject',
    text_data=None,
    html_data=None,
#    server='mail.mozilla.com',
#    port=465,
#    username=None,
#    password=None,
    settings=Map()
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

    from_address=nvl(from_address, settings.from_address)

    if not from_address or not to_addrs:
        raise Exception("Both from_addr and to_addrs must be specified")
    if not text_data and not html_data:
        raise Exception("Must specify either text_data or html_data")

    if settings.use_ssl:
        server = smtplib.SMTP_SSL(settings.host, settings.port)
    else:
        server = smtplib.SMTP(settings.host, settings.port)

    if settings.username and settings.password:
        server.login(settings.username, settings.password)

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
    msg['From'] = from_address
    msg['To'] = ', '.join(to_addrs)

    server.sendmail(from_address, to_addrs, msg.as_string())

    server.quit()
