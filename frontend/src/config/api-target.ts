export type ApiTargetKey = "local" | "cloud";

type ApiTargetConfig = {
  label: string;
  directBaseUrl: string;
  proxyPath: string;
};

const STORAGE_KEY = "webdemo_api_target";
const DEFAULT_TARGET: ApiTargetKey = "local";

// 把真实后端地址和开发代理路径分开管理：
// 页面展示真实地址，开发环境实际走代理，避免浏览器跨域。
export const API_TARGETS: Record<ApiTargetKey, ApiTargetConfig> = {
  local: {
    label: "本地",
    directBaseUrl: "http://127.0.0.1:5003",
    proxyPath: "/api-local",
  },
  cloud: {
    label: "云端",
    directBaseUrl: "http://8.134.195.209:5003",
    proxyPath: "/api-cloud",
  },
};

function isApiTargetKey(value: unknown): value is ApiTargetKey {
  return value === "local" || value === "cloud";
}

export function getApiTarget(): ApiTargetKey {
  const cached = window.localStorage.getItem(STORAGE_KEY);
  if (isApiTargetKey(cached)) {
    return cached;
  }
  return DEFAULT_TARGET;
}

export function setApiTarget(target: ApiTargetKey): void {
  window.localStorage.setItem(STORAGE_KEY, target);
}

export function getCurrentApiBaseUrl(): string {
  const target = API_TARGETS[getApiTarget()];
  if (import.meta.env.DEV) {
    return target.proxyPath;
  }
  return target === API_TARGETS.local ? "" : target.directBaseUrl;
}

export function getCurrentApiDisplayUrl(): string {
  if (!import.meta.env.DEV && getApiTarget() === "local") {
    return window.location.origin;
  }
  return API_TARGETS[getApiTarget()].directBaseUrl;
}

export function getApiStorageKey(): string {
  return STORAGE_KEY;
}
