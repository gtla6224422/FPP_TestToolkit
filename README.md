# web_demo

一个用于内部测试与运维辅助的小工具站，采用单仓库管理：

- 后端：Flask，目录为 `backend/`
- 前端：Vue + Vite，目录为 `frontend/`
- 部署：单容器，对外只暴露 `5003`

当前方案保留了前后端代码边界，但在部署阶段统一打包，适合小型工具站快速维护与发布。

## 目录结构

```text
.
├─ backend/             Flask 后端
│  ├─ app/
│  ├─ test_case/
│  ├─ requirements.txt
│  └─ run.py
├─ frontend/            Vue 前端
├─ Dockerfile           单容器构建文件
├─ README.md
└─ .gitignore
```

## 本地开发

### 后端

```powershell
cd backend
python -m pip install -r requirements.txt
python run.py
```

默认监听 `http://127.0.0.1:5003`

### 前端

```powershell
cd frontend
npm install
npm run dev
```

开发模式下，Vite 会通过代理转发到后端接口。

## 单容器构建

```powershell
docker build -t webdemo-toolbox .
docker run -p 5003:5003 webdemo-toolbox
```

启动后直接访问：

```text
http://127.0.0.1:5003
```

前端静态资源由 Flask 统一托管，接口也走同一域名与端口。

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

## 后续如果要拆回双容器

当前结构已经保留了可拆分边界，后续只需要：

1. 让前端单独构建镜像
2. 停止由 Flask 托管 `frontend/dist`
3. 用 Nginx 或网关把页面流量转到前端、接口流量转到后端

前后端源码目录无需重写，迁移成本较低。
