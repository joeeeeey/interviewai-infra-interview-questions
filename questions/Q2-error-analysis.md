# Q2：最近错误日志分析（进阶）

## 任务

在 Q1 基础上继续：

1. 找出最近最值得关注的 10 条 error logs 或 10 个 error patterns
2. 对错误做分类/聚类（依赖失败、连接、鉴权、业务、资源等）
3. 区分噪音 vs 真正影响用户体验的问题，并给依据
4. 输出排查优先级和下一步

## 交付物

- `Top 10 error patterns`（或样本 + 聚类）
- `Error taxonomy`
- `Noise vs Impact`（判定依据）
- `Prioritized investigation plan`

## 面试官关注点

- 去噪能力
- 聚类与结构化表达
- 用户影响判断
- logs / metrics / traces 交叉验证

## 额外现实约束

- 只读 API 可能遇到速率限制（429），请展示你的节流/重试策略。
