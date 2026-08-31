# Self-use Skills 仓库规则

本仓库保存两个可独立安装的 Skill：`code-map`（导航）与 `evolve-plan`（演进）。职责分离，但通过调用协作：evolve-plan 改变目标项目结构后调用 code-map 同步地图。

## 权威来源

- 当前文件内容：实际状态。
- `CODEMAP.md`：文件职责导航。
- `CONTEXT.md`：稳定术语。
- `docs/research/`：调研依据，不自动等于当前决定。
- `evolve-plan/references/runtime-contract.md`：evolve-plan 运行契约。
- `code-map/references/`：code-map 输出文档的结构模板。

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
4. `evolve-plan` 与 `code-map` 的连接关系：
   - `evolve-plan` 的 advance 写入 `PLAN.md` 或 `evolution/*.md` 后，调用 `code-map` skill 更新目标项目的地图。
   - `code-map` 将 `PLAN.md` 与 `evolution/*.md` 视为 evolve-plan 产物，纳入导航登记与 freshness check 范围。
   - 修改任一 Skill 的协作行为时，同时核对另一个 Skill 是否受影响。
5. 保持最小改动，不修改当前任务无关的文件。

## 验证

- Skill 修改后，使用当前环境 `skill-creator` 附带的 `scripts/quick_validate.py` 验证对应 Skill 目录。
- evolve-plan 修改后，运行 `python3 -m unittest discover -s evolve-plan/tests -p 'test_*.py'`。
