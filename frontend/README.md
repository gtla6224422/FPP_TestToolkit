# WebDemo Frontend (Vite + Vue 3 + TypeScript)

这是一个独立于 `WebDemo-Flask-` 的前端项目，用于联调 Flask API，并支持本地/云端地址一键切换。

## 目录位置

`D:\测试\WebDemo-Frontend`

## 快速开始

```powershell
cd D:\测试\WebDemo-Frontend
npm install
npm run dev
```

默认前端地址：`http://127.0.0.1:5173`

## 联调说明

- 先启动 Flask：

```powershell
cd D:\测试\WebDemo-Flask-
python run.py
```

然后在前端页面顶部切换 API 地址（默认本地）：

- `本地`：`http://127.0.0.1:5003`
- `云端`：`http://8.134.195.209:5003`
- 切换结果会持久化到浏览器 `localStorage`：`webdemo_api_target`
- `npm run dev` 时，请求会走 Vite proxy：
  - `/api-local -> http://127.0.0.1:5003`
  - `/api-cloud -> http://8.134.195.209:5003`
- 这样开发环境下不会触发浏览器跨域限制

切换后可直接调用：

- `GET /get_user`
- `POST /UserInfo`
- `POST /Create_order`
- `POST /Sum_json`

## 可改项

- 如果 Flask 地址有变更，修改 `src/config/api-target.ts`。
- 如果你想部署到生产，前端单独代码无法绕过浏览器 CORS；需要后端开启 CORS，或者在部署前端的 Web 服务器上配置同源反向代理。
