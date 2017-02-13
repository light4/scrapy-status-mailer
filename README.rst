Status mailer extension for `Scrapy <http://scrapy.org/>`__
===========================================================

Send an email when a crawler finishes or breaks.

Install
-------

The quick way:

::

    pip install scrapy_status_mailer

Or install from GitHub:

::

    pip install git+git://github.com/light4/scrapy-status-mailer.git@master

Or checkout the source and run:

::

    python setup.py install

settings.py
-----------

settings for send email

1. `163 <http://help.mail.163.com/faq.do?m=list&categoryID=76>`__
2. `qq <http://service.mail.qq.com/cgi-bin/help?id=14>`__
3. `gmail <https://support.google.com/mail/answer/7126229?visit_id=1-636225695838794234-432865084&hl=zh-Hans&rd=1>`__

::

    STATUSMAILER_RECIPIENTS = []
    STATUSMAILER_COMPRESSION = 'gzip'
    # STATUSMAILER_COMPRESSION = None

    MAIL_FROM = ''
    MAIL_HOST = 'smtp.qq.com'
    MAIL_PORT = 465
    MAIL_USER = ''
    MAIL_PASS = ''
    MAIL_TLS = True
    MAIL_SSL = True

    EXTENSIONS = {
        'scrapy_status_mailer.StatusMailer': 80,
    }

Thanks
------

`stackoverflow <http://stackoverflow.com/questions/16260753/emailing-items-and-logs-with-scrapy>`__
