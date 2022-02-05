---
typora-copy-images-to: upload
---

### 从零搭建邮件服务器（只收不发阉割版）

参考文章

[一沟绝望的死水：模拟邮件服务器，批量注册利器](https://cloud.tencent.com/developer/article/1511808)

相关技术

[postfix](http://www.postfix.org/)

----

前段时间撸NFT白名单，比如冠[希哥的2426C](https://www.nvlpe.io/)直接邮箱验证抽奖就可以参与。当时嫌搭一个邮件服务器比较麻烦，就直接找了个现成的，一波撸了几十万个邮箱，捉摸着多少也能中点。

**万万没想到，这现成的自搭邮件服务器直接给我邮件清空了......**

据可靠消息，有人一万多个邮箱撸到了60多个白名单（一个白名单1ETH）.... 

我的心更痛了...

于是决定自己搭一个，网上找了下资料，发现许多文章讲了个大概，正儿八经满足需求的不多，这边趁自己刚好做了一个，就顺便记录一下。

----

#### 1.准备工作

- [x] 一个已经备案的域名
- [x] 一台服务器（需开放25端口）
- [x] mysql数据库（邮件解析完直接落库，查找效率更快）



#### 2.域名解析

例:域名为**coolmail.com**

> 配置A记录

记录类型 - A记录

主机记录 - mx

记录值 - 你的服务器IP



> 配置MX记录

记录类型 - MX

主机记录 - @

记录值 - mx.coolmail.com



如此一来，xxx@coolmail.com 均为你的可用邮箱



#### 3.服务器环境配置

笔者使用的服务器规格为2核2G

系统为Debian10

**切记开放25端口**



安装postfix

```shell
sudo apt install postfix
```



修改postfix配置文件（/etc/postfix/main.cf）

```shell
mydestination = $myhostname, coolmail.com, localhost.localdomain, localhost
```

这里只需要将你的备案域名加入即可，其他不用动



保存配置

```shell
sudo postfix reload
```

至此，你已经可以往该域名对应的邮箱投递邮件了，但是**必然投递失败**



![WeChat498d0fd65f9389325358507e9b36bcd4](https://tva1.sinaimg.cn/large/008i3skNly1gz306ka668j321a0g8gp5.jpg)

原因简单说，就是**没有创建收件人，邮件服务器无法分发该邮件到对应收件人，因而退信**

也许你会想，那多麻烦，我每个邮箱都还要创建一个收件人，那自建邮件系统有个啥用....

**问题不大，继续往下看**



#### 4.邮件服务器配置

解决思路大致如下

- [x] 创建一个邮件账户（比如admin@coolmail.com)
- [x] 将所有邮件都路由到该账户下

这样就实现了无限邮箱且不用挨个注册的效果



创建admin用户

```shell
sudo adduser admin
usermod -aG sudo admin
```



修改postfix配置

```shell
canonical_maps = regexp:/etc/postfix/canonical-redirect
```



创建/etc/postfix/canonical-redirect文件并写入以下内容

```shell
/^.*$/ root@your.domain
```



重新加载postfix配置

```shell
sudo postfix reload
```



再次发送邮件到xxxx@coolmail.com

此时邮件已经成功的发送并统一投递到admin@coolmail.com



查看邮件

```shell
cat /var/mail/admin
```

![WeChat7b36a0f6d20aad6332e304ced9fed075](https://tva1.sinaimg.cn/large/008i3skNly1gz30i05yurj30u00vn0y7.jpg)

这就是原始邮件（厚码了，大家看个大概就行）

这里可以看到，原始邮件是发送给daeoho@coolmail.com 的，因为之前的转发配置，被分发到了 admin@coolmail.com

这样，我们就可以用一个admin@coolmail.com收取任意xxx@coolmail.com 的邮件

**目前为止，基本上已经完成我们「只收不发阉割版」的目的**

但是，咱们收了邮件就要去读取啊，不能每次都看着这么一串恶心的原始数据吧，找个邮件不能检索文件吧...

接下来就开始处理这部分邮件



#### 5.处理邮件

因为笔者个人的需求，处理方式是将邮件简单解析后落到数据库，方便后期检索

目标解析字段

- [x] from - 发送者
- [x] to - 接受者
- [x] subject - 主题
- [x] content - 正文

这边贴一段不成熟的python代码...

```python
import json
import sys
from email.parser import Parser

from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

email_input = sys.stdin.readlines()

engine = create_engine(
    'mysql+pymysql://user:password@host:3306/db_name')
DBSession = sessionmaker(bind=engine)
Base = declarative_base()


class MailList(Base):
    __tablename__ = 'mail_list'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String)


class MailListParse(Base):
    __tablename__ = 'mail_list_parse'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String)
    sender = Column(String)
    to = Column(String)
    subject = Column(String)


def record_original(data):
    session = DBSession()
    session.add(MailList(content=data))
    session.commit()

    session.close()


def record_parse(sender, to, subject, content):
    session = DBSession()
    session.add(MailListParse(content=content, sender=sender, to=to, subject=subject))
    session.commit()
    session.close()


data = ""
for line in email_input:
    data = data + line
record_original(data)

email = Parser().parsestr(data)
body = []
for payload in email.get_payload():
    body.append(str(payload))
to = str(email['to'])
if to.index("<") > 0:
    to = to[to.index("<") + 1: to.index(">")]
sender = email['from']
if sender.index("<") > 0:
    sender = sender[sender.index("<") + 1: sender.index(">")]
record_parse(sender, to, email['subject'], json.dumps(body))

```

安装一下相关依赖，这个就不多说了



修改postfix配置

```shell
local_recipient_maps =
canonical_maps = regexp:/etc/postfix/canonical-redirect
mailbox_command = /etc/postfix/read_mail.py
default_privs = admin
```

read_mail.py 就是上述这段代码

**注意**

read_mail.py 需要在第一行加上一行代码，否则会各种异常

```she
#!/usr/bin/python3
```

保存配置

再次发送邮件

邮件经解析后，就会写入数据库，之后就根据项目方的发件邮箱，专门处理对应邮件正文即可

---

#### 6.其他

每个人的需求不一样，这边只是提供个思路，如果完全按照我的配置，也是可以运行的

起码不至于找了许多文字都只说了个大概，正儿八经去配，发现细节各种问题

接下来吧，继续去撸白名单呗

**顺便打个广告** Discord工具有需要的话可以联系咱蛤

- [x] 自动聊天
- [x] 自动回复
- [x] 管理员专属配置（禁言，回复，扫地等等）
- [x] 批量邀请
- [x] 自动进群
  - [x] 无验证进群
  - [x] 同意协议进群
  - [x] 表情验证进群
  - [x] 同意协议后表情验证进群

...

多账号同时运行

不定时送免费双绑号给大家

无需账号密码，安全可靠

国外代理IP（100W+），保证不会出现同IP多账号被封的情况（有部分工具用的是本地环境或者服务器环境，他们都是单IP运作的，封号是迟早的事情）

若是因为自动进群被封，我们包赔付账号（双绑号赔双绑号，单绑号赔单绑号）

有需要的话联系咱蛤

![2161644073126_.pic](https://tva1.sinaimg.cn/large/008i3skNly1gz313e62o0j30s310u0v4.jpg)

