# Self-use Skills

个人 Agent Skills 仓库，保存可独立安装、可独立演进的 Agent Skill。目前包含两个：`code-map`（仓库导航）与 `evolve-plan`（计划演进）。两者职责分离，但通过调用协作。

## 仓库内容

| Skill | 职责 | 何时使用 |
| --- | --- | --- |
| [code-map](code-map/SKILL.md) | 维护目标仓库根目录的 `CODEMAP.md`，以一句话说明每个值得导航的文件负责什么 | 创建/检查/更新代码地图；需要快速定位文件职责 |
| [evolve-plan](evolve-plan/SKILL.md) | 推进唯一的 Living `PLAN.md`，并用稀疏的 Evolution Graph 保存长期设计理由 | 仓库已有 `PLAN.md` 或 `evolution/`，需要规划或推进下一 revision |

## code-map

维护一个只负责导航的 `CODEMAP.md`：代码是当前行为的最终事实，地图只回答"每个文件负责什么"。包含四种模式：

- **Bootstrap**：在目标仓库根创建 `AGENTS.md` 与 `CODEMAP.md`（模板见 [references/](code-map/references/)）
- **Query**：用已有地图路由任务到具体文件，只读不改
- **Check**：对照 Git 变更评估地图新鲜度，识别新增、删除、移动或职责变化的文件
- **Update**：文件结构变化时更新地图，保持最小改动

## evolve-plan

`PLAN.md` 回答"下一步做什么"，`evolution/*.md`（Evolution Graph）回答"为什么变成现在这样"。完整契约见 [references/runtime-contract.md](evolve-plan/references/runtime-contract.md)，包括：

- **draft / advance 两个分支**：draft 零写入只产出提案；advance 原子写入 `PLAN.md` 和必要的 `evolution/*.md`
- **四道门**：Decided / Material / Grounded / Durable，决定是否创建 Evolution Node
- **校验与测试**：`scripts/evolution_graph.py` 实现 Graph 校验、检索和原子写入，附 10 个单元测试

## 连接关系

```text
evolve-plan advance 写入 PLAN.md / evolution/*.md
        │
        ▼（若目标项目存在 CODEMAP.md）
code-map 同步地图，登记新写入的文件
```

- `evolve-plan` 的 advance 写入通过校验后，调用 `code-map` 更新目标项目地图
- `code-map` 将 `PLAN.md` 与 `evolution/*.md` 视为 evolve-plan 产物，纳入导航登记与 freshness check 范围

连接规则在根 [AGENTS.md](AGENTS.md) 工作规则 4，术语定义在 [CONTEXT.md](CONTEXT.md)。

## 安装

```bash
git clone https://github.com/tengjiaozhai/self-use-skills.git
# 将 skill 目录放入你的 skills 目录，例如 Claude Code / Codex：
ln -s "$PWD/self-use-skills/code-map" ~/.agents/skills/code-map
ln -s "$PWD/self-use-skills/evolve-plan" ~/.agents/skills/evolve-plan
```

## 仓库结构

```text
.
├── AGENTS.md                    # 任务路由 + 两 Skill 连接规则
├── CODEMAP.md                   # 本仓库文件导航
├── CONTEXT.md                   # 稳定术语
├── code-map/                    # code-map skill
│   ├── SKILL.md
│   └── references/              # AGENTS.md / CODEMAP.md 结构模板
├── evolve-plan/                 # evolve-plan skill
│   ├── SKILL.md
│   ├── references/runtime-contract.md
│   ├── scripts/evolution_graph.py
│   ├── assets/                  # PLAN / Evolution Node 模板
│   ├── agents/openai.yaml
│   └── tests/
└── docs/research/               # 调研报告
```

## 开发与验证

```bash
# 校验 Skill 目录结构（skill-creator）
python3 <skill-creator>/scripts/quick_validate.py code-map
python3 <skill-creator>/scripts/quick_validate.py evolve-plan

# evolve-plan 单元测试
cd evolve-plan && python3 -m unittest discover -s tests -p 'test_*.py'
```

## License

[MIT](LICENSE)
