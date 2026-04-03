<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  apiDeleteTestcase,
  apiGetEquipment,
  apiGetSqlKitTemplate,
  apiGetSqlKitTools,
  apiListSqlKitResults,
  apiListTestcases,
  apiRunSqlKitTool,
  apiSaveSqlKitTemplate,
  apiUploadTestcase,
} from "@/api/endpoints";
import {
  API_TARGETS,
  type ApiTargetKey,
  getApiStorageKey,
  getApiTarget,
  getCurrentApiBaseUrl,
  getCurrentApiDisplayUrl,
  setApiTarget,
} from "@/config/api-target";

type PageMode = "dashboard" | "testcase" | "sqlKit" | "equipment";
type MessageTone = "info" | "success" | "error";
type LogLevel = "info" | "success" | "error";

type EquipmentItem = Record<string, string | number | null>;

type TestcaseFileItem = {
  name: string;
  type: "file";
  relative_path: string;
  size: number;
  updated_at: string;
  extension: string;
  is_html: boolean;
};

type SqlKitParam = {
  key: string;
  label: string;
  type: "number" | "text";
  required: boolean;
  min?: number;
  placeholder?: string;
  help?: string;
};

type SqlKitResultFile = {
  name: string;
  size: number;
  updated_at: string;
  relative_path: string;
};

type SqlKitTemplateItem = {
  index: number;
  preview: string;
};

type SqlKitTool = {
  id: string;
  name: string;
  description: string;
  params: SqlKitParam[];
  results?: SqlKitResultFile[];
};

type SqlKitLog = {
  time: string;
  level: LogLevel;
  message: string;
};

const pageMode = ref<PageMode>("dashboard");
const apiTarget = ref<ApiTargetKey>(getApiTarget());

const equipmentRows = ref<EquipmentItem[]>([]);
const equipmentLoading = ref(false);
const equipmentKeyword = ref("");
const equipmentMessage = ref("进入页面后会自动加载可用设备池。");
const equipmentMessageTone = ref<MessageTone>("info");

const testcaseFiles = ref<TestcaseFileItem[]>([]);
const testcaseLoading = ref(false);
const testcaseUploading = ref(false);
const testcaseDeleting = ref(false);
const deletingFilePath = ref("");
const testcaseMessage = ref("请选择测试用例文件后上传，文件会保存在后端项目根目录下的 test_case 文件夹。");
const testcaseMessageTone = ref<MessageTone>("info");
const lastDeletedFileName = ref("");
const selectedFile = ref<File | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

const sqlTools = ref<SqlKitTool[]>([]);
const selectedSqlToolId = ref("");
const sqlKitTemplateContent = ref("");
const sqlKitTemplatePath = ref("");
const sqlKitTemplateUpdatedAt = ref("");
const sqlKitTemplateItems = ref<SqlKitTemplateItem[]>([]);
const sqlKitResults = ref<SqlKitResultFile[]>([]);
const sqlKitLogs = ref<SqlKitLog[]>([]);
const sqlKitPreviewLines = ref<string[]>([]);
const sqlKitCopyingPreview = ref(false);
const sqlKitLoading = ref(false);
const sqlKitSaving = ref(false);
const sqlKitRunning = ref(false);
const sqlKitMessage = ref("选择 SQL 工具后即可编辑模板并执行脚本。");
const sqlKitMessageTone = ref<MessageTone>("info");
const sqlKitParams = reactive<Record<string, string>>({});

const apiBaseUrl = computed(() => getCurrentApiDisplayUrl());
const apiRequestMode = computed(() =>
  import.meta.env.DEV ? "开发模式代理转发（避免浏览器跨域）" : "浏览器直接请求后端",
);
const selectedFileName = computed(() => selectedFile.value?.name || "未选择文件");
const selectedSqlTool = computed(() => sqlTools.value.find((tool) => tool.id === selectedSqlToolId.value) ?? null);
const currentPageLabel = computed(() => {
  if (pageMode.value === "sqlKit") {
    return "SQL 脚本工具";
  }
  if (pageMode.value === "equipment") {
    return "可用设备池";
  }
  if (pageMode.value === "testcase") {
    return "测试用例管理";
  }
  return "仪表盘";
});
const breadcrumbItems = computed(() => {
  const items = ["首页", currentPageLabel.value];
  if (pageMode.value === "sqlKit" && selectedSqlTool.value?.name) {
    items.push(selectedSqlTool.value.name);
  }
  return items;
});
const equipmentColumnLabelMap: Record<string, string> = {
  tenant_id: "租户ID",
  name: "目前所在租户",
  equipment_id: "设备编号",
  activate_status_h5: "H5激活状态",
  activate_status: "激活状态",
  online_status: "在线状态",
  ".online_status": "激活状态",
};
const equipmentColumns = computed(() => {
  const firstRow = equipmentRows.value[0];
  return firstRow ? Object.keys(firstRow) : [];
});
const filteredEquipmentRows = computed(() => {
  const keyword = equipmentKeyword.value.trim().toLowerCase();
  if (!keyword) {
    return equipmentRows.value;
  }
  return equipmentRows.value.filter((item) => String(item.equipment_id ?? "").toLowerCase().includes(keyword));
});
const equipmentOnlineCount = computed(() =>
  equipmentRows.value.filter((item) => getEquipmentStatusKind(item) === "online").length,
);
const equipmentOfflineCount = computed(() =>
  equipmentRows.value.filter((item) => getEquipmentStatusKind(item) === "offline").length,
);
const equipmentUnknownCount = computed(() =>
  Math.max(equipmentRows.value.length - equipmentOnlineCount.value - equipmentOfflineCount.value, 0),
);
const equipmentOnlineRate = computed(() => {
  const classifiedTotal = equipmentOnlineCount.value + equipmentOfflineCount.value;
  if (classifiedTotal === 0) {
    return 0;
  }
  return Math.round((equipmentOnlineCount.value / classifiedTotal) * 100);
});
const equipmentGaugeStyle = computed(() => ({
  background: `conic-gradient(#16a34a 0deg ${equipmentOnlineRate.value * 3.6}deg, #f97316 ${equipmentOnlineRate.value * 3.6}deg 360deg)`,
}));
const equipmentDashboardHint = computed(() => {
  if (equipmentLoading.value) {
    return "正在同步设备状态...";
  }
  if (equipmentRows.value.length === 0) {
    return "还没有设备数据，首页会自动尝试加载一次。";
  }
  if (equipmentUnknownCount.value > 0) {
    return `有 ${equipmentUnknownCount.value} 台设备状态未识别，首页统计已按设备列表中的“在线状态”列口径计算。`;
  }
  if (equipmentOfflineCount.value === 0) {
    return "当前设备全部在线，可以直接进入设备池查看明细。";
  }
  return `当前有 ${equipmentOfflineCount.value} 台设备离线，建议优先排查最近未心跳设备。`;
});

function pretty(data: unknown) {
  return JSON.stringify(data, null, 2);
}

function formatFileSize(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function renderError(error: unknown) {
  if (typeof error === "object" && error !== null && "response" in error) {
    const e = error as {
      response?: {
        status?: number;
        data?: unknown;
      };
      message?: string;
    };
    return pretty({
      message: e.message ?? "请求失败",
      status: e.response?.status,
      data: e.response?.data,
      requestBaseUrl: getCurrentApiBaseUrl(),
      displayBaseUrl: getCurrentApiDisplayUrl(),
    });
  }

  if (typeof error === "object" && error !== null && "message" in error) {
    const e = error as { message?: string };
    return pretty({
      message: e.message ?? "网络请求异常",
      requestBaseUrl: getCurrentApiBaseUrl(),
      displayBaseUrl: getCurrentApiDisplayUrl(),
      hint: import.meta.env.DEV
        ? "如果修改了 vite.config.ts 但代理未生效，请重启 Vite 开发服务。"
        : "生产环境如有跨域问题，需要后端开启 CORS 或由同源反向代理转发。",
    });
  }

  return String(error);
}

function setTestcaseMessage(message: string, tone: MessageTone = "info") {
  testcaseMessage.value = message;
  testcaseMessageTone.value = tone;
}

function setSqlKitMessage(message: string, tone: MessageTone = "info") {
  sqlKitMessage.value = message;
  sqlKitMessageTone.value = tone;
}

function setEquipmentMessage(message: string, tone: MessageTone = "info") {
  equipmentMessage.value = message;
  equipmentMessageTone.value = tone;
}

function getEncodedFileUrl(endpoint: string, relativePath: string) {
  const baseUrl = getCurrentApiDisplayUrl();
  const query = encodeURIComponent(relativePath);
  return `${baseUrl}${endpoint}?path=${query}`;
}

function getDownloadUrl(relativePath: string) {
  return getEncodedFileUrl("/testcases/download", relativePath);
}

function getPreviewUrl(relativePath: string) {
  return getEncodedFileUrl("/testcases/view", relativePath);
}

function getSqlKitDownloadUrl(relativePath: string) {
  return getEncodedFileUrl("/sql-kit/download", relativePath);
}

function isDeletingFile(relativePath: string) {
  return testcaseDeleting.value && deletingFilePath.value === relativePath;
}

function getLogClass(level: LogLevel) {
  return `log-${level}`;
}

function isNavActive(target: PageMode) {
  return pageMode.value === target;
}

function getEquipmentColumnLabel(column: string) {
  return equipmentColumnLabelMap[column] ?? column;
}

function getEquipmentStatusKind(item: EquipmentItem): "online" | "offline" | "unknown" {
  const statusValue = String(item.online_status ?? "").trim().toLowerCase();
  if (!statusValue) {
    return "unknown";
  }

  if (["1", "true", "online", "on", "已在线", "在线", "上线"].some((keyword) => statusValue.includes(keyword))) {
    return "online";
  }

  if (["2", "false", "offline", "off", "已离线", "离线"].some((keyword) => statusValue.includes(keyword))) {
    return "offline";
  }

  return "unknown";
}

async function copySqlKitPreview() {
  const previewText = sqlKitPreviewLines.value.join("\n").trim();
  if (!previewText) {
    setSqlKitMessage("当前没有可复制的预览内容。", "error");
    return;
  }

  sqlKitCopyingPreview.value = true;
  try {
    await navigator.clipboard.writeText(previewText);
    setSqlKitMessage("结果预览内容已复制到剪贴板。", "success");
  } catch (error) {
    setSqlKitMessage(`复制预览内容失败：${renderError(error)}`, "error");
  } finally {
    sqlKitCopyingPreview.value = false;
  }
}

async function loadTestcases() {
  testcaseLoading.value = true;
  try {
    const resp = await apiListTestcases();
    testcaseFiles.value = resp.data.data ?? [];
  } catch (error) {
    setTestcaseMessage(`加载文件列表失败：${renderError(error)}`, "error");
  } finally {
    testcaseLoading.value = false;
  }
}

async function loadEquipment() {
  equipmentLoading.value = true;
  try {
    const resp = await apiGetEquipment();
    equipmentRows.value = resp.data.data ?? [];
    if (equipmentRows.value.length > 0) {
      setEquipmentMessage(`已加载 ${equipmentRows.value.length} 台设备。`, "success");
    } else {
      setEquipmentMessage("当前没有查询到设备数据。");
    }
  } catch (error) {
    equipmentRows.value = [];
    setEquipmentMessage(`加载设备池失败：${renderError(error)}`, "error");
  } finally {
    equipmentLoading.value = false;
  }
}

function switchApiTarget(target: ApiTargetKey) {
  if (target === apiTarget.value) {
    return;
  }
  setApiTarget(target);
  apiTarget.value = target;
  if (pageMode.value === "equipment") {
    setEquipmentMessage(`已切换到${API_TARGETS[target].label}，可刷新设备池查看对应环境数据。`, "success");
  }
}

async function goToTestcasePage() {
  pageMode.value = "testcase";
  setTestcaseMessage("正在加载测试用例列表...");
  await loadTestcases();
  if (testcaseFiles.value.length === 0) {
    setTestcaseMessage("当前还没有上传测试用例文件，请先选择文件并上传。");
  } else {
    setTestcaseMessage(`已加载 ${testcaseFiles.value.length} 个文件。`, "success");
  }
}

async function goToEquipmentPage() {
  pageMode.value = "equipment";
  await loadEquipment();
}

function resetSqlKitState() {
  sqlKitLogs.value = [];
  sqlKitPreviewLines.value = [];
  setSqlKitMessage("选择 SQL 工具后即可编辑模板并执行脚本。");
}

function resetSqlKitParams(tool: SqlKitTool | null) {
  Object.keys(sqlKitParams).forEach((key) => {
    delete sqlKitParams[key];
  });
  if (!tool) {
    return;
  }
  tool.params.forEach((param) => {
    sqlKitParams[param.key] = "";
  });
}

async function loadSqlKitTemplate(toolId: string) {
  if (!toolId) {
    return;
  }

  sqlKitLoading.value = true;
  try {
    const resp = await apiGetSqlKitTemplate(toolId);
    const payload = resp.data.data;
    sqlKitTemplateContent.value = payload.template.content ?? "";
    sqlKitTemplatePath.value = payload.template.path ?? "";
    sqlKitTemplateUpdatedAt.value = payload.template.updated_at ?? "";
    sqlKitTemplateItems.value = payload.template.items ?? [];
    sqlKitResults.value = payload.results ?? [];
    setSqlKitMessage(`已载入模板：${payload.tool.name}`, "success");
  } catch (error) {
    setSqlKitMessage(`加载 SQL 工具模板失败：${renderError(error)}`, "error");
  } finally {
    sqlKitLoading.value = false;
  }
}

async function loadSqlKitResults(toolId: string) {
  if (!toolId) {
    return;
  }
  try {
    const resp = await apiListSqlKitResults(toolId);
    sqlKitResults.value = resp.data.data ?? [];
  } catch (error) {
    setSqlKitMessage(`刷新结果文件失败：${renderError(error)}`, "error");
  }
}

async function loadSqlKitTools(initial = false) {
  sqlKitLoading.value = true;
  try {
    const resp = await apiGetSqlKitTools();
    sqlTools.value = resp.data.data ?? [];
    const currentTool = sqlTools.value.find((tool) => tool.id === selectedSqlToolId.value);
    const targetTool = currentTool ?? sqlTools.value[0] ?? null;
    selectedSqlToolId.value = targetTool?.id ?? "";
    resetSqlKitParams(targetTool);
    if (targetTool) {
      await loadSqlKitTemplate(targetTool.id);
      if (initial) {
        setSqlKitMessage(`已载入 ${targetTool.name}，可以直接编辑模板并执行。`, "success");
      }
    }
  } catch (error) {
    setSqlKitMessage(`加载 SQL 工具列表失败：${renderError(error)}`, "error");
  } finally {
    sqlKitLoading.value = false;
  }
}

async function goToSqlKitPage() {
  pageMode.value = "sqlKit";
  resetSqlKitState();
  await loadSqlKitTools(true);
}

async function selectSqlTool(tool: SqlKitTool) {
  if (tool.id === selectedSqlToolId.value) {
    return;
  }
  selectedSqlToolId.value = tool.id;
  resetSqlKitParams(tool);
  sqlKitLogs.value = [];
  sqlKitPreviewLines.value = [];
  await loadSqlKitTemplate(tool.id);
}

async function saveSqlTemplate() {
  if (!selectedSqlTool.value) {
    return;
  }

  sqlKitSaving.value = true;
  try {
    const resp = await apiSaveSqlKitTemplate(selectedSqlTool.value.id, sqlKitTemplateContent.value);
    sqlKitTemplateUpdatedAt.value = resp.data.data.updated_at ?? sqlKitTemplateUpdatedAt.value;
    setSqlKitMessage(`模板保存成功：${selectedSqlTool.value.name}`, "success");
    await loadSqlKitTemplate(selectedSqlTool.value.id);
  } catch (error) {
    setSqlKitMessage(`模板保存失败：${renderError(error)}`, "error");
  } finally {
    sqlKitSaving.value = false;
  }
}

async function runSqlTool() {
  if (!selectedSqlTool.value) {
    return;
  }

  const params: Record<string, string | number> = {};
  selectedSqlTool.value.params.forEach((param) => {
    const rawValue = sqlKitParams[param.key];
    params[param.key] = param.type === "number" ? Number(rawValue) : rawValue;
  });

  sqlKitRunning.value = true;
  sqlKitLogs.value = [];
  sqlKitPreviewLines.value = [];
  setSqlKitMessage(`正在执行：${selectedSqlTool.value.name}`);
  try {
    const resp = await apiRunSqlKitTool(selectedSqlTool.value.id, params, sqlKitTemplateContent.value);
    sqlKitLogs.value = resp.data.data.logs ?? [];
    sqlKitPreviewLines.value = resp.data.data.result?.preview ?? [];
    sqlKitResults.value = resp.data.data.results ?? [];
    setSqlKitMessage(`执行完成：${selectedSqlTool.value.name}`, "success");
    await loadSqlKitTemplate(selectedSqlTool.value.id);
  } catch (error) {
    const responseData = (error as { response?: { data?: { data?: { logs?: SqlKitLog[] } } } }).response?.data;
    sqlKitLogs.value = responseData?.data?.logs ?? [];
    setSqlKitMessage(`执行失败：${renderError(error)}`, "error");
  } finally {
    sqlKitRunning.value = false;
  }
}

function goToDashboard() {
  pageMode.value = "dashboard";
}

function onSelectFile(event: Event) {
  const target = event.target as HTMLInputElement;
  selectedFile.value = target.files?.[0] ?? null;
  setTestcaseMessage(
    selectedFile.value ? `已选择文件：${selectedFile.value.name}` : "未选择文件。",
  );
}

function resetSelectedFile() {
  selectedFile.value = null;
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
}

async function uploadSelectedFile() {
  if (!selectedFile.value) {
    setTestcaseMessage("请先选择要上传的测试用例文件。", "error");
    return;
  }

  testcaseUploading.value = true;
  setTestcaseMessage(`正在上传：${selectedFile.value.name}`);
  try {
    const resp = await apiUploadTestcase(selectedFile.value);
    lastDeletedFileName.value = "";
    setTestcaseMessage(`上传成功：${resp.data.data?.name ?? selectedFile.value.name}`, "success");
    resetSelectedFile();
    await loadTestcases();
  } catch (error) {
    setTestcaseMessage(`上传失败：${renderError(error)}`, "error");
  } finally {
    testcaseUploading.value = false;
  }
}

async function deleteFile(item: TestcaseFileItem) {
  const shouldDelete = window.confirm(`确认删除文件：${item.name}？`);
  if (!shouldDelete) {
    return;
  }

  testcaseDeleting.value = true;
  deletingFilePath.value = item.relative_path;
  setTestcaseMessage(`正在删除：${item.name}`);
  try {
    await apiDeleteTestcase(item.relative_path);
    lastDeletedFileName.value = item.name;
    await loadTestcases();
    setTestcaseMessage(`删除成功：${item.name}`, "success");
  } catch (error) {
    setTestcaseMessage(`删除失败：${renderError(error)}`, "error");
  } finally {
    testcaseDeleting.value = false;
    deletingFilePath.value = "";
  }
}

onMounted(() => {
  if (equipmentRows.value.length === 0) {
    void loadEquipment();
  }
});
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar card">
      <div class="sidebar-brand">
        <div class="sidebar-eyebrow">Workbench</div>
        <h2>小猪测试工具箱</h2>
        <p>根据现有卡片能力整理成稳定导航，常用入口可以直接从左侧进入。</p>
      </div>

      <nav class="sidebar-nav">
        <button class="nav-item" :class="{ 'nav-item-active': isNavActive('dashboard') }" @click="goToDashboard">
          <span class="nav-title">仪表盘</span>
          <span class="nav-desc">查看总览、切换接口地址、查看接口返回结果</span>
        </button>
        <button class="nav-item" :class="{ 'nav-item-active': isNavActive('sqlKit') }" @click="goToSqlKitPage">
          <span class="nav-title">SQL 脚本工具</span>
          <span class="nav-desc">模板编辑、执行日志、结果预览和下载</span>
        </button>
        <button class="nav-item" :class="{ 'nav-item-active': isNavActive('testcase') }" @click="goToTestcasePage">
          <span class="nav-title">测试用例管理</span>
          <span class="nav-desc">上传、删除、下载并在线打开测试文件</span>
        </button>
        <button class="nav-item nav-item-quiet" :class="{ 'nav-item-active': isNavActive('equipment') }" @click="goToEquipmentPage">
          <span class="nav-title">可用设备池</span>
          <span class="nav-desc">查看设备列表，支持设备名称模糊搜索</span>
        </button>
      </nav>

      <div class="sidebar-foot">
        <span class="status">当前环境</span>
        <code>{{ apiBaseUrl }}</code>
      </div>
    </aside>

    <main class="app-main">
      <div class="breadcrumb">
        <span v-for="(item, index) in breadcrumbItems" :key="`${item}-${index}`" class="breadcrumb-item">
          <span v-if="index > 0" class="breadcrumb-sep">/</span>
          <span :class="{ 'breadcrumb-current': index === breadcrumbItems.length - 1 }">{{ item }}</span>
        </span>
      </div>

      <div v-if="pageMode === 'dashboard'">
        <h1 class="page-title">小猪测试工具箱</h1>
        <p class="page-subtitle">
          支持本地和云端接口切换。开发模式下通过 Vite 代理转发请求，避免浏览器跨域。
        </p>

        <section class="card switcher-card">
          <div class="switcher-row">
            <div>
              <h3>接口地址切换</h3>
              <p class="status">当前目标地址：<code>{{ apiBaseUrl }}</code></p>
              <p class="status">当前请求模式：<code>{{ apiRequestMode }}</code></p>
              <p class="status">本地缓存键：<code>{{ getApiStorageKey() }}</code></p>
            </div>
            <div class="actions">
              <button
                class="btn-secondary"
                :class="{ 'btn-active': apiTarget === 'local' }"
                :disabled="equipmentLoading"
                @click="switchApiTarget('local')"
              >
                本地
              </button>
              <button
                class="btn-secondary"
                :class="{ 'btn-active': apiTarget === 'cloud' }"
                :disabled="equipmentLoading"
                @click="switchApiTarget('cloud')"
              >
                云端
              </button>
            </div>
          </div>
        </section>

        <section class="card equipment-gauge-card">
          <div class="equipment-gauge-header">
            <div>
              <h3>已接入设备总览</h3>
            </div>
            <div class="actions">
              <button class="btn-secondary" :disabled="equipmentLoading" @click="loadEquipment">
                {{ equipmentLoading ? "同步中..." : "刷新状态" }}
              </button>
              <button class="btn-primary" :disabled="equipmentLoading" @click="goToEquipmentPage">
                查看设备池
              </button>
            </div>
          </div>

          <div class="equipment-gauge-layout">
            <div class="equipment-gauge-wrap">
              <div class="equipment-gauge" :style="equipmentGaugeStyle">
                <div class="equipment-gauge-core">
                  <span class="gauge-value">{{ equipmentRows.length }}</span>
                  <span class="gauge-label">已接入设备</span>
                </div>
              </div>
              <div class="gauge-rate">
                <span class="gauge-rate-value">{{ equipmentOnlineRate }}%</span>
                <span class="gauge-rate-label">在线占比</span>
              </div>
            </div>

            <div class="equipment-stat-list">
              <div class="equipment-stat-item equipment-stat-online">
                <span class="equipment-stat-dot"></span>
                <div>
                  <div class="equipment-stat-value">{{ equipmentOnlineCount }}</div>
                  <div class="equipment-stat-label">在线设备</div>
                </div>
              </div>
              <div class="equipment-stat-item equipment-stat-offline">
                <span class="equipment-stat-dot"></span>
                <div>
                  <div class="equipment-stat-value">{{ equipmentOfflineCount }}</div>
                  <div class="equipment-stat-label">离线设备</div>
                </div>
              </div>
              <div class="equipment-stat-item equipment-stat-total">
                <span class="equipment-stat-dot"></span>
                <div>
                  <div class="equipment-stat-value">{{ equipmentRows.length }}</div>
                  <div class="equipment-stat-label">设备总数</div>
                </div>
              </div>
            </div>

            <div class="equipment-gauge-side">
              <div class="equipment-side-kicker">Live Monitor</div>
              <h4>接入状态总览</h4>
              <p class="status equipment-side-copy">
                这张卡片会优先展示当前设备规模和离线风险，适合作为首页第一视觉。
              </p>
              <p class="status equipment-gauge-hint" :class="[`status-${equipmentMessageTone}`]">
                {{ equipmentDashboardHint }}
              </p>
            </div>
          </div>
        </section>

        <div class="layout layout-tools">
          <section class="card sql-kit-card">
            <h3>SQL 脚本工具</h3>
            <p class="status card-desc">
              集成 SQL 模板编辑、脚本执行、终端日志与结果文件下载，后续可以继续扩展更多 SQL 工具。
            </p>
            <div class="actions">
              <button class="btn-primary" @click="goToSqlKitPage">管理</button>
            </div>
          </section>

          <section class="card">
            <h3>可用设备池</h3>
            <p class="status card-desc">
              独立页面展示设备列表，支持按设备名称模糊筛选，并直接查看接口返回字段。
            </p>
            <div class="actions">
              <button class="btn-primary" :disabled="equipmentLoading" @click="goToEquipmentPage">进入设备池</button>
            </div>
          </section>

          <section class="card feature-card">
            <h3>测试用例管理</h3>
            <p class="status card-desc">
              进入独立管理页面，支持上传测试用例、下载文件、删除文件以及在线打开 HTML 文件。
            </p>
            <div class="actions">
              <button class="btn-primary" @click="goToTestcasePage">管理测试用例</button>
            </div>
          </section>
        </div>

      </div>

      <div v-else-if="pageMode === 'sqlKit'" class="page-shell sql-kit-shell">
        <div class="page-header">
          <div>
            <h1 class="page-title">SQL 脚本工具</h1>
            <p class="page-subtitle">通过 Flask 统一管理模板、执行 SQL 生成工具，并在页面中查看日志与结果文件。</p>
          </div>
          <button class="btn-secondary" @click="goToDashboard">返回首页</button>
        </div>

        <div class="sql-kit-grid">
          <section class="card sql-tool-panel">
            <div class="panel-header">
              <h3>工具列表</h3>
              <span class="status">共 {{ sqlTools.length }} 个工具</span>
            </div>
            <div class="tool-list">
              <button
                v-for="tool in sqlTools"
                :key="tool.id"
                class="tool-item"
                :class="{ 'tool-item-active': tool.id === selectedSqlToolId }"
                @click="selectSqlTool(tool)"
              >
                <span class="tool-name">{{ tool.name }}</span>
                <span class="tool-desc">{{ tool.description }}</span>
              </button>
            </div>
          </section>

          <section class="card sql-main-panel">
            <div class="panel-header">
              <div>
                <h3>{{ selectedSqlTool?.name || "SQL 工具" }}</h3>
                <p class="status">{{ selectedSqlTool?.description || "请选择左侧工具" }}</p>
              </div>
              <div class="actions">
                <button class="btn-secondary" :disabled="sqlKitSaving || sqlKitLoading" @click="saveSqlTemplate">
                  {{ sqlKitSaving ? "保存中..." : "保存模板" }}
                </button>
                <button class="btn-primary" :disabled="sqlKitRunning || sqlKitLoading" @click="runSqlTool">
                  {{ sqlKitRunning ? "执行中..." : "执行脚本" }}
                </button>
              </div>
            </div>

            <div v-if="selectedSqlTool" class="sql-main-content">
              <section class="sql-form-card">
                <div class="panel-header compact-header">
                  <h4>执行参数</h4>
                  <span class="status">模板路径：{{ sqlKitTemplatePath || "未加载" }}</span>
                </div>
                <div class="sql-param-grid">
                  <label v-for="param in selectedSqlTool.params" :key="param.key" class="sql-param-item">
                    <span class="param-label">{{ param.label }}</span>
                    <input
                      v-model="sqlKitParams[param.key]"
                      :type="param.type === 'number' ? 'number' : 'text'"
                      :min="param.min"
                      :placeholder="param.placeholder"
                    />
                    <span v-if="param.help" class="param-help">{{ param.help }}</span>
                  </label>
                </div>
                <div v-if="sqlKitTemplateItems.length > 0" class="template-tip-box">
                  <div class="template-tip-title">当前模板条目</div>
                  <div class="template-tip-list">
                    <div v-for="item in sqlKitTemplateItems" :key="item.index" class="template-tip-item">
                      <span class="template-tip-index">{{ item.index }}</span>
                      <span class="template-tip-text">{{ item.preview }}</span>
                    </div>
                  </div>
                </div>
              </section>

              <section class="sql-editor-card">
                <div class="panel-header compact-header">
                  <h4>模板编辑区</h4>
                  <span class="status">最近更新：{{ sqlKitTemplateUpdatedAt || "暂无" }}</span>
                </div>
                <textarea v-model="sqlKitTemplateContent" class="sql-editor" spellcheck="false" />
                <p class="status" :class="[`status-${sqlKitMessageTone}`]">{{ sqlKitMessage }}</p>
              </section>
            </div>
          </section>
        </div>

        <div class="sql-kit-bottom-grid">
          <section class="card terminal-card">
            <div class="panel-header">
              <h3>执行日志</h3>
              <div class="actions">
                <button class="btn-secondary" :disabled="!selectedSqlToolId" @click="loadSqlKitResults(selectedSqlToolId)">刷新结果</button>
                <button class="btn-secondary" @click="sqlKitLogs = []">清空日志</button>
              </div>
            </div>
            <div class="terminal-window">
              <div v-if="sqlKitLogs.length === 0" class="terminal-empty">执行后会在这里显示仿终端日志。</div>
              <div v-for="(log, index) in sqlKitLogs" :key="`${log.time}-${index}`" class="terminal-line" :class="getLogClass(log.level)">
                <span class="terminal-time">[{{ log.time }}]</span>
                <span class="terminal-level">{{ log.level.toUpperCase() }}</span>
                <span class="terminal-text">{{ log.message }}</span>
              </div>
            </div>
            <div v-if="sqlKitPreviewLines.length > 0" class="preview-box">
              <div class="panel-header compact-header">
                <div class="preview-title">结果预览</div>
                <button class="btn-secondary" :disabled="sqlKitCopyingPreview" @click="copySqlKitPreview">
                  {{ sqlKitCopyingPreview ? "复制中..." : "复制全部" }}
                </button>
              </div>
              <pre class="preview-content">{{ sqlKitPreviewLines.join("\n") }}</pre>
            </div>
          </section>

          <section class="card result-file-card">
            <div class="panel-header">
              <h3>结果文件</h3>
              <span class="status">共 {{ sqlKitResults.length }} 个文件</span>
            </div>
            <div v-if="sqlKitResults.length === 0" class="empty-state">
              当前还没有生成结果文件，执行脚本后会显示在这里。
            </div>
            <div v-else class="file-list">
              <div v-for="item in sqlKitResults" :key="item.relative_path" class="file-row">
                <div class="file-main">
                  <div class="file-name">{{ item.name }}</div>
                  <div class="file-meta">更新时间：{{ item.updated_at }}</div>
                  <div class="file-meta">大小：{{ formatFileSize(item.size) }}</div>
                </div>
                <div class="row-actions">
                  <a class="link-btn" :href="getSqlKitDownloadUrl(item.relative_path)" target="_blank" rel="noreferrer">
                    下载结果
                  </a>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <div v-else-if="pageMode === 'equipment'" class="page-shell">
        <div class="page-header">
          <div>
            <h1 class="page-title">可用设备池</h1>
            <p class="page-subtitle">展示设备查询接口返回的数据，支持按设备编号模糊搜索。</p>
          </div>
          <div class="actions">
            <button class="btn-secondary" :disabled="equipmentLoading" @click="loadEquipment">
              {{ equipmentLoading ? "加载中..." : "刷新设备池" }}
            </button>
            <button class="btn-secondary" @click="goToDashboard">返回首页</button>
          </div>
        </div>

        <section class="card manager-card">
          <div class="equipment-toolbar">
            <label class="equipment-search">
              <span class="param-label">设备编号查询</span>
              <input v-model="equipmentKeyword" type="text" placeholder="输入设备编号，支持模糊搜索" />
            </label>
            <div class="equipment-summary">
              <span class="status">设备总数：{{ equipmentRows.length }}</span>
              <span class="status">筛选结果：{{ filteredEquipmentRows.length }}</span>
            </div>
          </div>
          <p class="status manager-status" :class="[`status-${equipmentMessageTone}`]">{{ equipmentMessage }}</p>
        </section>

        <section class="card manager-card">
          <div class="list-header">
            <h3>设备列表</h3>
            <span class="status">{{ equipmentLoading ? "加载中..." : `共 ${filteredEquipmentRows.length} 条` }}</span>
          </div>

          <div v-if="equipmentLoading" class="empty-state">
            正在加载设备数据...
          </div>
          <div v-else-if="filteredEquipmentRows.length === 0" class="empty-state">
            当前没有匹配的设备数据。
          </div>
          <div v-else class="equipment-table-wrap">
            <table class="equipment-table">
              <thead>
                <tr>
                  <th v-for="column in equipmentColumns" :key="column">{{ getEquipmentColumnLabel(column) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, rowIndex) in filteredEquipmentRows" :key="`${item.equipment_id ?? rowIndex}`">
                  <td v-for="column in equipmentColumns" :key="`${rowIndex}-${column}`">
                    {{ item[column] ?? "-" }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div v-else class="page-shell">
        <div class="page-header">
          <div>
            <h1 class="page-title">测试用例管理</h1>
            <p class="page-subtitle">用例文件保存在后端项目根目录下的 test_case 文件夹，支持下载、删除和 HTML 在线打开。</p>
          </div>
          <button class="btn-secondary" @click="goToDashboard">返回首页</button>
        </div>

        <section class="card manager-card">
          <div class="manager-toolbar">
            <input ref="fileInputRef" class="file-input" type="file" @change="onSelectFile" />
            <button class="btn-primary" :disabled="testcaseUploading" @click="uploadSelectedFile">
              {{ testcaseUploading ? "上传中..." : "上传文件" }}
            </button>
            <button class="btn-secondary" :disabled="testcaseLoading || testcaseDeleting" @click="loadTestcases()">
              刷新列表
            </button>
          </div>
          <p class="status manager-status">当前选择：{{ selectedFileName }}</p>
          <p class="status manager-status" :class="[`status-${testcaseMessageTone}`]">{{ testcaseMessage }}</p>
          <p v-if="lastDeletedFileName" class="status manager-status status-success">最近删除：{{ lastDeletedFileName }}</p>
        </section>

        <section class="card manager-card">
          <div class="list-header">
            <h3>文件列表</h3>
            <span class="status">{{ testcaseLoading ? "加载中..." : `共 ${testcaseFiles.length} 个文件` }}</span>
          </div>

          <div v-if="testcaseFiles.length === 0" class="empty-state">
            当前还没有上传测试用例文件，请先上传。
          </div>

          <div v-else class="file-list">
            <div v-for="item in testcaseFiles" :key="`file-${item.relative_path}`" class="file-row">
              <div class="file-main">
                <a
                  v-if="item.is_html"
                  class="file-link"
                  :href="getPreviewUrl(item.relative_path)"
                  target="_blank"
                  rel="noreferrer"
                >
                  {{ item.name }}
                </a>
                <div v-else class="file-name">{{ item.name }}</div>
                <div class="file-meta">更新时间：{{ item.updated_at }}</div>
                <div class="file-meta">大小：{{ formatFileSize(item.size) }}</div>
              </div>
              <div class="row-actions">
                <a class="link-btn" :href="getDownloadUrl(item.relative_path)" target="_blank" rel="noreferrer">
                  下载文件
                </a>
                <a
                  v-if="item.is_html"
                  class="link-btn link-btn-light"
                  :href="getPreviewUrl(item.relative_path)"
                  target="_blank"
                  rel="noreferrer"
                >
                  打开页面
                </a>
                <button
                  class="btn-danger"
                  :disabled="testcaseDeleting"
                  @click="deleteFile(item)"
                >
                  {{ isDeletingFile(item.relative_path) ? "删除中..." : "删除文件" }}
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>
