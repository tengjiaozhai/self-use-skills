# CODEMAP.md 示例

> 用于构建目标仓库根 `CODEMAP.md` 的结构示例。以下条目展示格式，必须替换为目标仓库的实际文件职责。

本文件只说明文件职责，帮助定位下一份应该读取的内容。实际文件内容是当前行为的最终事实。两个 Skill 的连接关系见目标仓库根 AGENTS.md 工作规则 4。

模板中的链接使用 `../../` 指向本仓库内对应文件（基准是本模板所在目录 `code-map/references/`），方便在 GitHub 上直接跳转。bootstrap 复制到目标仓库根时，改为相对目标仓库根的链接（去掉 `../..` 前缀）。

## 根目录

- [AGENTS.md](../../AGENTS.md) — 根据任务类型路由到相关 Skill、契约、实现或调研文件。
- [CONTEXT.md](../../CONTEXT.md) — 定义 Code Map、Code Map Skill 和 Freshness Check 等稳定术语。
- [LICENSE](../../LICENSE) — 声明仓库采用 MIT License。

## code-map

- [code-map/SKILL.md](../../code-map/SKILL.md) — 定义 `CODEMAP.md` 的查询、检查和更新方式，并登记 evolve-plan 产物。

## evolve-plan

- [evolve-plan/SKILL.md](../../evolve-plan/SKILL.md) — evolve-plan 的 Skill 入口，定义检查、演进和写入流程，并在 advance 后调用 code-map 同步地图。
- [evolve-plan/references/runtime-contract.md](../../evolve-plan/references/runtime-contract.md) — 定义 PLAN、Evolution Graph、运行模式和写入边界的权威契约。
- [evolve-plan/scripts/evolution_graph.py](../../evolve-plan/scripts/evolution_graph.py) — 实现 Evolution Graph 校验、检索和原子写入。
- [evolve-plan/assets/PLAN.template.md](../../evolve-plan/assets/PLAN.template.md) — 提供 Living PLAN 的标准模板。
- [evolve-plan/assets/evolution-node.template.md](../../evolve-plan/assets/evolution-node.template.md) — 提供 Evolution Node 的标准模板。
- [evolve-plan/agents/openai.yaml](../../evolve-plan/agents/openai.yaml) — 定义 evolve-plan 的界面元数据。
- [evolve-plan/tests/test_evolution_graph.py](../../evolve-plan/tests/test_evolution_graph.py) — 验证 Evolution Graph CLI 的主要行为。

## docs/research

- [docs/research/research001.md](../../docs/research/research001.md) — 保存 Repository Map、渐进式披露和 graph-plan 优化方向的调研报告。
