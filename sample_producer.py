#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ConfigParser
import aliyun_mqs as mqs
import sys, time

def main():
    cf = ConfigParser.ConfigParser()
    cf.optionxform=str
    cf.read('aliyun_mqs.conf')
    Account = dict(cf.items("Account"))
    print '>>> Account', Account
    mq = mqs.AliMQS(Account['Host'], Account['OwnerID'], Account['AccessKeyId'], Account['AccessKeySecret'])
    print 'sleep 10'
    time.sleep(10)

    current_time = time.time()
    print 'send message hello and sleep 10(current time:%lf)' % (current_time)
    mq.SendMessage('testq', 'hello,%lf' %(current_time))
    print '(current time:%lf)' % (time.time())
    time.sleep(10)

    current_time = time.time()
    print 'send message hello1 and sleep 10(current time:%lf)' % (current_time)
    mq.SendMessage('testq', 'hello1,%lf' %(current_time))
    print '(current time:%lf)' % (time.time())
    time.sleep(10)

    current_time = time.time()
    print 'send message hello2 and sleep 10(current time:%lf)' % (current_time)
    mq.SendMessage('testq', 'hello2,%lf' %(current_time))
    print '(current time:%lf)' % (time.time())
    time.sleep(10)

    current_time = time.time()
    print 'send message end(current time:%lf)' % (current_time)
    mq.SendMessage('testq', 'end,%lf' %(current_time))
    print '(current time:%lf)' % (time.time())


if __name__ == '__main__':
    main()

