# BugPortal: ExplainedRealBugs 缺陷查询与管理系统

本项目为 `ExplainedRealBugs` 数据集提供一个轻量级 Web 查询与管理界面，基于 FastAPI + SQLite + Jinja2 构建。

- 支持按项目、bug id、issue id、类别、关键字等条件查询
- 展示每个缺陷的基本信息、仓库链接、文本内容（标题/描述/讨论）
- 支持手工标注缺陷类型、状态、备注和标签
- UI 支持中英文切换（右上角按钮）

## 1. 目录结构

在 `ExplainedRealBugs/` 下新增目录：

```text
ExplainedRealBugs/
  bugportal/
    requirements.txt
    README.md
    app/
      __init__.py
      db.py
      models.py
      repositories.py
      main.py
      templates/
        base.html
        search.html
        detail.html
      static/
```

## 2. 安装依赖

建议在 `bugportal` 目录下创建虚拟环境并安装依赖：

```bash
cd ExplainedRealBugs/bugportal
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. 初始化数据库

第一次运行前，需要初始化 SQLite 数据库并从现有数据导入索引：

```bash
cd ExplainedRealBugs/bugportal
source .venv/bin/activate
python -m app.db
```

这会在 `ExplainedRealBugs/bugportal/` 下创建 `explainedrealbugs_meta.db` 数据库文件，并建表（`bug_index`、`bug_meta`）。

随后在启动 FastAPI 时，会自动检查 `bug_index` 是否为空，若为空则从：

- `../bug-mining/*/active-bugs.csv`
- `../bug-classification/parsed_data.jsonl`
- `../bug-classification/classified_data_llm.jsonl`

导入数据。

## 4. 启动服务

```bash
cd ExplainedRealBugs/bugportal
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

启动后，在浏览器中访问：

- 中文界面（默认）：<http://127.0.0.1:8000/bugs?lang=zh>
- 英文界面：<http://127.0.0.1:8000/bugs?lang=en>

右上角有语言切换按钮（`中` / `EN`），点击即可在中英文之间切换，语言偏好会保存在浏览器 cookie 中。

## 5. 使用说明

### 5.1 缺陷查询

访问 `/bugs` 页面，可以看到查询表单：

- 项目（Project）：从已有项目列表中选择或选择“全部”
- Bug ID：项目内的缺陷编号（如 `1`、`2`）
- Issue ID：原 issue 编号（如 `AMQ-449`），支持模糊匹配
- 类别（Label）：使用 LLM 分类和手工标注的类别
- 关键字（Keyword）：在标题 / 描述 / 讨论文本中搜索

点击“搜索”后，下方表格会展示符合条件的缺陷列表。

### 5.2 查看缺陷详情

在查询结果中点击“详情”按钮，会进入 `/bugs/{project_id}/{bug_id}` 页面，展示：

- 基本信息：项目、Bug ID、Issue ID/URL、LLM Label、Manual Label、Status
- 仓库信息：修复前/后的 commit hash 及其仓库链接、compare diff 链接
- 文本内容：Title、Description、Discussion
- Patch 路径：对应的补丁文件在 `bug-mining/<project_id>/patches/<bug_id>.src.patch`

### 5.3 管理信息（标注 / 备注）

在详情页右侧的“管理信息”区域可以：

- 手工填写 `Manual Label`（例如：`Logic/Workflow`）
- 设置 `Status`（例如：`unreviewed`、`reviewed`、`selected_for_paper`）
- 添加备注（Notes）
- 添加标签（Tags，逗号分隔，将以 JSON 数组形式存储）

表单提交后，这些信息会写入 SQLite 数据库的 `bug_meta` 表，而不会修改原始的 CSV/JSONL 文件。

## 6. 注意事项

- 本系统默认从 `ExplainedRealBugs/bug-mining` 和 `ExplainedRealBugs/bug-classification` 目录读取数据，请保证这些数据已通过原框架运行生成。
- 如果后续重新挖掘并更新了 CSV/JSONL，可以：
  - 直接删除 `explainedrealbugs_meta.db` 重新初始化（会丢失手工标注），或
  - 手动扩展导入逻辑为“增量导入”。

如需扩展更多高级功能（例如补丁内容在线预览、报告原文解析展示、多维统计图表等），可以在现有 FastAPI 结构上继续迭代实现。
