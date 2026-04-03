# web_demo

这是一个前后端同仓库管理的内部测试工具：

- 后端：Flask，目录为 `backend/`
- 前端：Vue + Vite，目录为 `frontend/`
- 部署方式：单容器，对外暴露 `5003`

当前方案保留了前后端代码边界，但在部署阶段统一打包，适合本地构建镜像并通过 `docker compose` 快速启动。

## 目录结构

```text
.
|-- backend/              Flask 后端
|   |-- app/
|   |-- test_case/
|   |-- requirements.txt
|   `-- run.py
|-- frontend/             Vue 前端
|-- Dockerfile            单容器镜像构建文件
|-- docker-compose.yml    本地 compose 启动文件
|-- README.md
`-- .gitignore
```

## 本地开发

### 后端

```powershell
cd backend
python -m pip install -r requirements.txt
python run.py
```

默认监听：`http://127.0.0.1:5003`

### 前端

```powershell
cd frontend
npm install
npm run dev
```

开发模式下，Vite 会代理请求到后端接口。

## Docker Compose 部署

项目根目录已经提供：

- `Dockerfile`：先构建前端，再将 `frontend/dist` 打进 Flask 容器
- `docker-compose.yml`：本地构建镜像、加载 `.env`，并映射端口 `5003:5003`
- `.env.example`：环境变量模板

首次使用建议先复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

容器启动后，以下目录会持久化到仓库根目录下的 `docker-data/`：

- `docker-data/backend-instance`：SQLite 数据库等后端实例数据
- `docker-data/test_case`：测试用例上传文件
- `docker-data/sql_kit`：SQL Kit 模板与结果文件

在项目根目录执行：

```powershell
docker compose up --build -d
```

查看日志：

```powershell
docker compose logs -f
```

查看容器健康状态：

```powershell
docker compose ps
```

停止并删除容器：

```powershell
docker compose down
```

启动后直接访问：

```text
http://127.0.0.1:5003
```

## 单独构建镜像

如果你只想先构建镜像，也可以执行：

```powershell
docker build -t fpp-test-toolkit:local .
docker run -p 5003:5003 fpp-test-toolkit:local
```

## 主要接口

- `GET /Get_equipment`
- `GET /sql-kit`
- `GET /sql-kit/tools`
- `GET /sql-kit/template`
- `POST /sql-kit/template`
- `POST /sql-kit/template/analyze`
- `POST /sql-kit/run`
- `GET /sql-kit/results`
- `GET /sql-kit/result-preview`
- `GET /sql-kit/download`
- `GET /testcases`
- `POST /testcases/upload`
- `POST /testcases/delete`
- `GET /testcases/download`
- `GET /testcases/view`
- `POST /Sum_json`
- `POST /Get_field`
- `POST /Get_exp_field`
- `POST /Get_json`
- `POST /Create_order`
- `GET /get_user`
- `POST /UserInfo`
- `GET /metrics`
- `GET /metrics/raw`

## 后续如果要拆分成双容器

当前仓库已经保留了拆分边界，后续只需要：

1. 让前端单独构建镜像
2. 停止由 Flask 托管 `frontend/dist`
3. 使用 Nginx 或网关分别转发前端页面与后端接口流量

前后端源码目录不需要重写，迁移成本较低。
