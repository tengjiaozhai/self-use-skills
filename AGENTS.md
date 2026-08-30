# Agent 导航

## 权威来源

- 当前文件内容：实际状态。
- `CODEMAP.md`：文件职责导航。
- `CONTEXT.md`：稳定术语。
- `docs/research/`：调研依据，不自动等于当前决定。
- `evolve-plan/references/runtime-contract.md`：evolve-plan 运行契约。

## 任务路由

| 当前任务 | 先读 |
| --- | --- |
| 查找某项能力在哪个文件 | `CODEMAP.md` |
| 创建、检查或更新代码地图 | `code-map/SKILL.md` |
| 修改 Living Plan 工作流 | `evolve-plan/SKILL.md` |
| 修改 Evolution Graph 行为 | `evolve-plan/references/runtime-contract.md` |
| 调查 Evolution Graph 实现 | `evolve-plan/scripts/evolution_graph.py` |
| 了解代码地图设计背景 | `docs/research/research001.md` |

## 工作规则

1. 根据任务路由读取文件，不为了解整个仓库而加载全部文档。
2. `CODEMAP.md` 只负责导航；与文件内容冲突时，以实际文件为准。
3. 文件新增、删除、移动或核心职责变化时，同步检查 `CODEMAP.md`。
4. `code-map` 与 `evolve-plan` 相互独立。
5. 保持最小改动，不修改当前任务无关的文件。

## 验证

- Skill 修改后，使用当前环境 `skill-creator` 附带的 `scripts/quick_validate.py` 验证对应 Skill 目录。
- evolve-plan 修改后，运行 `python3 -m unittest discover -s evolve-plan/tests -p 'test_*.py'`。
