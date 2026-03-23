import shutil
import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from app.db import init_db, db_session
from app.repositories import list_projects, query_bugs, get_bug
from app.models import Bug

# 配置输出目录
OUTPUT_DIR = Path("site")
TEMPLATES_DIR = Path("app/templates")
STATIC_DIR = Path("app/static")

# 初始化 Jinja2 环境
env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

def ensure_dir(path: Path):
    if not path.exists():
        path.mkdir(parents=True)

def generate_static():
    # 1. 准备输出目录
    print(f"Cleaning output directory: {OUTPUT_DIR}")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    ensure_dir(OUTPUT_DIR)

    # 复制静态资源
    print("Copying static files...")
    ensure_dir(OUTPUT_DIR / "static")
    if STATIC_DIR.exists():
        for item in STATIC_DIR.iterdir():
            if item.is_file():
                shutil.copy(item, OUTPUT_DIR / "static" / item.name)

    # 2. 生成首页 (index.html) - 展示项目列表
    print("Generating index.html...")
    projects = list_projects()
    template = env.get_template("static_index.html") # 我们需要创建一个新的静态首页模板
    html = template.render(projects=projects, lang="zh")
    with open(OUTPUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(html)

    # 3. 生成每个项目的列表页和详情页
    for project_id in projects:
        print(f"Processing project: {project_id}")
        project_dir = OUTPUT_DIR / "bugs" / project_id
        ensure_dir(project_dir)

        # 获取该项目所有 bugs (为了简化，这里不分页，或者简单列出)
        # 注意：query_bugs 默认 limit=50，这里我们需要获取全部
        # 我们可以临时修改 query_bugs limit 或者写一个新的 helper，这里为了演示，只取前 500 个
        rows = query_bugs(project_id=project_id, limit=10000) 
        
        # 生成项目索引页
        project_template = env.get_template("static_project_index.html")
        project_html = project_template.render(project_id=project_id, rows=rows, lang="zh")
        with open(project_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(project_html)

        # 生成该项目下每个 bug 的详情页
        detail_template = env.get_template("detail.html")
        for row in rows:
            bug_id = str(row["bug_id"])
            # 获取完整详情（包括 tags 等）
            bug_detail = get_bug(project_id, bug_id)
            if not bug_detail:
                continue

            # detail.html 原本依赖 request 对象和 form 提交，静态化后需要把这些去掉或隐藏
            # 为了复用，我们传入一个伪造的 context
            # 注意：静态页面不能有 "Edit Meta" 的表单功能
            
            tags = []
            if bug_detail["tags"]:
                try:
                    tags = json.loads(bug_detail["tags"])
                except:
                    pass

            html_content = detail_template.render(
                request=None, 
                bug=bug_detail, 
                project_id=project_id, 
                bug_id=bug_id, 
                lang="zh",
                static_mode=True, # 这是一个开关，用来在模板里隐藏动态功能
                tags=tags
            )
            
            bug_file = project_dir / f"{bug_id}.html"
            with open(bug_file, "w", encoding="utf-8") as f:
                f.write(html_content)

    print("Static site generation complete!")

if __name__ == "__main__":
    from app.db import init_db
    init_db() # 确保 DB 初始化
    generate_static()
