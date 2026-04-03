# coding=utf-8

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import fnmatch
import os
import re

from flask import Blueprint, current_app, jsonify, request, send_file

SqlKit_bp = Blueprint("sql_kit_bp", __name__)


def build_log(logs: list[dict], level: str, message: str) -> None:
    logs.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        }
    )


def get_sql_kit_root() -> Path:
    configured_root = current_app.config.get("SQL_KIT_ROOT")
    if configured_root:
        return Path(configured_root)

    # 默认将 SQL Kit 数据保存到后端目录内，方便容器部署时挂载持久化卷。
    return Path(current_app.root_path).parent / "sql_kit_data"


def ensure_sql_kit_structure() -> None:
    root = get_sql_kit_root()
    for relative_path in [
        Path("temp/sql"),
        Path("log/sql"),
    ]:
        (root / relative_path).mkdir(parents=True, exist_ok=True)


TOOL_DEFINITIONS = {
    "union_all": {
        "id": "union_all",
        "name": "SQL 分表 UNION ALL",
        "description": "从模板中选择一条 SQL，按分表数量生成完整的 UNION ALL 查询语句。",
        "template_path": Path("temp/sql/select_temp.sql"),
        "result_dir": Path("log/sql"),
        "result_pattern": "union_query_*.txt",
        "result_label": "生成结果",
        "params": [
            {
                "key": "sql_index",
                "label": "SQL 序号",
                "type": "number",
                "required": True,
                "min": 1,
                "placeholder": "例如 1",
                "help": "模板中按行拆分后的 SQL 序号，从 1 开始。",
            },
            {
                "key": "table_count",
                "label": "分表数量",
                "type": "number",
                "required": True,
                "min": 1,
                "placeholder": "例如 200",
                "help": "会按原始表名拼接 _1、_2 ... 生成查询。",
            },
        ],
    },
    "batch_insert": {
        "id": "batch_insert",
        "name": "批量 INSERT 生成",
        "description": "基于一条 INSERT 模板，批量生成可直接执行的 SQL 文件。",
        "template_path": Path("temp/sql/insert_temp.sql"),
        "result_dir": Path("log/sql"),
        "result_pattern": "batch_insert_*.sql",
        "result_label": "生成结果",
        "params": [
            {
                "key": "record_count",
                "label": "记录总数",
                "type": "number",
                "required": True,
                "min": 1,
                "placeholder": "例如 1000",
                "help": "总共要生成多少条记录。",
            },
            {
                "key": "batch_size",
                "label": "每批条数",
                "type": "number",
                "required": True,
                "min": 1,
                "placeholder": "例如 500",
                "help": "每个 INSERT 语句中包含多少条记录。",
            },
            {
                "key": "auto_increment_col",
                "label": "自增字段名",
                "type": "text",
                "required": True,
                "placeholder": "例如 id",
                "help": "需要递增生成的字段名，必须出现在模板列中。",
            },
            {
                "key": "start_value",
                "label": "起始值",
                "type": "number",
                "required": True,
                "placeholder": "例如 0",
                "help": "自增字段的起始值。",
            },
        ],
    },
}


def get_tool_definition(tool_id: str) -> dict:
    definition = TOOL_DEFINITIONS.get(tool_id)
    if not definition:
        raise ValueError("不支持的 SQL 工具")
    return definition


def serialize_tool_definition(tool_id: str) -> dict:
    definition = get_tool_definition(tool_id)
    return {
        "id": definition["id"],
        "name": definition["name"],
        "description": definition["description"],
        "params": definition["params"],
        "result_label": definition["result_label"],
    }


def get_template_file(tool_id: str) -> Path:
    definition = get_tool_definition(tool_id)
    return get_sql_kit_root() / definition["template_path"]


def get_result_directory(tool_id: str) -> Path:
    definition = get_tool_definition(tool_id)
    result_dir = get_sql_kit_root() / definition["result_dir"]
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def serialize_result_file(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "relative_path": path.relative_to(get_sql_kit_root()).as_posix(),
    }


def read_text_preview(path: Path, line_limit: int = 80, char_limit: int = 12000) -> dict:
    raw_content = path.read_text(encoding="utf-8", errors="replace")
    content = raw_content
    truncated = False
    if len(content) > char_limit:
        content = content[:char_limit]
        truncated = True

    lines = content.splitlines()
    if len(lines) > line_limit:
        content = "\n".join(lines[:line_limit])
        truncated = True

    return {
        "content": content,
        "truncated": truncated,
        "line_count": len(raw_content.splitlines()),
    }


def list_result_files(tool_id: str) -> list[dict]:
    definition = get_tool_definition(tool_id)
    result_dir = get_result_directory(tool_id)
    pattern = definition["result_pattern"]

    matched_files = [
        serialize_result_file(path)
        for path in sorted(result_dir.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True)
        if path.is_file() and fnmatch.fnmatch(path.name, pattern)
    ]
    return matched_files


def cleanup_result_files(tool_id: str) -> int:
    definition = get_tool_definition(tool_id)
    result_dir = get_result_directory(tool_id)
    pattern = definition["result_pattern"]
    removed_count = 0

    for path in result_dir.iterdir():
        if path.is_file() and fnmatch.fnmatch(path.name, pattern):
            path.unlink()
            removed_count += 1

    return removed_count


def parse_sql_lines(template_content: str) -> list[str]:
    sql_lines = [line.strip() for line in template_content.splitlines() if line.strip()]
    if not sql_lines:
        raise ValueError("模板内容为空，请先填写 SQL 模板")
    return sql_lines


def extract_table_name(sql_template: str) -> str:
    pattern = r"FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\w+)?\s*(?:WHERE|\n|$)"
    match = re.search(pattern, sql_template, re.IGNORECASE)
    if match:
        return match.group(1)

    fallback_pattern = r"FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    fallback_match = re.search(fallback_pattern, sql_template, re.IGNORECASE)
    if fallback_match:
        return fallback_match.group(1)

    raise ValueError("无法从模板 SQL 中提取表名")


def generate_union_all_sql(sql_template: str, original_table: str, table_count: int, logs: list[dict]) -> str:
    base_table_name = re.sub(r"_\d+$", "", original_table)
    sql_lines: list[str] = []

    select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql_template, re.IGNORECASE | re.DOTALL)
    select_clause = select_match.group(1).strip() if select_match else "*"
    build_log(logs, "info", f"已识别 SELECT 子句：{select_clause}")

    table_alias_match = re.search(r"FROM\s+\w+\s+(\w+)\s*(?:WHERE|$)", sql_template, re.IGNORECASE)
    table_alias = table_alias_match.group(1) if table_alias_match else "t"
    build_log(logs, "info", f"已识别表别名：{table_alias}")

    where_match = re.search(r"WHERE\s+(.+)$", sql_template, re.IGNORECASE | re.DOTALL)
    where_clause = where_match.group(1).strip() if where_match else ""
    if where_clause:
        build_log(logs, "info", f"已识别 WHERE 条件：{where_clause}")

    for index in range(1, table_count + 1):
        new_table = f"{base_table_name}_{index}"
        sql = f"SELECT '{new_table}' AS source_table, {select_clause} FROM {new_table} {table_alias}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        if index < table_count:
            sql += " UNION ALL"
        else:
            sql += ";"
        sql_lines.append(sql)

    build_log(logs, "success", f"已生成 {table_count} 段 UNION ALL 查询")
    return "\n".join(sql_lines)


def smart_parse_values(values_str: str) -> list[str]:
    values: list[str] = []
    current: list[str] = []
    in_string = False
    quote_char = None
    escape_next = False

    for char in values_str:
        if escape_next:
            current.append(char)
            escape_next = False
            continue
        if char == "\\":
            current.append(char)
            escape_next = True
            continue
        if char in {"'", '"'}:
            if not in_string:
                in_string = True
                quote_char = char
            elif quote_char == char:
                in_string = False
            current.append(char)
            continue
        if char == "," and not in_string:
            values.append("".join(current).strip())
            current = []
            continue
        current.append(char)

    if current:
        values.append("".join(current).strip())

    return values


def parse_insert_statement(sql_template: str) -> dict:
    sql_clean = re.sub(r"\s+", " ", sql_template.strip())
    pattern = r"INSERT\s+INTO\s+([\w.]+)\s*\(([^)]+)\)\s*VALUES\s*\((.+)\);?"
    match = re.search(pattern, sql_clean, re.IGNORECASE)
    if not match:
        raise ValueError("无法解析 INSERT 模板，请确认格式为 INSERT INTO ... VALUES (...) ;")

    table_name = match.group(1).strip()
    columns = [column.strip() for column in match.group(2).split(",") if column.strip()]
    values = smart_parse_values(match.group(3))

    if len(columns) != len(values):
        raise ValueError(f"INSERT 模板列数与值数量不匹配：列 {len(columns)} 个，值 {len(values)} 个")

    return {
        "table_name": table_name,
        "columns": columns,
        "original_values": values,
    }


def analyze_template(tool_id: str, template_content: str) -> dict:
    analysis = {
        "type": tool_id,
        "valid": bool(template_content.strip()),
        "message": "模板为空",
    }

    if not template_content.strip():
        return analysis

    if tool_id == "union_all":
        sql_lines = parse_sql_lines(template_content)
        analysis.update(
            {
                "type": "union_all",
                "valid": True,
                "message": f"已识别 {len(sql_lines)} 条 SQL 模板",
                "sql_count": len(sql_lines),
            }
        )
        return analysis

    if tool_id == "batch_insert":
        template_info = parse_insert_statement(template_content)
        columns = template_info["columns"]
        default_field = columns[0] if columns else ""
        analysis.update(
            {
                "type": "batch_insert",
                "valid": True,
                "message": f"已识别表 {template_info['table_name']}，共 {len(columns)} 个字段",
                "table_name": template_info["table_name"],
                "columns": columns,
                "auto_increment_candidates": columns,
                "suggested_auto_increment_col": default_field,
            }
        )
        return analysis

    return analysis


def safe_analyze_template(tool_id: str, template_content: str) -> dict:
    try:
        return analyze_template(tool_id, template_content)
    except ValueError as exc:
        return {
            "type": tool_id,
            "valid": False,
            "message": str(exc),
        }


def format_value_based_on_template(template_value: str, new_value: int) -> str:
    template_str = str(template_value)
    if template_str.startswith("'") and template_str.endswith("'"):
        return f"'{new_value}'"
    if template_str.startswith('"') and template_str.endswith('"'):
        return f'"{new_value}"'
    return str(new_value)


def generate_batch_insert_sql(template_info: dict, params: dict, logs: list[dict]) -> list[str]:
    columns = template_info["columns"]
    template_values = template_info["original_values"]
    table_name = template_info["table_name"]

    record_count = params["record_count"]
    batch_size = params["batch_size"]
    auto_increment_col = params["auto_increment_col"]
    start_value = params["start_value"]

    if auto_increment_col not in columns:
        raise ValueError(f"模板中不存在字段：{auto_increment_col}")
    if batch_size > 5000:
        raise ValueError("每批条数建议不超过 5000")

    col_index = columns.index(auto_increment_col)
    batch_count = (record_count + batch_size - 1) // batch_size

    build_log(logs, "info", f"已识别表名：{table_name}")
    build_log(logs, "info", f"共 {len(columns)} 个字段，自增字段为 {auto_increment_col}")
    build_log(logs, "info", f"总记录数 {record_count}，每批 {batch_size}，共 {batch_count} 个 INSERT 语句")

    statements: list[str] = []
    for batch_num in range(batch_count):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, record_count)
        batch_records = batch_end - batch_start
        rows: list[str] = []

        for row_index in range(batch_records):
            current_id = start_value + batch_start + row_index
            record_values: list[str] = []
            for value_index, template_value in enumerate(template_values):
                if value_index == col_index:
                    record_values.append(format_value_based_on_template(template_value, current_id))
                else:
                    record_values.append(template_value)
            rows.append(f"({', '.join(record_values)})")

        statement = (
            f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES\n    "
            + ",\n    ".join(rows)
            + ";"
        )
        statements.append(statement)
        build_log(logs, "info", f"已生成第 {batch_num + 1}/{batch_count} 个 INSERT 语句")

    build_log(logs, "success", f"批量 INSERT 生成完成，共输出 {record_count} 条记录")
    return statements


def ensure_positive_int(value: object, field_label: str) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception as exc:
        raise ValueError(f"{field_label}必须是整数") from exc
    if parsed <= 0:
        raise ValueError(f"{field_label}必须大于 0")
    return parsed


def ensure_int(value: object, field_label: str) -> int:
    try:
        return int(str(value).strip())
    except Exception as exc:
        raise ValueError(f"{field_label}必须是整数") from exc


def execute_union_all(tool_id: str, template_content: str, params: dict, logs: list[dict]) -> dict:
    sql_lines = parse_sql_lines(template_content)
    sql_index = ensure_positive_int(params.get("sql_index"), "SQL 序号")
    table_count = ensure_positive_int(params.get("table_count"), "分表数量")

    if sql_index > len(sql_lines):
        raise ValueError(f"SQL 序号超出范围，当前模板共有 {len(sql_lines)} 条 SQL")

    selected_sql = sql_lines[sql_index - 1]
    build_log(logs, "info", f"已选择第 {sql_index} 条 SQL：{selected_sql}")

    original_table = extract_table_name(selected_sql)
    build_log(logs, "info", f"提取到原始表名：{original_table}")

    generated_sql = generate_union_all_sql(selected_sql, original_table, table_count, logs)

    removed_count = cleanup_result_files(tool_id)
    if removed_count:
        build_log(logs, "info", f"已清理 {removed_count} 个历史结果文件")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = get_result_directory(tool_id) / f"union_query_{timestamp}.txt"
    output_path.write_text(generated_sql, encoding="utf-8")
    build_log(logs, "success", f"结果文件已生成：{output_path.name}")

    return {
        "output_file": serialize_result_file(output_path),
        "preview": generated_sql.splitlines()[:8],
    }


def execute_batch_insert(tool_id: str, template_content: str, params: dict, logs: list[dict]) -> dict:
    template_info = parse_insert_statement(template_content)
    validated_params = {
        "record_count": ensure_positive_int(params.get("record_count"), "记录总数"),
        "batch_size": ensure_positive_int(params.get("batch_size"), "每批条数"),
        "auto_increment_col": str(params.get("auto_increment_col", "")).strip(),
        "start_value": ensure_int(params.get("start_value"), "起始值"),
    }
    if not validated_params["auto_increment_col"]:
        raise ValueError("自增字段名不能为空")

    statements = generate_batch_insert_sql(template_info, validated_params, logs)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = get_result_directory(tool_id) / f"batch_insert_{timestamp}.sql"
    output_path.write_text("\n\n".join(statements), encoding="utf-8")
    build_log(logs, "success", f"结果文件已生成：{output_path.name}")

    preview_lines = output_path.read_text(encoding="utf-8").splitlines()[:8]
    return {
        "output_file": serialize_result_file(output_path),
        "preview": preview_lines,
    }


EXECUTORS = {
    "union_all": execute_union_all,
    "batch_insert": execute_batch_insert,
}


def read_template_payload(tool_id: str) -> dict:
    template_file = get_template_file(tool_id)
    if not template_file.exists():
        template_file.parent.mkdir(parents=True, exist_ok=True)
        template_file.write_text("", encoding="utf-8")

    content = template_file.read_text(encoding="utf-8")
    template_items = []
    if tool_id == "union_all":
        template_items = [
            {
                "index": index,
                "preview": sql[:120],
            }
            for index, sql in enumerate(parse_sql_lines(content), start=1)
        ] if content.strip() else []

    return {
        "tool": serialize_tool_definition(tool_id),
        "template": {
            "content": content,
            "path": template_file.relative_to(get_sql_kit_root()).as_posix(),
            "updated_at": datetime.fromtimestamp(template_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "items": template_items,
            "analysis": safe_analyze_template(tool_id, content),
        },
        "results": list_result_files(tool_id),
    }


@SqlKit_bp.route("/sql-kit", methods=["GET"])
def sql_kit_index():
    ensure_sql_kit_structure()
    tools = [serialize_tool_definition(tool_id) for tool_id in TOOL_DEFINITIONS]
    return jsonify(
        {
            "status_code": 200,
            "message": "SQL Kit API is available",
            "data": {
                "tools": tools,
                "endpoints": [
                    "/sql-kit/tools",
                    "/sql-kit/template",
                    "/sql-kit/template/analyze",
                    "/sql-kit/run",
                    "/sql-kit/results",
                    "/sql-kit/result-preview",
                    "/sql-kit/download",
                ],
            },
        }
    ), 200


@SqlKit_bp.route("/sql-kit/tools", methods=["GET"])
def get_sql_kit_tools():
    ensure_sql_kit_structure()
    tools = []
    for tool_id, definition in TOOL_DEFINITIONS.items():
        tool_info = serialize_tool_definition(tool_id)
        tool_info["results"] = list_result_files(tool_id)
        tools.append(tool_info)
    return jsonify({"status_code": 200, "data": tools}), 200


@SqlKit_bp.route("/sql-kit/template", methods=["GET"])
def get_sql_kit_template():
    ensure_sql_kit_structure()
    tool_id = request.args.get("tool", "").strip()
    try:
        payload = read_template_payload(tool_id)
    except ValueError as exc:
        return jsonify({"status_code": 12001, "error": str(exc)}), 400
    return jsonify({"status_code": 200, "data": payload}), 200


@SqlKit_bp.route("/sql-kit/template", methods=["POST"])
def save_sql_kit_template():
    ensure_sql_kit_structure()
    payload = request.get_json(silent=True) or {}
    tool_id = str(payload.get("tool", "")).strip()
    content = str(payload.get("content", ""))

    try:
        template_file = get_template_file(tool_id)
    except ValueError as exc:
        return jsonify({"status_code": 12001, "error": str(exc)}), 400

    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(content, encoding="utf-8")

    return jsonify(
        {
            "status_code": 200,
            "message": "模板保存成功",
            "data": {
                "path": template_file.relative_to(get_sql_kit_root()).as_posix(),
                "updated_at": datetime.fromtimestamp(template_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "analysis": safe_analyze_template(tool_id, content),
            },
        }
    ), 200


@SqlKit_bp.route("/sql-kit/template/analyze", methods=["POST"])
def analyze_sql_kit_template():
    ensure_sql_kit_structure()
    payload = request.get_json(silent=True) or {}
    tool_id = str(payload.get("tool", "")).strip()
    content = str(payload.get("content", ""))

    try:
        get_tool_definition(tool_id)
    except ValueError as exc:
        return jsonify({"status_code": 12001, "error": str(exc)}), 400

    return jsonify({"status_code": 200, "data": safe_analyze_template(tool_id, content)}), 200


@SqlKit_bp.route("/sql-kit/run", methods=["POST"])
def run_sql_kit_tool():
    ensure_sql_kit_structure()
    payload = request.get_json(silent=True) or {}
    tool_id = str(payload.get("tool", "")).strip()
    params = payload.get("params", {}) or {}
    template_content = str(payload.get("content", ""))

    try:
        get_tool_definition(tool_id)
        if not template_content.strip():
            template_content = get_template_file(tool_id).read_text(encoding="utf-8")
    except ValueError as exc:
        return jsonify({"status_code": 12001, "error": str(exc)}), 400
    except FileNotFoundError:
        return jsonify({"status_code": 12002, "error": "模板文件不存在，请先保存模板"}), 400

    logs: list[dict] = []
    build_log(logs, "info", f"开始执行工具：{TOOL_DEFINITIONS[tool_id]['name']}")
    try:
        result = EXECUTORS[tool_id](tool_id, template_content, params, logs)
    except ValueError as exc:
        build_log(logs, "error", str(exc))
        return jsonify({"status_code": 12003, "error": str(exc), "data": {"logs": logs}}), 400
    except Exception as exc:
        build_log(logs, "error", f"执行失败：{exc}")
        return jsonify({"status_code": 12004, "error": f"执行失败：{exc}", "data": {"logs": logs}}), 500

    build_log(logs, "success", "工具执行完成")
    return jsonify(
        {
            "status_code": 200,
            "message": "执行成功",
            "data": {
                "logs": logs,
                "result": result,
                "results": list_result_files(tool_id),
            },
        }
    ), 200


@SqlKit_bp.route("/sql-kit/results", methods=["GET"])
def get_sql_kit_results():
    ensure_sql_kit_structure()
    tool_id = request.args.get("tool", "").strip()
    try:
        results = list_result_files(tool_id)
    except ValueError as exc:
        return jsonify({"status_code": 12001, "error": str(exc)}), 400
    return jsonify({"status_code": 200, "data": results}), 200


@SqlKit_bp.route("/sql-kit/download", methods=["GET"])
def download_sql_kit_result():
    ensure_sql_kit_structure()
    raw_path = request.args.get("path", "").strip().replace("\\", "/")
    if not raw_path:
        return jsonify({"status_code": 12005, "error": "缺少文件路径"}), 400

    target_root = get_sql_kit_root().resolve()
    target_file = (target_root / raw_path).resolve()
    try:
        target_file.relative_to(target_root)
    except ValueError:
        return jsonify({"status_code": 12006, "error": "文件路径不合法"}), 400

    if not target_file.exists() or not target_file.is_file():
        return jsonify({"status_code": 12007, "error": "结果文件不存在"}), 404

    return send_file(target_file, as_attachment=True, download_name=target_file.name)


@SqlKit_bp.route("/sql-kit/result-preview", methods=["GET"])
def preview_sql_kit_result():
    ensure_sql_kit_structure()
    raw_path = request.args.get("path", "").strip().replace("\\", "/")
    if not raw_path:
        return jsonify({"status_code": 12005, "error": "缺少文件路径"}), 400

    target_root = get_sql_kit_root().resolve()
    target_file = (target_root / raw_path).resolve()
    try:
        target_file.relative_to(target_root)
    except ValueError:
        return jsonify({"status_code": 12006, "error": "文件路径不合法"}), 400

    if not target_file.exists() or not target_file.is_file():
        return jsonify({"status_code": 12007, "error": "结果文件不存在"}), 404

    preview = read_text_preview(target_file)
    return jsonify(
        {
            "status_code": 200,
            "data": {
                "file": serialize_result_file(target_file),
                "preview": preview,
            },
        }
    ), 200
