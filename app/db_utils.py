# coding=utf-8

import pymysql


def build_db_config(app_config, prefix):
    return {
        "host": app_config[f"{prefix}_HOST"],
        "port": app_config[f"{prefix}_PORT"],
        "user": app_config[f"{prefix}_USER"],
        "password": app_config[f"{prefix}_PASSWORD"],
        "database": app_config[f"{prefix}_NAME"],
        "cursorclass": pymysql.cursors.DictCursor,
        "connect_timeout": 5,
        "read_timeout": 10,
        "write_timeout": 10,
        "charset": "utf8mb4",
    }


def query_all(db_config, sql, params=None):
    connection = None

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        if connection is not None:
            connection.close()
