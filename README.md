# 赞助
<div style="text-align: center;">
    <a href="https://yxvm.com/">
        <img src="https://raw.githubusercontent.com/betteryjs/lightweightserver/refs/heads/master/images/logo.webp" >
    </a>
</div>

我们非常感谢 [Yxvm](https://yxvm.com/) 提供了支持本项目所需的网络基础设施。


# 前言

通过阿里云的 AccessKeyId AccessKeySecret 管理帐号下的轻量应用服务器
用户在TG bot操作 适合上不去帐号的


# 安装部署
- 克隆项目
```shell
git clone  git@github.com:betteryjs/lightweightserver.git
cd lightweightserver
```
- 复制 `config.json.exp`到 `config.json` 并填入配置信息

```shell

{
  "BaseConfig": {
    "TGBotAPI": "xxxxxx", # 填入在Botfather创建的Telegram Bot
    "chartId": "xxxx",    # 填入你的会话id 通过 @get_myidbot 获取
    "authorized_users": [
      "example"     # 授权的用户 谁可以使用这个bot 填入@后面的用户名 例如 @example 填入example
    ]
  },
  "LightConfig": [
    {
      "AccessKeyId": "xxxxxxx", # 填入阿里云AccessKeyId
      "AccessKeySecret": "xxxxxx", # 填入阿里云AccessKeyId
      "InstanceId": "xxxxxx",  # 填入阿里云轻量的实例ID
      "region_id": "cn-hongkong",  # 填入机器的地域ID 通过 https://help.aliyun.com/document_detail/40654.html 查看
      "DefaultPassword":"password",  # 填入要重置系统的密码
      "name": "Light-HK-200M",     # 填入独一无二的name 
      "SnapshotCrons": "0 3 * * *"  # 填入自动快照策略的创建时间 默认每天凌晨3点 功能还在测试 可以不开启
    }
  ]
}

```
- 安装`Python`环境
```shell
./initvenv.sh
```
- 开启或者重启服务
```shell

./restart.sh
```

