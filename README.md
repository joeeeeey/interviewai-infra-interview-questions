# Infra 面试题（Datadog Read-only）

这个目录可直接作为 GitHub Public Repo 的内容，用于 Infra / Observability 面试作业。

核心目标：在陌生服务上下文中，考察候选人的证据驱动分析能力、排障优先级判断能力、以及把个人方法沉淀成团队 workflow 的能力。

## 仓库特点

- 题目按 `Q1 -> Q2 -> Q3` 递进。
- 提供 `makrodnw`（你要求的入口）用于逐题展示。
- 明确只读与数据安全边界。
- 默认不包含任何真实 key。

## 目录结构

- `makrodnw.md`: 给候选人的主入口（可直接发链接）
- `questions/`: 三道题的详细说明
- `templates/submission-template.md`: 候选人提交模板
- `scripts/show_question.sh`: 逐题展示工具（支持 `next`）
- `scripts/self_attempt.py`: 用本地临时 key 做一次“候选人自测”并生成产出
- `tmp-cred.example.md`: 临时 key 文件格式示例

## 快速使用

```bash
# 1) 查看题目（逐题）
make makrodnw          # 默认显示下一题（next）
make q1
make q2
make q3

# 2) 候选人提交模板
cat templates/submission-template.md

# 3) 面试官本地自测（需要本地 tmp-cred.md，且不会提交）
make self-attempt
```

## 安全说明

- `tmp-cred.md` 已加入 `.gitignore`，不会被提交。
- `artifacts/`（本地跑题产出）已加入 `.gitignore`，避免误提交真实观测数据。
- `draft.md` 与 `interviewer/` 为内部资料，默认不提交到 public repo。
- 公开仓库仅保留题目与模板，不包含任何真实环境截图/日志原文。
