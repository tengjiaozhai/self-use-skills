# Self-use Skills

本仓库保存可独立安装和演进的 Agent Skills。代码地图能力与设计演进能力职责分离，但通过调用协作：evolve-plan 写入 PLAN 后调用 code-map 同步地图。

## Language

**Code Map Skill**:
独立维护多语言 Git 仓库导航文档的 Skill；使用 `SKILL.md` 定义行为，并用按需 reference 展示 `AGENTS.md` 与 `CODEMAP.md` 的结构，不承担符号解析、依赖分析或设计历史。
_Avoid_: Graph Plan extension, architecture generator

**Code Map**:
目标仓库根目录的单一 `CODEMAP.md`，以一句话说明值得导航的受版本控制文本文件负责什么；代码是当前行为的最终事实。
_Avoid_: Symbol index, directory tree mirror, architecture source of truth

**Semantic Map**:
由人维护的任务路由、模块责任、canonical entry point 和依赖边界，例如 `AGENTS.md`、`ARCHITECTURE.md` 与模块 README。
_Avoid_: Generated map, symbol index

**Freshness Check**:
比较 Git 变更与 Code Map 条目，识别新增、删除、移动或职责已变化的文件；普通函数内部修改不要求地图变化。
_Avoid_: Background watcher, source hash index
