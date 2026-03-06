# Candidate Pack (`makrodnw`)

> 请按顺序完成：Q1 -> Q2 -> Q3。不要一次性跳到最后。

## 开始方式

```bash
# 本地逐题查看
make makrodnw        # 显示下一题
make q1              # 强制查看 Q1
make q2
make q3
```

## 题目入口

- [Q1 - 快速理解陌生服务](questions/Q1-service-overview.md)
- [Q2 - 最近错误日志分析](questions/Q2-error-analysis.md)
- [Q3 - 沉淀 AI skill/workflow](questions/Q3-workflow-skill.md)
- [提交模板](templates/submission-template.md)

## 统一约束

- 只读查询，不得创建/修改/删除 Datadog 资源。
- 结论必须有证据（logs / metrics / traces）。
- 将“事实 / 推断 / 假设 / 待验证项”分开写。
- 不得在提交中泄露 token、敏感用户数据、完整原始 payload。
