import axios from "axios";
import { getCurrentApiBaseUrl } from "@/config/api-target";

export const http = axios.create({
  timeout: 10000,
});

http.interceptors.request.use((config) => {
  // 每次请求都动态读取当前后端地址，这样切换环境后可以立即生效。
  config.baseURL = getCurrentApiBaseUrl();
  return config;
});
