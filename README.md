# 阿里云MQS队列服务python客户端(Aliyun MQS python client)

## 使用方法(Usage)

* 参考aliyun_mqs.py里面的test函数 (referer to test() function in aliyun_mqs.py)
* cp aliyun_mqs.conf-sample aliyun_mqs.conf
* 配置aliyun_mqs.conf 文件即可运行 ./aliyun_mqs.py，如果不是运行例子则不需要使用这个配置文件，你可以用自己的方式来配置 (configure aliyun_mqs.conf and run ./aliyun_mqs. aliyun_mqs.conf is not required unless you are running the example.)

## 更多例子 (more examples)
* sample_consumer.py / sample_producer.py 是一对消费者/生产者例子，可以参考一下 (sample_consumer.py / sample_producer.py)
* 需要手工创建testq这个队列 (you will need to crete testq manually first.)

## 仓库地址 (Repositories)
* bithucket: https://fluke.l@bitbucket.org/fluke.l/aliyun_mqs_python_client.git
* github: https://github.com/heyfluke/aliyun_mqs_python_client.git

## MIT License

Copyright (C) 2014 Yongchao Lao

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.