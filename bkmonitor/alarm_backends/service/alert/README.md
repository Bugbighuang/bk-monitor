# Alert


## 功能

### 数据来源

- 第三方事件数据：从 transfer 写入到 Kafka
- 监控策略事件数据：
    - 异常事件：从 trigger 写入到 Kafka
    - 恢复和关闭事件：从 event-manager 写入到 Kafka

### 数据处理流程

1. 从 Kafka 拉取事件数据，对事件进行简单格式化
2. 将事件写入到 Elasticsearch

 
### 输出
    
对于所有状态发生变更的告警，发送信号

状态发生变更的定义如下
- 新产生的异常告警
- 告警状态 (异常 -> 恢复/关闭)

包含的信号种类如下
- 即时动作信号：如果告警是由监控策略产生的，则直接推送动作执行信号到 Action 队列
- 关联策略信号：用于后续的关联策略检测


## 其他

- 模块需统计指标数据，能代表目前的处理能力
- 完善的日志记录
- 单元测试