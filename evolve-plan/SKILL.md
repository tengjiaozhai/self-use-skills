---
name: evolve-plan
description: 演进项目的 Living PLAN 和 Evolution Graph。用于仓库已有 PLAN.md 或 evolution/，且用户要求规划或推进下一 revision；也用于用户明确要求在指定项目中初始化这套工作流时。
---

# 演进 Plan

推进唯一的 Living `PLAN.md`，并用稀疏的 Evolution Graph 保存长期有效的设计理由。

行动前完整阅读 [references/runtime-contract.md](references/runtime-contract.md)。它是文件路径、Graph 语义、上下文预算、写入分支、失败处理和完成标准的唯一事实源。

## 1. 检查

严格按照 Runtime Contract 确定项目根目录，并选择 `draft` 或 `advance`。

运行：

```bash
python3 <skill-dir>/scripts/evolution_graph.py inspect --root <project-root> [--area <area> ...]
```

使用命令返回的路径和哈希。读取每个选中 Node 的正文，以及证明 `Current` 所需的代码、配置、测试和 Git 事实。

只有同时满足以下条件才完成本步骤：项目根目录唯一、Graph 校验通过、每个种子 Node 都有选择依据、每项 `Current` 陈述都有仓库事实支撑。

## 2. 演进

使用 [assets/PLAN.template.md](assets/PLAN.template.md) 构建下一轮 Plan。只保留一条可执行路径，并让每个 Plan 步骤说明预期结果和验证方式。

对每个可能的设计变化应用 Runtime Contract 的四道门。四道门全部通过时，使用 [assets/evolution-node.template.md](assets/evolution-node.template.md) 为每个独立变化理由创建一个 Node。已有 Node 完整表达同一决定时复用已有 Node。

本次运行新提出的偏好不能通过 `Decided`。影响外部契约、安全边界、数据兼容、成本或迁移结果的选择，在用户或仓库确立之前必须保持 unresolved。

只有同时满足以下条件才完成本步骤：Plan 内部一致、每条候选 Edge 指向实际被改变或依赖的设计、每个 Node 决定都有四道门结论、没有把 unresolved 选择表述为已接受决定。

## 3. 完成选定分支

### Draft 分支

返回完整 Plan 提案、可能存在的 `EV-NEXT` 提案，以及 Runtime Contract §9 定义的标准结果块。`Files` 必须完整列出为证明 `Current` 而读取的每个文件；`Decision` 必须公开每个 unresolved 设计选择。保持零写入不变量。

只有提案满足 Runtime Contract 的全部 `draft` 完成标准，并且工作树与运行前状态一致时才完成。

### Advance 分支

在项目树外暂存完整 Plan 和所有新 Node。再次运行 `inspect`；只有返回哈希仍与首次检查一致时才写入：

```bash
python3 <skill-dir>/scripts/evolution_graph.py apply \
  --root <project-root> \
  --plan-source <staged-PLAN.md> \
  --expected-plan-sha <sha> \
  --expected-graph-sha <sha> \
  [--node-source <staged-EV.md> ...]
```

根据写入后的实际状态返回 Runtime Contract §9 定义的标准结果块。`Files` 必须完整区分为证明 `Current` 而读取的文件和实际修改的文件；`Decision` 必须公开每个 unresolved 设计选择。

只有同时满足以下条件才完成：`apply` 成功、写入后校验通过、有效变化使 revision 恰好增加一次、修改文件仅限 `PLAN.md` 和必要的 `evolution/*.md`。
