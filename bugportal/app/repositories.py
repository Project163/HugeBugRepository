import csv
import json
from pathlib import Path
from typing import List, Optional, Tuple

from .db import BUG_MINING_DIR, BUG_CLASSIFICATION_DIR, db_session


def _parse_llm_input_text(llm_text: str) -> Tuple[str, str, str]:
    """Split llm_input_text into title / description / discussion."""
    if not llm_text:
        return "", "", ""

    title = ""
    description = ""
    discussion = ""

    parts = llm_text.split("\n\n")

    for part in parts:
        if part.startswith("Title:"):
            title = part[len("Title:"):].strip()
        elif part.startswith("Description:"):
            description = part[len("Description:"):].strip()
        elif part.startswith("Discussion:"):
            discussion = part[len("Discussion:"):].strip()

    return title, description, discussion


def import_data_if_empty() -> None:
    """Import CSV/JSONL data into bug_index if table is empty."""
    from .db import get_connection

    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(1) FROM bug_index")
        (count,) = cur.fetchone()
        if count > 0:
            return

    # 1. 先导入 active-bugs.csv 基本信息
    rows = []
    for project_dir in sorted(p for p in BUG_MINING_DIR.iterdir() if p.is_dir()):
        csv_path = project_dir / "active-bugs.csv"
        if not csv_path.exists():
            continue
        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

    # 2. 建立 (project_id, bug_id) -> llm_input_text + label 映射
    llm_text_map = {}
    parsed_path = BUG_CLASSIFICATION_DIR / "parsed_data.jsonl"
    if parsed_path.exists():
        with parsed_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (obj.get("project_id"), str(obj.get("bug_id")))
                llm_text_map[key] = obj.get("llm_input_text") or ""

    llm_label_map = {}
    classified_path = BUG_CLASSIFICATION_DIR / "classified_data_llm.jsonl"
    if classified_path.exists():
        with classified_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (obj.get("project_id"), str(obj.get("bug_id")))
                llm_label_map[key] = obj.get("label")

    with db_session() as conn:
        cur = conn.cursor()
        for r in rows:
            project_id = r.get("project_id")
            bug_id = str(r.get("bug.id"))
            key = (project_id, bug_id)

            llm_full_text = llm_text_map.get(key, "")
            title, description, discussion = _parse_llm_input_text(llm_full_text)
            llm_label = llm_label_map.get(key)

            cur.execute(
                """
                INSERT OR IGNORE INTO bug_index (
                    project_id, bug_id, issue_id, issue_url,
                    revision_buggy, revision_fixed,
                    buggy_commit_url, fixed_commit_url, compare_url,
                    source_type, title, description, discussion,
                    llm_label, llm_full_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    bug_id,
                    r.get("report.id"),
                    r.get("report.url"),
                    r.get("revision.id.buggy"),
                    r.get("revision.id.fixed"),
                    r.get("buggy_commit_url"),
                    r.get("fixed_commit_url"),
                    r.get("compare_url"),
                    None,
                    title,
                    description,
                    discussion,
                    llm_label,
                    llm_full_text,
                ),
            )


def query_bugs(
    project_id: Optional[str] = None,
    bug_id: Optional[str] = None,
    issue_id: Optional[str] = None,
    label: Optional[str] = None,
    keyword: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
):
    sql = [
        "SELECT bi.*, bm.manual_label, bm.status, bm.notes, bm.tags FROM bug_index bi",
        "LEFT JOIN bug_meta bm ON bi.project_id = bm.project_id AND bi.bug_id = bm.bug_id",
        "WHERE 1=1",
    ]
    params: List[object] = []

    if project_id:
        sql.append("AND bi.project_id = ?")
        params.append(project_id)
    if bug_id:
        sql.append("AND bi.bug_id = ?")
        params.append(str(bug_id))
    if issue_id:
        sql.append("AND bi.issue_id LIKE ?")
        params.append(f"%{issue_id}%")
    if label:
        # 优先按 manual_label，其次 llm_label
        sql.append("AND (bm.manual_label = ? OR (bm.manual_label IS NULL AND bi.llm_label = ?))")
        params.extend([label, label])
    if keyword:
        like = f"%{keyword}%"
        sql.append("AND (bi.title LIKE ? OR bi.description LIKE ? OR bi.discussion LIKE ?)")
        params.extend([like, like, like])

    sql.append("ORDER BY bi.project_id, CAST(bi.bug_id AS INTEGER) LIMIT ? OFFSET ?")
    params.extend([limit, offset])

    final_sql = "\n".join(sql)

    with db_session() as conn:
        cur = conn.cursor()
        cur.execute(final_sql, params)
        rows = cur.fetchall()

    return rows


def get_bug(project_id: str, bug_id: str):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT bi.*, bm.manual_label, bm.status, bm.notes, bm.tags
            FROM bug_index bi
            LEFT JOIN bug_meta bm ON bi.project_id = bm.project_id AND bi.bug_id = bm.bug_id
            WHERE bi.project_id = ? AND bi.bug_id = ?
            """,
            (project_id, str(bug_id)),
        )
        row = cur.fetchone()
    return row


def upsert_bug_meta(project_id: str, bug_id: str, manual_label: Optional[str], status: Optional[str], notes: Optional[str], tags_json: Optional[str]):
    from datetime import datetime

    now = datetime.utcnow().isoformat(timespec="seconds")

    with db_session() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO bug_meta (project_id, bug_id, manual_label, status, notes, tags, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, bug_id) DO UPDATE SET
                manual_label = excluded.manual_label,
                status = excluded.status,
                notes = excluded.notes,
                tags = excluded.tags,
                updated_at = excluded.updated_at
            """,
            (project_id, str(bug_id), manual_label, status, notes, tags_json, now),
        )


def list_projects() -> List[str]:
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT project_id FROM bug_index ORDER BY project_id")
        return [r[0] for r in cur.fetchall()]


def list_labels() -> List[str]:
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT llm_label FROM bug_index WHERE llm_label IS NOT NULL ORDER BY llm_label")
        labels = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT manual_label FROM bug_meta WHERE manual_label IS NOT NULL ORDER BY manual_label")
        labels_meta = [r[0] for r in cur.fetchall()]
    return sorted(set(labels) | set(labels_meta))
