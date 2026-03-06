# Q1：快速理解一个陌生服务的运行状态（基础）

## 背景

你将获得 Datadog read-only key，仅知道：

- `SERVICE_NAME = interviewai-core`
- Datadog 中有 logs / metrics / APM traces
- 业务关注 `chatFirstTimeToken` 一类 latency signal
- 服务包含 websocket / socket 行为，也包含 REST API 行为
- 不提供额外背景文档

## 任务

在限定时间内完成以下内容：

1. 快速梳理该服务的关键观测入口（logs / metrics / traces）
2. 给出 3-5 个最能代表健康度的指标（SLI 候选）
3. 给出你认为最关键的 3 个风险点
4. 输出一份 oncall 可执行 `Runbook v0.1`

## 交付物

- `Service Overview`（1 页内）
- `Key Signals & Health Indicators`
- `Top 3 Risks`（每条包含：事实/推断/待验证）
- `Runbook v0.1`

## 面试官关注点

- 陌生系统学习速度
- 是否能抓住真正关键信号
- 是否有证据链
- 输出是否可执行
