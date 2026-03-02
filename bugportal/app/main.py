from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

from .db import init_db
from .repositories import import_data_if_empty, query_bugs, get_bug, upsert_bug_meta, list_projects, list_labels
from .models import BugMetaUpdate

BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"

app = FastAPI(title="ExplainedRealBugs Portal")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
async def startup_event():
    init_db()
    import_data_if_empty()


# 简单的语言切换：通过查询参数 lang=zh/en，并在 cookie 中保存

def get_lang(request: Request) -> str:
    lang = request.query_params.get("lang")
    if lang in ("zh", "en"):
        return lang
    cookie_lang = request.cookies.get("lang")
    if cookie_lang in ("zh", "en"):
        return cookie_lang
    return "zh"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    lang = get_lang(request)
    url = request.url_for("search_bugs") + f"?lang={lang}"
    return RedirectResponse(url)


@app.get("/bugs", response_class=HTMLResponse, name="search_bugs")
async def search_bugs_page(
    request: Request,
    project_id: str | None = None,
    bug_id: str | None = None,
    issue_id: str | None = None,
    label: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    lang = get_lang(request)
    page = max(page, 1)
    # 默认每页 500 条，允许用户调节，但单次查询上限为 15000
    default_page_size = 500
    # 若用户未显式提供 page_size，则使用默认值
    if "page_size" not in request.query_params:
        page_size = default_page_size
    page_size = min(max(page_size, 1), 15000)

    # 没有任何筛选条件时，不加载记录，保持页面干净
    has_filter = any([
        project_id,
        bug_id,
        issue_id,
        label,
        q,
    ])

    if has_filter:
        offset = (page - 1) * page_size
        rows = query_bugs(
            project_id=project_id or None,
            bug_id=bug_id or None,
            issue_id=issue_id or None,
            label=label or None,
            keyword=q or None,
            offset=offset,
            limit=page_size,
        )
    else:
        rows = []

    projects = list_projects()
    labels = list_labels()

    response = templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "lang": lang,
            "rows": rows,
            "projects": projects,
            "labels": labels,
            "current": {
                "project_id": project_id or "",
                "bug_id": bug_id or "",
                "issue_id": issue_id or "",
                "label": label or "",
                "q": q or "",
                "page": page,
                "page_size": page_size,
            },
        },
    )

    # 设置语言 cookie
    response.set_cookie("lang", lang, max_age=3600 * 24 * 365)
    return response


@app.get("/bugs/{project_id}/{bug_id}", response_class=HTMLResponse)
async def bug_detail(request: Request, project_id: str, bug_id: str):
    lang = get_lang(request)
    row = get_bug(project_id, bug_id)
    if not row:
        return HTMLResponse(content="Bug not found", status_code=404)

    tags_list = []
    if row["tags"]:
        try:
            tags_list = json.loads(row["tags"])
        except Exception:
            tags_list = []

    response = templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "lang": lang,
            "bug": row,
            "tags": tags_list,
        },
    )
    response.set_cookie("lang", lang, max_age=3600 * 24 * 365)
    return response


@app.post("/bugs/{project_id}/{bug_id}/meta", response_class=HTMLResponse)
async def update_bug_meta(
    request: Request,
    project_id: str,
    bug_id: str,
    manual_label: str | None = Form(default=None),
    status: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    tags: str | None = Form(default=None),
):
    lang = get_lang(request)
    tags_json = None
    if tags:
        # 以逗号分隔输入，存储为 JSON 数组
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        tags_json = json.dumps(tag_list, ensure_ascii=False)

    upsert_bug_meta(project_id, bug_id, manual_label or None, status or None, notes or None, tags_json)

    url = request.url_for("bug_detail", project_id=project_id, bug_id=bug_id)
    url = str(url) + f"?lang={lang}"
    return RedirectResponse(url=url, status_code=303)


@app.get("/api/labels", response_class=JSONResponse)
async def api_labels():
    labels = list_labels()
    return {"labels": labels}
