# -*- coding: utf-8 -*-

import gzip
import datetime
import pprint

from collections import defaultdict

from scrapy import signals
from scrapy.mail import MailSender
from scrapy.exceptions import NotConfigured
from scrapy.utils.serialize import ScrapyJSONEncoder

try:
    from cStringIO import cStringIO as StringIO
except ImportError:
    from StringIO import StringIO


def format_size(size):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return "{:3.1f} {}".format(size, x)

        size /= 1024.0


class GzipCompressor(gzip.GzipFile):
    extension = '.gz'
    mimetype = 'application/gzip'

    def __init__(self):
        super(GzipCompressor, self).__init__(fileobj=PlainCompressor(), mode='w')
        self.read = self.fileobj.read


class PlainCompressor(StringIO):
    extension = ''
    mimetype = 'text/plain'

    def read(self, *args, **kwargs):
        self.seek(0)

        return StringIO.read(self, *args, **kwargs)

    @property
    def size(self):
        return len(self.getvalue())


class StatusMailer(object):
    def __init__(self, recipients, mail, compressor, crawler):
        self.recipients = recipients
        self.mail = mail
        self.encoder = ScrapyJSONEncoder()
        self.files = defaultdict(compressor)

        self.num_items = 0
        self.num_errors = 0
        self.num_dropped = 0
        self.stats = crawler.stats

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        recipients = crawler.settings.getlist('STATUSMAILER_RECIPIENTS')
        compression = crawler.settings.get('STATUSMAILER_COMPRESSION')

        if not compression:
            compressor = PlainCompressor
        elif compression.lower().startswith('gz'):
            compressor = GzipCompressor
        else:
            raise NotConfigured

        if not recipients:
            raise NotConfigured

        mail = MailSender.from_settings(crawler.settings)
        instance = cls(recipients, mail, compressor, crawler)

        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(instance.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(instance.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(instance.spider_error, signal=signals.spider_error)
        crawler.signals.connect(instance.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(instance.request_received, signal=signals.request_received)

        return instance

    def spider_opened(self, spider):
        self.start_time = datetime.datetime.now()

    def item_scraped(self, item, response, spider):
        self.files[spider.name + '-items.json'].write(self.encoder.encode(item))
        self.files[spider.name + '-items.json'].write('\n')
        self.num_items += 1

    def item_dropped(self, item, response, exception, spider):
        self.files[spider.name + '-dropped-items.json'].write(self.encoder.encode(item))
        self.files[spider.name + '-dropped-items.json'].write('\n')
        self.num_dropped += 1

    def spider_error(self, failure, response, spider):
        # compressor = PlainCompressor()
        # self.files[spider.name + '-errors.log'] = compressor
        self.files[spider.name + '-errors.log'].write(response.url + '\n')
        self.files[spider.name + '-errors.log'].write(failure.getTraceback())
        self.num_errors += 1

    def request_received(self, request, spider):
        self.files[spider.name + '.log'].write(str(request) + '\n')

    def spider_closed(self, spider, reason):
        files = []
        self.finish_time = datetime.datetime.now()
        self.used_time = self.finish_time - self.start_time

        dumppy_stats = pprint.pformat(self.stats.get_stats())
        self.files[spider.name + '-statistics.log'].write(dumppy_stats)
        self.files[spider.name + '-statistics.log'].write('\n')

        for name, compressed in self.files.items():
            # close compressed file
            compressed.fileobj.write(compressed.compress.flush())
            gzip.write32u(compressed.fileobj, compressed.crc)
            gzip.write32u(compressed.fileobj, compressed.size & 0xffffffff)
            files.append((name + compressed.extension, compressed.mimetype, compressed))

        try:
            size = self.files[spider.name + '-items.json'].size
        except KeyError:
            size = 0

        body = '''Crawl statistics:

 - Spider name: {0}
 - Spider started at: {1}
 - Spider finished at: {2}
 - Spider used time: {3}
 - Number of items scraped: {4}
 - Number of items dropped: {5}
 - Number of errors: {6}
 - Size of scraped items: {7}

Scrapy Dumppy stats:
{8}
'''.format(spider.name,
           self.start_time,
           self.finish_time,
           self.used_time,
           self.num_items,
           self.num_dropped,
           self.num_errors,
           format_size(size),
           dumppy_stats
           )

        return self.mail.send(
            to=self.recipients,
            subject='Crawler for {}: {}'.format(spider.name, reason),
            body=body,
            attachs=files
        )
