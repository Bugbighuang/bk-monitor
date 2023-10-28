## 社区版故障自愈升级说明

### 版本依赖：
监控saas版本： > 3.6.x

监控后台版本： >= 3.6.2435

标准运维版本： >= 3.24.5
> 说明： 标准运维版本依赖强依赖， 其他版本的标准运维可通过标准运维管理员后台(o/bk_sops/django_admin/core/environmentvariables/）提前配置变量名为 APP_WHITELIST ，值为bk_monitorv3

### 部署说明
1. 迁移需要通过配置环境  `BKAPP_NEED_MIGRATE_FTA = True` 条件，才会触发迁移
2. 本次迁移是通过直连故障自愈的DB进行数据转移，故障自愈DB如果在默认的mysql服务器上，则不需要配置DB信息，如果自愈为独立DB，则需要配置以下几个环境变量
   - `BKAPP_FTA_DB_NAME`： DB名称
   - `BKAPP_FTA_DB_USERNAME`： 用户名
   - `BKAPP_FTA_DB_PASSWORD`： 密码
   - `BKAPP_FTA_DB_HOST`： 服务器IP或域名
   - `BKAPP_FTA_DB_PORT`： DB端口
3. 如果自动迁移失败，需要手动尝试，可通过在BK_APPO的机器上手动执行：bk_biz_id为对应的业务ID，多个以逗号分隔
   ```shell
   docker exec -it `docker ps | grep "bk_monitorv3" | awk '{print($1)}'` bash -c "cd /data/app/code/ ; /cache/.bk/env/bin/python manage.py migrate_fta_strategy bk_biz_id"
   ```

### 迁移内容
#### 1、 内置处理套餐的迁移： 
包括以下五项，均通过调用标准运维流程实现， 其中原有的磁盘清理迁移之后为标准运维磁盘清理流程，可通过选择标准运维类型套餐来进行内置磁盘清理配置
  - 【快捷套餐】微信发送内存使用率 Top 10 进程
  - 【快捷套餐】微信发送 CPU 使用率 Top 10 进程
  - 【快捷套餐】转移主机至故障机模块
  - 【快捷套餐】转移主机至空闲机模块
  - 【自愈套餐】磁盘清理(适用于Linux) 
#### 2、 普通套餐的迁移
  - 原有的作业平台和标准运维套餐保持类型不变
  - 原有的http回调调整为webhook回调
  - 原有的通知不做迁移，默认使用监控的通知
  - 原有的组合套餐迁移采用标准运维流程实现，现有自愈不再支持组合套餐功能

#### 3、 告警源的迁移， 目前支持以下四个告警源：
  - rest拉取
  - rest推送
  - zabbix
  - 原有的监控平台对接直接接入新版监控策略
#### 4、 自愈接入的迁移：
  - 所有自愈接入的内容，将会在监控策略对应业务下创建对应的策略
  - 原有自愈接入的通知方式和人员信息，将以告警组的方式进行迁移
  - 原有的全局防御，目前迁移为同策略下的告警防御策略，见策略详情告警处理部分

### 迁移影响
由于自愈在产品形态后台架构完全不同，因此本次迁移仅作数据迁移，以下几点需要在迁移之后进行人工确认
- 告警源： 由于监控告警源对接为新模块，其中rest推送和zabbix告警源在迁移之后，需要根据新版本的说明重新进行推送事件的配置才能生效。原有的监控3.2对接不再支持
- 部分组合套餐包含了内置套餐（进程CPU和MEM TOP10发送, 磁盘清理）和 使用了标准运维套餐为节点的，由于迁移不支持子流程迁移， 需要用户手动配置确认
- 所有的自愈接入策略迁移之后，将会关闭原有自愈接入，新版本默认为不开启状态，需要用户确认
- 原对接监控平台的自愈接入，如果设置了监控目标，请注意检查原策略是否设置了有设置监控目标，如果无， 请设置为全业务，否则小目标范围优先生效的规则将不生效。


