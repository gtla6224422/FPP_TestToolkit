# coding=utf-8

import logging

from flask import Blueprint, current_app, jsonify
from .db_utils import build_db_config, query_all

Equipment_bp = Blueprint('equipment_bp', __name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EQUIPMENT_SQL = """
select e.tenant_id, t.name, e.equipment_id,
case e.activate_status_h5 when 1 then 'H5未激活' when 2 then 'H5待激活' END AS activate_status_h5,
case e.online_status when 1 then '上线' when 2 then '离线' END AS online_status,
case e.activate_status when 1 then '未激活' when 2 then '待激活' END AS online_status
from fpp_platform.equipment e
inner join fpp_platform.system_tenant t on e.tenant_id = t.id
where e.equipment_id in (
    'XZ0002', 'XZ00025', 'XZ00026', 'PG001193', 'PG000002', 'PH000707', 'PH000528'
)
"""


@Equipment_bp.route('/Get_equipment', methods=['GET'])
def get_equipment():
    try:
        db_config = build_db_config(current_app.config, "FPP_PLATFORM_DB")
        rows = query_all(db_config, EQUIPMENT_SQL)

        return jsonify({
            "status_code": 200,
            "message": "查询设备信息成功",
            "data": rows
        }), 200
    except Exception as exc:
        logger.exception("Failed to query equipment data")
        return jsonify({
            "status_code": 10001,
            "error": f"查询设备信息失败: {str(exc)}"
        }), 500
