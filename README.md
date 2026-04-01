# web_demo

一个基于 Flask 的接口演示项目，包含登录注册、用户查询、订单创建、JSON 数据提取工具和 Prometheus 监控接口。

## 本地启动

1. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

2. 使用默认本地配置启动

```powershell
python run.py
```

默认会监听 `http://127.0.0.1:5003`，并使用本地 SQLite 数据库 `instance/app.db`。

## 可选环境变量

```powershell
$env:SECRET_KEY="dev-secret"
$env:FLASK_DEBUG="1"
$env:DATABASE_URL="sqlite:///instance/app.db"
$env:REDIS_ENABLED="0"
python run.py
```

如果要接入外部 MySQL / Redis，可以设置：

```powershell
$env:DATABASE_URL="mysql+pymysql://user:password@127.0.0.1:3306/web_demo"
$env:REDIS_ENABLED="1"
$env:REDIS_HOST="127.0.0.1"
$env:REDIS_PORT="6379"
$env:REDIS_PASSWORD=""
python run.py
```

## 主要接口

- `GET /get_user`
- `POST /UserInfo`
- `POST /Create_order`
- `POST /Sum_json`
- `POST /Get_field`
- `POST /Get_exp_field`
- `POST /Get_json`
- `GET /metrics`
- `GET /metrics/raw`
