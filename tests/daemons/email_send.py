#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####
from datazilla.daemons.email_send import email_send
from datazilla.util.db import DB
from tests.util.emailer import Emailer
from util.testing import settings




class test_email_send():

    def __init__(self):
        self.db=DB(settings.database)
        self.emailer=None
        self.uid=None


    def test_zero_receivers(self):
        self.help_test_emailer([])

    def test_one_receivers(self):
        self.help_test_emailer([self.uid+"@mozilla.com"])

    def test_one_receivers(self):
        self.help_test_emailer([self.uid+"@mozilla.com"])

    def test_many_receivers(self):
        to_list=[self.uid+"_"+str(i)+"@mozilla.com" for i in range(0,10)]
        self.help_test_emailer(to_list)

        

    def help_test_emailer(self, to_list):
        self.setup(";".join(to_list))

        ########################################################################
        # TEST
        ########################################################################
        email_send(
            db=self.db,
            emailer=self.emailer,
            debug=True
        )

        ########################################################################
        # VERIFY
        ########################################################################
        self.verify_notify()
        mail_content=self.verify_content()
        self.verify_delivery(mail_content, to_list)
        self.verify_sent(to_list)



    def setup(self, to_list):
        self.uid=str(self.db.query("SELECT util_newID() uid FROM DUAL")[0].uid)
        
        self.db.call("email_send",(
            to_list, #to
            "subject"+self.uid, #title
            "body"+self.uid, #body
            None
        ))
        
        self.emailer=Emailer(None)



    def verify_notify(self):
        #THE NOTIFY FLAG IS PROPERLY CLEARED
        notify = self.db.query("SELECT new_mail FROM email_notify")[0].new_mail
        assert notify == 0


    def verify_content(self):
        #MAIL DOES EXIST
        mail_content=self.db.query("SELECT id, subject, date_sent, body FROM email_content WHERE subject=${subject}", {"subject":"subject"+self.uid})
        assert len(mail_content)==1
        assert mail_content[0].date_sent is not None
        assert mail_content[0].body=="body"+self.uid


    def verify_delivery(self, mail_content, to_list):
        #VERIFY DELIVERY IN DATABASE IS SAME AS LIST
        mail_delivery=self.db.query("SELECT id, deliver_to FROM email_delivery WHERE content=${content_id} ORDER BY deliver_to", {"content_id":mail_content.id})
        assert len(mail_delivery)==len(to_list)

        for i, d in enumerate(to_list):
            assert mail_delivery[i].deliver_to==d


    def verify_sent(self, to_list):
        assert len(self.emailer.sent)==1
        assert self.emailer.sent[0].from_address is None
        assert self.emailer.sent[0].subject=="subject"+self.uid
        assert self.emailer.sent[0].text_data is None
        assert self.emailer.sent[0].html_data=="body"+self.uid

        #THE EMAIL SHOULD HAVE BEEN SENT TO EVERYONE IN to_list. NO MORE, NO LESS
        to_list=set(to_list)
        to_addr=set(self.emailer.sent[0].to_addr)
        assert len(to_list ^ to_addr)==0

