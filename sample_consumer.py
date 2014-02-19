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
    count = 0
    total_diff = 0
    while True:
        message = mq.ReceiveMessage('testq')
        current_time = time.time()
        if isinstance(message, mqs.Error):
            print '.',
            sys.stdout.flush()
            #time.sleep(1)
        else:
            print ''
            print 'received message', message.MessageBody, '(current time:%lf)' % (current_time)
            print 'delete message with handle %s' % (message.ReceiptHandle)
            cmd, t = message.MessageBody.split(',')
            time_diff = current_time - float(t)
            count += 1
            total_diff += time_diff
            print '>>> send/recv time_diff', time_diff
            end = False
            if cmd == 'end':
                end = True
            message = mq.DeleteMessage('testq', message.ReceiptHandle)
            #print 'delete message or error', message
            if end:
                print '>>> get end message so exit'
                break
    print 'total_diff %lf count %d average diff %f' % (total_diff, count, float(total_diff)/count)

if __name__ == '__main__':
    main()

