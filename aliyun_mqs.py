#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import httplib
from xml.dom import minidom
import base64, hmac, hashlib
from time import gmtime, strftime
import ConfigParser
import logging

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format = FORMAT)
logger = logging.getLogger('aliyun_mqs')
logger.setLevel(logging.WARN)

MQS_VERSION = 1
MQS_QUEUE_ATTRS = ('ActiveMessages','CacheSize','CreateTime','DelayMessages','DelaySeconds','InactiveMessages','LastModifyTime','MaximumMessageSize','MessageRetentionPeriod','QueueName','QueueStatus','SplitEnabled','VisibilityTimeout')
MQS_ERROR_ATTRS = ('Code', 'Message', 'RequestId', 'HostId')
MQS_QUEUEMESSAGE_ATTRS = ('MessageId', 'ReceiptHandle', 'MessageBody', 'MessageBodyMD5', 'EnqueueTime', 'NextVisibleTime', 'FirstDequeueTime', 'DequeueCount')

class Error:
    def __init__(self, Code='DefaultErrorCode', Message='DefaultErrorMessage', RequestId='NoRequestId', HostId='NoHostId'):
        for a in MQS_ERROR_ATTRS:
            setattr(self, a, None)
        self.Code = Code
        self.Message = Message
        self.RequestId = RequestId
        self.HostId = HostId
    def __repr__(self):
        repr = u'Error'
        for a in MQS_ERROR_ATTRS:
            if getattr(self, a):
                repr += '\n\t%s:\t\t%s' % (a, getattr(self, a))
        return repr

class Queue:
    def __init__(self, QueueName=None, QueueURL=None):
        for a in MQS_QUEUE_ATTRS:
            setattr(self, a, None)
        self.QueueName = QueueName
        self.QueueURL = QueueURL
    def __repr__(self):
        repr = u'Queue<QueueName:%s>' % (self.QueueName)
        for a in MQS_QUEUE_ATTRS:
            if a != 'QueueName' and getattr(self, a):
                repr += '\n\t%s:\t\t%s' % (a, getattr(self, a))
        return repr

class QueueMessage:
    def __init__(self, MessageBody=None):
        for a in MQS_QUEUEMESSAGE_ATTRS:
            setattr(self, a, None)
        self.MessageBody = MessageBody
    def __repr__(self):
        repr = u'QueueMessage<MessageBody[:50]:%s>' % (self.MessageBody and self.MessageBody[:50] or None)
        for a in MQS_QUEUEMESSAGE_ATTRS:
            if getattr(self, a):
                repr += '\n\t%s:\t\t%s' % (a, str(getattr(self, a))[:50])
        return repr

class AliMQS(object):
    def __init__(self, host, QueueOwnerId, AccessKeyId, AccessKeySecret):
        self.host = host
        if self.host.find('http://') == 0:
            self.host = self.host[7:]
        self.port = 80
        self.QueueOwnerId = QueueOwnerId
        self.AccessKeyId = AccessKeyId
        self.AccessKeySecret = AccessKeySecret

    def _getGMTDate(self):
        return strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime())

    def _genSignature(self, VERB, CONTENT_MD5, CONTENT_TYPE, GMT_DATE, CanonicalizedMQSHeaders={}, CanonicalizedResource='/'):
        x_mqs_headers_string = ''
        ordered_keys = CanonicalizedMQSHeaders.keys()
        ordered_keys.sort()
        for k in ordered_keys:
            x_mqs_headers_string += ':'.join([k, str(CanonicalizedMQSHeaders[k])]) + '\n'
        
        string2sign = VERB + "\n" + CONTENT_MD5 + "\n" + CONTENT_TYPE + "\n" + GMT_DATE + "\n" + x_mqs_headers_string + CanonicalizedResource
        sig = base64.b64encode(hmac.new(self.AccessKeySecret, string2sign, hashlib.sha1).digest()).strip()
        return ('Authorization', "MQS " + self.AccessKeyId + ":"+ sig)

    def _handlerErrorResponse(self, r, data):
        if r.status in (httplib.FORBIDDEN, httplib.NOT_FOUND, httplib.CONFLICT, httplib.BAD_REQUEST):
            logger.debug('Error %s, data %s' % (r.status, data))
            error = Error()
            try:
                doc = minidom.parseString(data)
                for node in doc.childNodes[0].childNodes:
                    if node.nodeName in MQS_ERROR_ATTRS:
                        setattr(error, node.nodeName, node.childNodes[0].nodeValue)
                return error
            except Exception, e:
                logger.debug('error parsing xml: %s', str(e))
                print 'err'
                return error
        return None

    def _kv2element(self, key, value, doc):
        ele = doc.createElement(key)
        if isinstance(value, str) or isinstance(value, unicode):
            data = doc.createCDATASection(value)
            ele.appendChild(data)
        else:
            text = doc.createTextNode(str(value))
            ele.appendChild(text)
        return ele

    # FIXME: support NextMarker
    def ListQueue(self, prefix=None, nextmarker=None, retnumber=1000):
        GMT_DATE = self._getGMTDate()
        content = ''
        CONTENT_MD5 = hashlib.md5(content).hexdigest()
        CONTENT_TYPE = 'text/xml'
        CanonicalizedMQSHeaders = {'x-mqs-version': MQS_VERSION, 
            'x-mqs-ret-number': retnumber}
        if nextmarker: 
            CanonicalizedMQSHeaders['x-mqs-marker'] = nextmarker
        if prefix: 
            CanonicalizedMQSHeaders['x-mqs-prefix'] = prefix

        RequestResource = '/'
        sig = self._genSignature('GET', CONTENT_MD5, CONTENT_TYPE, GMT_DATE, CanonicalizedMQSHeaders, RequestResource)        

        conn = httplib.HTTPConnection(self.host, self.port)
        headers = {'Host': self.host,
            'Date': GMT_DATE,
            'Content-Type': CONTENT_TYPE,
            'Content-MD5': CONTENT_MD5,
            sig[0]: sig[1],}
        
        for k in CanonicalizedMQSHeaders.keys():
            headers[k] = CanonicalizedMQSHeaders[k]

        #print '>>> headers', headers

        conn.request('GET', RequestResource, headers=headers)
        r = conn.getresponse()
        #print '>>> response', r, r.status, r.getheaders()
        data = r.read()
        conn.close()
        error = self._handlerErrorResponse(r, data)
        if error:
            return error

        queues = []
        if r.status == httplib.OK:
            logger.debug('ListQueue response\n' + data)
            try:
                doc = minidom.parseString(data)
                if doc.childNodes[0].tagName != u'Queues':
                    return []
                
                for node in doc.childNodes[0].childNodes:
                    if node.nodeName == 'Queue':
                        queue = Queue()
                        for subnode in node.childNodes:
                            if subnode.nodeName == 'QueueURL':
                                for n in subnode.childNodes:
                                    if n.nodeType == n.TEXT_NODE:
                                        queue.QueueURL = n.nodeValue

                        # FIXME: undocumented
                        if not queue.QueueName and queue.QueueURL:
                            pos = queue.QueueURL.rfind('/')
                            if pos > -1:
                                queue.QueueName = queue.QueueURL[pos+1:]
                        queues.append(queue)

                return queues
                    
            except Exception, e:
                logger.info('parsing xml exception %s' % (str(e)))
                return []

        logger.debug('Error status %d body\n%s', r.status, data)
        return []

    def GetQueueAttributes(self, QueueName):
        GMT_DATE = self._getGMTDate()
        content = ''
        CONTENT_MD5 = hashlib.md5(content).hexdigest()
        CONTENT_TYPE = 'text/xml'
        CanonicalizedMQSHeaders = {'x-mqs-version': MQS_VERSION}

        RequestResource = '/%s' % (QueueName)
        sig = self._genSignature('GET', CONTENT_MD5, CONTENT_TYPE, GMT_DATE, CanonicalizedMQSHeaders, RequestResource)        

        conn = httplib.HTTPConnection(self.host, self.port)
        headers = {'Host': self.host,
            'Date': GMT_DATE,
            'Content-Type': CONTENT_TYPE,
            'Content-MD5': CONTENT_MD5,
            sig[0]: sig[1],}
        
        for k in CanonicalizedMQSHeaders.keys():
            headers[k] = CanonicalizedMQSHeaders[k]

        conn.request('GET', RequestResource, headers=headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()
        error = self._handlerErrorResponse(r, data)
        if error:
            return error

        queue = Queue()
        if r.status == httplib.OK:
            logger.debug('GetQueueAttributes response\n' + data)
            try:
                doc = minidom.parseString(data)
                if doc.childNodes[0].tagName != u'Queue':
                    return []
                
                for node in doc.childNodes[0].childNodes:
                    if node.nodeName in MQS_QUEUE_ATTRS:
                        for subnode in node.childNodes:
                            if subnode.nodeType == subnode.TEXT_NODE:
                                setattr(queue, node.nodeName, subnode.nodeValue)

                return queue
                    
            except Exception, e:
                logger.info('parsing xml exception %s' % (str(e)))
                return None

        logger.debug('Error status %d body\n%s', r.status, data)
        return None

    def SetQueueAttributes(self, QueueName, DelaySeconds=0, MaximumMessageSize=65536, MessageRetentionPeriod=4*24*3600, VisibilityTimeout=30):
        return self.CreateQueue(QueueName, DelaySeconds, MaximumMessageSize, MessageRetentionPeriod, VisibilityTimeout, ismodify=True)

    # FIXME: keep default value None ?
    def CreateQueue(self, QueueName, DelaySeconds=0, MaximumMessageSize=65536, MessageRetentionPeriod=4*24*3600, VisibilityTimeout=30, ismodify=False):
        logger.debug('CreateQueue %s, DelaySeconds:%d, MaximumMessageSize: %d, MessageRetentionPeriod: %d, VisibilityTimeout: %d, ismodify: %d' % (QueueName, DelaySeconds, MaximumMessageSize, MessageRetentionPeriod, VisibilityTimeout, ismodify))
        try:
            doc = minidom.Document()
            queuenode = doc.createElement('Queue')
            queuenode.setAttribute('xmlns', 'http://mqs.aliyuncs.com/doc/v1/')
            doc.appendChild(queuenode)
            queuenode.appendChild(self._kv2element('DelaySeconds', DelaySeconds, doc))
            queuenode.appendChild(self._kv2element('MaximumMessageSize', MaximumMessageSize, doc))
            queuenode.appendChild(self._kv2element('MessageRetentionPeriod', MessageRetentionPeriod, doc))
            queuenode.appendChild(self._kv2element('VisibilityTimeout', VisibilityTimeout, doc))
            content = doc.toxml()
        except Exception, e:
            logger.warn('Create content exception %s' % (str(e)))
            return None

        GMT_DATE = self._getGMTDate()
        CONTENT_MD5 = hashlib.md5(content).hexdigest()
        # print '>>> content %s, digest %s' %(content, CONTENT_MD5)
        CONTENT_TYPE = 'text/xml'
        CanonicalizedMQSHeaders = {'x-mqs-version': MQS_VERSION}

        RequestResource = '/%s%s' % (QueueName, ismodify and '?metaoverride=true' or '')
        sig = self._genSignature('PUT', CONTENT_MD5, CONTENT_TYPE, GMT_DATE, CanonicalizedMQSHeaders, RequestResource)        

        conn = httplib.HTTPConnection(self.host, self.port)
        headers = {'Host': self.host,
            'Date': GMT_DATE,
            'Content-Type': CONTENT_TYPE,
            'Content-MD5': CONTENT_MD5,
            sig[0]: sig[1],}
        
        for k in CanonicalizedMQSHeaders.keys():
            headers[k] = CanonicalizedMQSHeaders[k]

        conn.request('PUT', RequestResource, body=content, headers=headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()

        queue = Queue()
        if r.status == httplib.NO_CONTENT:
            error = Error()
            error.Code = 'NO_CONTENT'
            return error
        elif r.status == httplib.CONFLICT:
            error = Error()
            error.Code = 'CONFLICT'
            return error
        elif r.status in (httplib.CREATED, httplib.OK): # OK for setattr
            logger.debug('CreateQueue successful')
            try:
                QueueURL = r.getheader('Location')
                queue = Queue(QueueName, QueueURL)
                return queue
            except Exception, e:
                error = Error()
                error.Code = 'LOCAL_ERROR'
                error.Message = str(e)
                return error
        else:
            error = self._handlerErrorResponse(r, data)
            if error:
                return error

        logger.debug('Error status %d body\n%s', r.status, data)
        return None

    def DeleteQueue(self, QueueName):
        logger.debug('DeleteQueue %s' % (QueueName))
        content = ''
        GMT_DATE = self._getGMTDate()
        CONTENT_MD5 = hashlib.md5(content).hexdigest()
        CONTENT_TYPE = 'text/xml'
        CanonicalizedMQSHeaders = {'x-mqs-version': MQS_VERSION}

        RequestResource = '/%s' % (QueueName)
        sig = self._genSignature('DELETE', CONTENT_MD5, CONTENT_TYPE, GMT_DATE, CanonicalizedMQSHeaders, RequestResource)        

        conn = httplib.HTTPConnection(self.host, self.port)
        headers = {'Host': self.host,
            'Date': GMT_DATE,
            'Content-Type': CONTENT_TYPE,
            'Content-MD5': CONTENT_MD5,
            sig[0]: sig[1],}
        
        for k in CanonicalizedMQSHeaders.keys():
            headers[k] = CanonicalizedMQSHeaders[k]

        conn.request('DELETE', RequestResource, body=content, headers=headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()

        queue = Queue()
        if r.status == httplib.NO_CONTENT:
            logger.debug('DeleteQueue successful')
            return True
        else:
            error = self._handlerErrorResponse(r, data)
            if error:
                return error

        logger.debug('Error status %d body\n%s', r.status, data)
        return None

    def SendMessage(self, QueueName, MessageBody, DelaySeconds=None):
        try:
            doc = minidom.Document()
            messagenode = doc.createElement('Message')
            messagenode.setAttribute('xmlns', 'http://mqs.aliyuncs.com/doc/v1/')
            doc.appendChild(messagenode)
            messagenode.appendChild(self._kv2element('MessageBody', MessageBody, doc))
            if DelaySeconds != None:
                messagenode.appendChild(self._kv2element('DelaySeconds', DelaySeconds, doc))
            content = doc.toxml()
        except Exception, e:
            logger.warn('Create content exception %s' % (str(e)))
            return None

        GMT_DATE = self._getGMTDate()
        CONTENT_MD5 = hashlib.md5(content).hexdigest()
        CONTENT_TYPE = 'text/xml'
        CanonicalizedMQSHeaders = {'x-mqs-version': MQS_VERSION}

        RequestResource = '/%s/messages' % (QueueName)
        sig = self._genSignature('POST', CONTENT_MD5, CONTENT_TYPE, GMT_DATE, CanonicalizedMQSHeaders, RequestResource)        

        conn = httplib.HTTPConnection(self.host, self.port)
        headers = {'Host': self.host,
            'Date': GMT_DATE,
            'Content-Type': CONTENT_TYPE,
            'Content-MD5': CONTENT_MD5,
            sig[0]: sig[1],}
        
        for k in CanonicalizedMQSHeaders.keys():
            headers[k] = CanonicalizedMQSHeaders[k]

        conn.request('POST', RequestResource, body=content, headers=headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()
        error = self._handlerErrorResponse(r, data)
        if error:
            return error
        # print data
        
        message = QueueMessage()
        if r.status == httplib.CREATED:
            logger.debug('SendMessage successful')
            try:
                doc = minidom.parseString(data)
                if doc.childNodes[0].tagName != u'Message':
                    return []
                
                for node in doc.childNodes[0].childNodes:
                    if node.nodeName in MQS_QUEUEMESSAGE_ATTRS:
                        for subnode in node.childNodes:
                            if subnode.nodeType == subnode.TEXT_NODE:
                                setattr(message, node.nodeName, subnode.nodeValue)

                return message
                    
            except Exception, e:
                logger.info('parsing xml exception %s' % (str(e)))
                return None
        
        logger.debug('Error status %d body\n%s', r.status, data)
        return None

    def ReceiveMessage(self, QueueName, peekonly=False):
        logger.debug('ReceiveMessage QueueName %s peekonly %d' % (QueueName, peekonly))
        GMT_DATE = self._getGMTDate()
        content = ''
        CONTENT_MD5 = hashlib.md5(content).hexdigest()
        CONTENT_TYPE = 'text/xml'
        CanonicalizedMQSHeaders = {'x-mqs-version': MQS_VERSION}

        RequestResource = '/%s/messages%s' % (QueueName, peekonly and '?peekonly=true' or '')
        sig = self._genSignature('GET', CONTENT_MD5, CONTENT_TYPE, GMT_DATE, CanonicalizedMQSHeaders, RequestResource)        

        conn = httplib.HTTPConnection(self.host, self.port)
        headers = {'Host': self.host,
            'Date': GMT_DATE,
            'Content-Type': CONTENT_TYPE,
            'Content-MD5': CONTENT_MD5,
            sig[0]: sig[1],}
        
        for k in CanonicalizedMQSHeaders.keys():
            headers[k] = CanonicalizedMQSHeaders[k]

        conn.request('GET', RequestResource, headers=headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()
        error = self._handlerErrorResponse(r, data)
        if error:
            return error
        # print data
        
        message = QueueMessage()
        if r.status == httplib.OK:
            logger.debug('GetQueueAttributes response\n' + data)
            try:
                doc = minidom.parseString(data)
                if doc.childNodes[0].tagName != u'Message':
                    return []
                
                for node in doc.childNodes[0].childNodes:
                    if node.nodeName in MQS_QUEUEMESSAGE_ATTRS:
                        for subnode in node.childNodes:
                            if subnode.nodeType == subnode.TEXT_NODE:
                                setattr(message, node.nodeName, subnode.nodeValue)

                return message
                    
            except Exception, e:
                logger.info('parsing xml exception %s' % (str(e)))
                return None
        
        logger.debug('Error status %d body\n%s', r.status, data)
        return None

    def PeekMessage(self, QueueName):
        return self.ReceiveMessage(QueueName, peekonly=True)

    def DeleteMessage(self, QueueName, ReceiptHandle):
        logger.debug('DeleteMessage QueueName %s ReceiptHandle %s' % (QueueName, ReceiptHandle))
        content = ''
        GMT_DATE = self._getGMTDate()
        CONTENT_MD5 = hashlib.md5(content).hexdigest()
        CONTENT_TYPE = 'text/xml'
        CanonicalizedMQSHeaders = {'x-mqs-version': MQS_VERSION}

        RequestResource = '/%s/messages?ReceiptHandle=%s' % (QueueName, ReceiptHandle)
        sig = self._genSignature('DELETE', CONTENT_MD5, CONTENT_TYPE, GMT_DATE, CanonicalizedMQSHeaders, RequestResource)        

        conn = httplib.HTTPConnection(self.host, self.port)
        headers = {'Host': self.host,
            'Date': GMT_DATE,
            'Content-Type': CONTENT_TYPE,
            'Content-MD5': CONTENT_MD5,
            sig[0]: sig[1],}
        
        for k in CanonicalizedMQSHeaders.keys():
            headers[k] = CanonicalizedMQSHeaders[k]

        conn.request('DELETE', RequestResource, body=content, headers=headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()

        queue = Queue()
        if r.status == httplib.NO_CONTENT:
            logger.debug('DeleteMessage successful')
            return True
        else:
            error = self._handlerErrorResponse(r, data)
            if error:
                return error

        logger.debug('Error status %d body\n%s', r.status, data)
        return None

    def ChangeMessageVisibility(self, QueueName, ReceiptHandle, VisibilityTimeout):
        logger.debug('ChangeMessageVisibility QueueName %s ReceiptHandle %s VisibilityTimeout %s' % (QueueName, ReceiptHandle, str(VisibilityTimeout)))
        GMT_DATE = self._getGMTDate()
        content = ''
        CONTENT_MD5 = hashlib.md5(content).hexdigest()
        CONTENT_TYPE = 'text/xml'
        CanonicalizedMQSHeaders = {'x-mqs-version': MQS_VERSION}

        RequestResource = '/%s/messages?ReceiptHandle=%s&VisibilityTimeout=%s' % (QueueName, ReceiptHandle, str(VisibilityTimeout))
        sig = self._genSignature('PUT', CONTENT_MD5, CONTENT_TYPE, GMT_DATE, CanonicalizedMQSHeaders, RequestResource)        

        conn = httplib.HTTPConnection(self.host, self.port)
        headers = {'Host': self.host,
            'Date': GMT_DATE,
            'Content-Type': CONTENT_TYPE,
            'Content-MD5': CONTENT_MD5,
            sig[0]: sig[1],}
        
        for k in CanonicalizedMQSHeaders.keys():
            headers[k] = CanonicalizedMQSHeaders[k]

        conn.request('PUT', RequestResource, headers=headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()
        error = self._handlerErrorResponse(r, data)
        if error:
            return error
        # print data
        
        message = QueueMessage()
        if r.status == httplib.OK:
            logger.debug('ChangeMessageVisibility successful')
            try:
                doc = minidom.parseString(data)
                if doc.childNodes[0].tagName != u'ChangeVisibility':  # FIXME
                    return []
                
                for node in doc.childNodes[0].childNodes:
                    if node.nodeName in MQS_QUEUEMESSAGE_ATTRS:
                        for subnode in node.childNodes:
                            if subnode.nodeType == subnode.TEXT_NODE:
                                setattr(message, node.nodeName, subnode.nodeValue)

                return message
                    
            except Exception, e:
                logger.info('parsing xml exception %s' % (str(e)))
                return None
        
        logger.debug('Error status %d body\n%s', r.status, data)
        return None

def test():
    print '>>> Running test'
    cf = ConfigParser.ConfigParser()
    cf.optionxform=str
    cf.read('aliyun_mqs.conf')
    Account = dict(cf.items("Account"))
    print '>>> Account', Account
    mq = AliMQS(Account['Host'], Account['OwnerID'], Account['AccessKeyId'], Account['AccessKeySecret'])
    xheaders = {'x-mqs-prefix':'test-'}
    print '>>> _genSignature', mq._genSignature('VERB', 'CONTENT_MD5', 'CONTENT_TYPE', 'GMT_DATE', xheaders, '/')
    print '>>> ListQueue'
    queues = mq.ListQueue()
    print '>>> queues(count %d):' % (len(queues))
    for q in queues:
        print '>>> q', q
        if q.QueueName:
            print '>>> GetQueueAttributes'
            queue = mq.GetQueueAttributes(q.QueueName)
            print '>>> QueueAttributes', queue

    print '>>> CreateQueue'
    queue = mq.CreateQueue('testcreatequeue1')
    
    if isinstance(queue, Error):
        print '>>> error', queue
    else:
        print '>>> created queue', queue

    print '>>> SetQueueAttributes'
    queue = mq.SetQueueAttributes('testcreatequeue1', 15)
    if isinstance(queue, Error):
        print '>>> error', queue
    else:
        print '>>> Set QueueAttributes for queue', queue

    '''
    print '>>> GetQueueAttributes for testcreatequeue1'
    queue = mq.GetQueueAttributes('testcreatequeue1')
    print '>>> testcreatequeue1:', queue

    print '>>> GetQueueAttributes for testcreatequeue2'
    queue = mq.GetQueueAttributes('testcreatequeue2')
    print '>>> testcreatequeue2 or error:', queue

    print '>>> DeleteQueue testcreatequeue1'
    delete_result = mq.DeleteQueue('testcreatequeue1')
    print '>>> delete_result', delete_result

    print '>>> DeleteQueue testcreatequeue2'
    delete_result = mq.DeleteQueue('testcreatequeue2')
    print '>>> delete_result', delete_result

    print '>>> ReceiveMessage in testq'
    message = mq.ReceiveMessage('testq')
    print '>>> received message or error', message

    print '>>> test ReceiveMessage and DeleteMessage' # this test not mean to clean the queue
    for i in range(5):
        print '>>>>>> GetQueueAttributes of testq'
        queue = mq.GetQueueAttributes('testq')
        print '>>>>>> ActiveMessages %s DelayMessages %s' % (queue.ActiveMessages, queue.DelayMessages)
        
        print '>>>>>> ReceiveMessage in testq'
        message = mq.ReceiveMessage('testq')
        print '>>>>>> received message or error', message
        if isinstance(message, Error):
            continue
        QueueName = i%2 and 'testq' or 'testqxxx'
        print '>>>>>> delete message from queue %s with handle %s' % (QueueName, message.ReceiptHandle)
        delete_result = mq.DeleteMessage(QueueName, message.ReceiptHandle)
        print '>>>>>> delete result', delete_result
    '''

    print '>>> SendMessage hello to testq'
    message = mq.SendMessage('testq', 'hello')
    print '>>> message or error', message

    print '>>> PeekMessage from testq'
    message = mq.PeekMessage('testq')
    print '>>> message or error', message

    print '>>> ReceiveMessage from testq'
    message = mq.ReceiveMessage('testq')
    print '>>> message or error', message

    if not isinstance(message, Error):
        print '>>> ChangeMessageVisibility for ReceiptHandle %s in testq' % (message.ReceiptHandle)
        message = mq.ChangeMessageVisibility('testq', message.ReceiptHandle, 10)
        print '>>> message or error', message

if __name__ == '__main__':
    test()