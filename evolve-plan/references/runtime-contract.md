# Evolve Plan Runtime Contract

本文件是 `evolve-plan` Skill 的权威运行契约。Skill 的步骤只引用本文件，不复制这里的规则。

## 目录

1. [术语与不变量](#1-术语与不变量)
2. [输入与项目发现](#2-输入与项目发现)
3. [当前 Evolution 节点](#3-当前-evolution-节点)
4. [相关子图检索](#4-相关子图检索)
5. [Evolution 创建判定](#5-evolution-创建判定)
6. [ID 分配与 Graph 校验](#6-id-分配与-graph-校验)
7. [运行模式与写入边界](#7-运行模式与写入边界)
8. [缺失、损坏与冲突处理](#8-缺失损坏与冲突处理)
9. [输出与完成标准](#9-输出与完成标准)

## 1. 术语与不变量

### 1.1 权威事实

| 对象 | 回答的问题 | 权威来源 |
| --- | --- | --- |
| `PLAN.md` | 下一步做什么 | 项目根目录当前文件 |
| Evolution Graph | 为什么变成现在这样 | `evolution/*.md` |
| Code | 现在实际上是什么 | 当前工作树 |
| Git | 具体发生过什么变化 | Git 历史 |

Code 与 `PLAN.md` 不一致时，以 Code 描述 `Current`，再让新 Plan 收敛二者。

### 1.2 Plan revision

项目只保留一个 `PLAN.md`。每次接受新的有效计划时：

1. 原位更新 `PLAN.md`。
2. 将 `revision` 增加 `1`。
3. 让 Git 保存旧内容。

不创建 `PLAN-v1.md`、`PLAN-v2.md` 或 Plan Graph。`revision` 是当前计划的单调版本号，不是长期历史。

没有实际内容变化时保持原 revision。

### 1.3 Evolution Node

一个 Evolution Markdown 文件是一个 Node。Node 记录已经形成的关键设计决定，不记录待选方案或执行步骤。

正式 Edge 只有：

- `evolves_from`：当前设计从哪些设计演进而来。
- `depends_on`：当前设计依赖哪些仍有独立解释价值的设计。

Evolution Graph 的长期单位是设计变化，不是 Plan revision。

### 1.4 文件形态

新建或规范化 `PLAN.md` 时使用 [`../assets/PLAN.template.md`](../assets/PLAN.template.md)。

新建 Evolution Node 时使用 [`../assets/evolution-node.template.md`](../assets/evolution-node.template.md)。

## 2. 输入与项目发现

### 2.1 必需输入

一次运行必须获得：

- 当前需求：用户要求、验收标准和明确约束。
- 项目根目录。
- 当前工作树中与需求相关的代码和配置。
- 规范位置存在时的 `PLAN.md` 与 `evolution/*.md`。

当前需求缺少会改变外部契约、安全边界、数据兼容、成本或迁移结果的决定时：

- `draft` 保持该决定为 unresolved，并给出推荐选项及影响。
- `advance` 进入 `blocked`，只提出解除阻塞所需的最少问题。

模型在本次运行中提出的偏好不自动成为已接受决定。

### 2.2 项目根目录

按以下顺序确定一个项目根目录：

1. 当前目录属于 Git 仓库时，使用 `git rev-parse --show-toplevel`。
2. 不属于 Git 仓库时，从当前目录向上查找同时容纳 `PLAN.md` 或 `evolution/` 的最近目录。
3. 两者都不存在时，只有用户明确把当前目录指定为项目目录，才使用当前目录初始化。

找到多个候选根目录且无法从当前目录唯一确定时进入 `blocked`，不选择猜测路径。

### 2.3 规范位置

只认以下位置：

```text
<project-root>/PLAN.md
<project-root>/evolution/*.md
```

发现 `plans/`、`PLAN-v*.md`、`docs/plan.md` 或其他候选计划文件时：

- 规范文件存在：把其他文件视为非权威材料，不自动合并。
- 规范文件不存在：进入 `blocked`，列出候选文件并要求先确定迁移来源。

### 2.4 读取顺序

按以下顺序建立规划上下文：

1. 当前需求和适用的项目指令。
2. `PLAN.md` frontmatter、`Goal`、`Current`、`Plan`、`Progress`。
3. Evolution 索引和校验结果。
4. 相关 Evolution 子图。
5. 与需求和 Plan 直接相关的代码、配置、测试和 Git 事实。

完成标准：

- 每个 `Current` 事实都有代码、配置、测试或运行结果依据。
- 每个选中的 Evolution area 都能回指需求、Plan context 或代码入口。
- 没有为了“了解整个仓库”而无边界读取无关文件。

## 3. 当前 Evolution 节点

### 3.1 Node schema

Skill Runtime V1 使用以下字段：

```yaml
id: EV-003
date: 2026-07-29
area: auth
evolves_from:
  - "[[EV-002-jwt-auth]]"
depends_on:
  - "[[EV-010-session]]"
status: adopted
```

规则：

- `id`、`date`、`area`、`evolves_from` 必须存在。
- `depends_on` 可省略，省略时按空列表读取；新 Node 必须显式写出。
- `status` 可省略，省略时按 `adopted` 读取；新 Node 必须显式写出。
- `status` 只能是 `adopted` 或 `abandoned`。
- `adopted` 表示设计曾被项目接受。
- `abandoned` 表示设计被明确放弃，不代表它从历史中删除。
- `id` 创建后不可修改。
- `area` 使用小写 kebab-case，并从项目实际设计领域自然产生。
- 根节点使用 `evolves_from: []`。
- 无设计依赖时使用 `depends_on: []`。

### 3.2 Current leaf

对每个 area 单独计算 Current leaf：

1. 只考虑 `status: adopted` 的 Node。
2. 建立 `evolves_from` 的反向索引。
3. 没有被同 area 的 adopted Node 继续演进的 Node 是 Current leaf。

`depends_on` 不参与 Current leaf 计算。

一个 area 可以有多个 Current leaf，表示仍然存在的并行设计分支。Skill 必须保留这种多分支事实。

### 3.3 选择当前节点

按以下证据选择与本次需求相关的 Current leaf：

1. `PLAN.md.context` 中仍存在且与需求相关的 Current leaf。
2. area 与需求或代码入口直接匹配的 Current leaf。
3. 标题和正文描述了本次要改变能力的 Current leaf。

多个节点都有直接证据时全部保留。证据不足以区分多个互斥节点时进入 `blocked`。

完成标准：

- 每个种子节点都有一条可陈述的选择依据。
- 已发现的相关并行分支没有被静默丢弃。
- 没有把 `depends_on` 目标误判为历史前序。

## 4. 相关子图检索

### 4.1 检索预算

Runtime V1 使用固定预算：

```yaml
max_evolves_from_hops: 3
max_depends_on_hops: 1
max_nodes: 12
```

修改预算属于 Runtime Contract 变更，不由单次运行临时决定。

### 4.2 遍历顺序

从选中的 Current leaf 开始：

1. 收集所有种子节点。
2. 按距离从近到远沿 `evolves_from` 回溯，最多三跳。
3. 对已收集的种子和历史节点读取一跳 `depends_on`。
4. 去重后按优先级裁剪到十二个 Node。

优先级从高到低：

1. 种子节点。
2. 更近的 `evolves_from` 前序。
3. 种子的直接 `depends_on`。
4. 历史节点的直接 `depends_on`。
5. 更远的前序节点。

同优先级按 `date` 降序、`id` 降序保持稳定顺序。

### 4.3 预算冲突

种子节点本身超过十二个时进入 `blocked`，不随机裁剪。

裁剪非种子节点时，在结果中列出被省略的 Node ID 和原因。被省略节点不进入模型的正文上下文。

### 4.4 空结果

Graph 合法但没有相关 Node 时使用空子图继续规划。空结果不触发历史补写，也不允许根据当前代码虚构过去的演进。

完成标准：

- 子图不超过十二个 Node。
- 每个收集节点都能沿允许的 Edge 回到种子。
- 遍历顺序和裁剪结果在同一输入下稳定。

## 5. Evolution 创建判定

### 5.1 四道门

只有同时通过以下四道门，才创建 Evolution Node：

1. **Decided**：方案已经由用户要求、仓库既有决定或用户接受的 Plan 确立，不是模型在本次运行中新提出的偏好。
2. **Material**：方案改变架构、技术路线、系统边界、核心能力，或推翻已有重要设计。
3. **Grounded**：变化能由当前需求、代码事实和新 Plan 共同证明。
4. **Durable**：半年后理解当前系统时，仍可能追问这次变化的原因。

任一道门未通过时，变化留在 `PLAN.md` 和 Code，不进入 Graph。

在 `draft` 中，可以展示条件性的 `EV-NEXT` 草案，但必须把未通过的门标为 `pending`；条件草案不是已经形成的 Evolution 决定。`advance` 只有在四道门全部通过时才能创建真实 Node。

### 5.2 创建粒度

一个 Node 表达一个可独立回答“为什么变化”的设计概念。

- 多个执行步骤共同实现一个设计变化：创建一个 Node。
- 两个变化拥有不同原因、不同前序或可以独立撤销：创建两个 Node。
- Graph 中已有 Node 完整表达同一决定：复用已有 Node，并把它加入 `PLAN.md.context`。

### 5.3 前序和依赖

设置 `evolves_from` 时：

- 连接本次改变的真实 Current leaf。
- 合并多个设计分支时列出所有真实前序。
- 新领域没有历史前序时使用空列表。

设置 `depends_on` 时：

- 只连接拥有独立长期解释价值的设计依赖。
- 普通代码调用、文件引用和库依赖留在 Code。

### 5.4 未知原因

Code 已经改变但无法从需求、Plan、Git 或现有 Evolution 确认“为什么”时：

- 在 `PLAN.md.Current` 明确记录事实和未知原因。
- 不补写推测性的 Evolution Node。

完成标准：

- 每个新 Node 都有四道门的逐项证据。
- 每个前序 Edge 都连接实际被改变的设计。
- 普通 Bug、样式、测试、重命名和局部重构归入 Plan/Code 路径。

## 6. ID 分配与 Graph 校验

### 6.1 ID 分配

创建 Node 前：

1. 扫描所有合法 `EV-<number>` ID。
2. 取最大数字加 `1`。
3. 使用至少三位十进制格式，例如 `EV-009` 后为 `EV-010`。
4. 永不复用空洞或 abandoned Node 的 ID。
5. 写入前重新扫描一次；发生冲突时重新分配一次，第二次冲突进入 `blocked`。

文件名格式：

```text
EV-003-short-kebab-slug.md
```

frontmatter `id` 必须与文件名前缀一致。Wikilink 使用不带 `.md` 的完整文件 stem。

### 6.2 写入前校验

任何 `advance` 写入前，Graph 必须满足：

- 每个 Markdown 都有合法 YAML frontmatter。
- 字段集合符合 Runtime V1 schema；必需字段齐全，可选字段缺失时使用规范默认值。
- `id` 和文件名前缀一致且全局唯一。
- `date` 是合法 `YYYY-MM-DD`。
- `area` 是小写 kebab-case。
- 两类 Edge 都是字符串列表。
- 每个 Wikilink 目标存在。
- Node 不引用自身。
- `evolves_from` 是有向无环图。
- `status` 取值合法。
- 正文包含且只包含一个 H1 标题，以及“为什么变化”“发生了什么”“最终结果”三个 H2。

`depends_on` 环只报告为设计风险，不判定 Graph 文件损坏；自依赖仍然非法。

### 6.3 写入后校验

写入后重新运行全部校验，并额外确认：

- `PLAN.md.context` 中每个 Wikilink 都存在。
- 新 Node 的所有前序和依赖都存在。
- 新 ID 没有重复。
- Current leaf 结果与新设计关系一致。

写入后校验失败时恢复本次触及文件的写入前内容，并进入 `blocked`。

## 7. 运行模式与写入边界

Skill 有两个运行分支：`draft` 和 `advance`。

### 7.1 draft

以下任一条件选择 `draft`：

- Codex 当前处于 Plan mode。
- 用户要求检查、分析、建议或预览。
- 当前环境没有项目写入能力。
- 目标 `PLAN.md` 或相关 Evolution 文件在读取前已经有未确认修改。

`draft` 执行完整调研、检索、规划和 Evolution 判定，但：

- 不修改文件。
- 不递增 revision。
- 候选 Evolution ID 使用 `EV-NEXT`，不占用真实 ID。

输出可直接写入的 `PLAN.md` 提案，以及必要时的 Evolution Node 提案。

### 7.2 advance

同时满足以下条件才选择 `advance`：

- 用户明确要求创建、更新、推进或持久化当前计划。
- 当前模式允许项目文件写入。
- Runtime Contract 的输入和 Graph 校验通过。
- 目标文件从读取到写入期间没有变化。

`advance` 按以下顺序执行：

1. 记录目标文件内容哈希。
2. 生成完整的新 Plan 和候选 Evolution Node。
3. 应用四道门。
4. 需要新 Node 时分配真实 ID。
5. 对暂存内容执行写入前校验。
6. 以临时文件暂存全部目标。
7. 先放置新 Evolution Node，再原子替换 `PLAN.md`。
8. 执行写入后校验。
9. 失败时恢复本次触及文件。

Skill 修改工作树，不自动创建 Git commit。

### 7.3 Revision 与 context

`advance` 产生有效 Plan 变化时：

- `revision` 恰好增加 `1`。
- `updated` 写当前本地日期。
- `context` 只列出本次规划的种子 Evolution Node。
- 祖先和依赖通过 Graph 遍历获得，不重复写入 `context`。

创建新 Evolution Node 时，新 Node 成为相关 area 的新种子并写入 `context`。

完成标准：

- `draft` 分支零文件写入。
- `advance` 分支要么全部写入并通过校验，要么恢复到写入前状态。
- 同一输入和同一工作树状态选择相同分支。

## 8. 缺失、损坏与冲突处理

### 8.1 初始化矩阵

| `PLAN.md` | `evolution/` | 处理 |
| --- | --- | --- |
| 不存在 | 不存在 | `draft` 给出初始化提案；`advance` 创建 revision 1 的 Plan 和空目录 |
| 不存在 | 合法 | 从当前需求、Code 和相关子图创建 revision 1 的 Plan |
| 合法 | 不存在 | 使用现有 Plan 继续；`advance` 需要时创建空目录 |
| 合法 | 合法 | 执行正常流程 |

初始化现有项目时不虚构历史 Node。只有已知且通过四道门的决定才能成为第一个根 Node。

### 8.2 非规范 Plan

`PLAN.md` 缺少规范 section 时：

1. 把能够唯一映射的内容映射到 `Goal`、`Current`、`Plan`、`Progress`。
2. 非空内容无法唯一映射时进入 `blocked`，列出未映射标题。
3. 可完全映射时，在提案或写入中规范化，并按一次有效变化递增 revision。

### 8.3 Graph 损坏

写入前校验失败时：

- 进入 `blocked`。
- 输出全部校验错误及文件路径。
- 不更新 Plan，也不创建 Node。

Graph 修复是独立任务；规划 Skill 不以跳过坏节点的方式继续写入。

### 8.4 Plan 与 Code 漂移

发现 Plan 的 `Current` 与 Code 不一致时：

- Code 决定新的 `Current` 描述。
- 新 Plan 明确列出需要收敛的差异。
- 只有能够确认设计原因时才创建 Evolution Node。

### 8.5 并发和已有修改

读取前目标文件已有未确认修改时降级为 `draft`。读取后目标哈希发生变化时进入 `blocked`。

无关文件存在修改不阻止规划；Skill 保留它们且不扩大修改范围。

## 9. 输出与完成标准

### 9.1 标准结果

每次运行返回：

```text
Mode: draft | advance | blocked
Plan: proposed | created | updated | unchanged
Revision: <old> -> <new>
Context: <seed EV IDs or empty>
Evolution: proposed <EV-NEXT> | created <EV IDs> | none
Decision: <四道门结论或阻塞原因>
Validation: passed | failed
Files: <实际读取或修改的规范文件>
Omitted: <因预算省略的 Node IDs or none>
```

`Files` 区分只读文件和修改文件。`blocked` 必须给出解除阻塞所需的最小动作。

### 9.2 draft 完成标准

以下条件全部成立才完成：

- 项目根目录和规范文件位置已经唯一确定。
- Graph 已校验。
- 相关子图满足预算和稳定顺序。
- Plan 提案包含完整 frontmatter 和四个规范 section。
- Evolution 判定完成；候选 Node 使用 `EV-NEXT`。
- 工作树没有被修改。

### 9.3 advance 完成标准

以下条件全部成立才完成：

- `PLAN.md` 符合模板并反映当前需求、Code 事实和选定方案。
- 有效变化使 revision 恰好增加 `1`。
- `PLAN.md.context` 只引用存在的种子 Node。
- 四道门通过时已经创建粒度正确的 Node；未通过时没有创建 Node。
- Graph 写入后校验通过。
- 本次只修改 `PLAN.md` 和必要的 `evolution/*.md`。
- 标准结果与实际文件状态一致。
