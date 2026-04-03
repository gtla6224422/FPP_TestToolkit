# coding=utf-8

from datetime import datetime
from pathlib import Path
import re

from flask import Blueprint, current_app, jsonify, request, send_file

Testcase_bp = Blueprint("testcase_bp", __name__)

ALLOWED_EXTENSIONS = {
    ".csv",
    ".doc",
    ".docx",
    ".html",
    ".json",
    ".pdf",
    ".txt",
    ".xls",
    ".xlsx",
}
INVALID_NAME_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def get_testcase_dir() -> Path:
    # 测试用例统一保存在后端根目录下，便于部署后的持久化管理。
    testcase_dir = Path(current_app.root_path).parent / "test_case"
    testcase_dir.mkdir(parents=True, exist_ok=True)
    return testcase_dir


def validate_name(name: str, label: str) -> str:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError(f"{label}不能为空")
    if cleaned_name in {".", ".."}:
        raise ValueError(f"{label}不合法")
    if INVALID_NAME_PATTERN.search(cleaned_name):
        raise ValueError(f"{label}包含非法字符")
    return cleaned_name


def serialize_file(path: Path, base_dir: Path) -> dict:
    relative_path = path.relative_to(base_dir).as_posix()
    stat = path.stat()
    suffix = path.suffix.lower()
    return {
        "name": path.name,
        "type": "file",
        "relative_path": relative_path,
        "size": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "extension": suffix,
        "is_html": suffix == ".html",
    }


def get_target_file(raw_path: str | None) -> tuple[Path, Path]:
    if not raw_path:
        raise ValueError("缺少文件路径")

    file_name = validate_name(raw_path, "文件名")
    base_dir = get_testcase_dir().resolve()
    target_file = (base_dir / file_name).resolve()

    try:
        target_file.relative_to(base_dir)
    except ValueError as exc:
        raise ValueError("文件路径不合法") from exc

    if not target_file.exists() or not target_file.is_file():
        raise FileNotFoundError("目标文件不存在")

    return base_dir, target_file


@Testcase_bp.route("/testcases", methods=["GET"])
def list_testcases():
    testcase_dir = get_testcase_dir().resolve()
    files = [
        serialize_file(path, testcase_dir)
        for path in sorted(testcase_dir.iterdir(), key=lambda item: item.name.lower())
        if path.is_file()
    ]
    return jsonify({"status_code": 200, "data": files}), 200


@Testcase_bp.route("/testcases/upload", methods=["POST"])
def upload_testcase():
    if "file" not in request.files:
        return jsonify({"status_code": 10001, "error": "缺少上传文件"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"status_code": 10002, "error": "文件名不能为空"}), 400

    try:
        file_name = validate_name(file.filename, "文件名")
    except ValueError as exc:
        return jsonify({"status_code": 10003, "error": str(exc)}), 400

    suffix = Path(file_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return jsonify({"status_code": 10004, "error": "暂不支持该文件类型"}), 400

    testcase_dir = get_testcase_dir().resolve()
    target_path = testcase_dir / file_name
    if target_path.exists():
        return jsonify({"status_code": 10007, "error": "同名文件已存在，请先重命名后再上传"}), 400

    file.save(target_path)

    return jsonify(
        {
            "status_code": 200,
            "message": "上传成功",
            "data": serialize_file(target_path, testcase_dir),
        }
    ), 200


@Testcase_bp.route("/testcases/delete", methods=["POST"])
def delete_testcase():
    payload = request.get_json(silent=True) or {}

    try:
        _, target_file = get_target_file(payload.get("path"))
    except (ValueError, FileNotFoundError) as exc:
        return jsonify({"status_code": 10008, "error": str(exc)}), 400

    target_file.unlink()
    return jsonify({"status_code": 200, "message": "删除成功"}), 200


@Testcase_bp.route("/testcases/download", methods=["GET"])
def download_testcase():
    try:
        _, target_file = get_target_file(request.args.get("path"))
    except (ValueError, FileNotFoundError) as exc:
        return jsonify({"status_code": 10008, "error": str(exc)}), 400

    return send_file(target_file, as_attachment=True, download_name=target_file.name)


@Testcase_bp.route("/testcases/view", methods=["GET"])
def view_testcase_file():
    try:
        _, target_file = get_target_file(request.args.get("path"))
    except (ValueError, FileNotFoundError) as exc:
        return jsonify({"status_code": 10008, "error": str(exc)}), 400

    if target_file.suffix.lower() != ".html":
        return jsonify({"status_code": 10009, "error": "当前文件不支持在线打开"}), 400

    return send_file(target_file, as_attachment=False, download_name=target_file.name)
