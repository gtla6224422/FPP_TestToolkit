import { http } from "./client";

export function apiGetUser(id: number, role: number) {
  return http.get("/get_user", { params: { id, role } });
}

export function apiUserInfo(role: number) {
  return http.post("/UserInfo", { role });
}

export function apiCreateOrder(payload: {
  custom_id: number;
  order_cost: number;
  insurance_type: number;
}) {
  return http.post("/Create_order", payload);
}

export function apiSumJson(field_name: string) {
  return http.post("/Sum_json", { field_name });
}

export function apiGetEquipment() {
  return http.get("/Get_equipment");
}

export function apiListTestcases() {
  return http.get("/testcases");
}

export function apiUploadTestcase(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return http.post("/testcases/upload", formData);
}

export function apiDeleteTestcase(path: string) {
  return http.post("/testcases/delete", { path });
}

export function apiGetSqlKitTools() {
  return http.get("/sql-kit/tools");
}

export function apiGetSqlKitTemplate(tool: string) {
  return http.get("/sql-kit/template", { params: { tool } });
}

export function apiSaveSqlKitTemplate(tool: string, content: string) {
  return http.post("/sql-kit/template", { tool, content });
}

export function apiRunSqlKitTool(tool: string, params: Record<string, string | number>, content: string) {
  return http.post("/sql-kit/run", { tool, params, content });
}

export function apiListSqlKitResults(tool: string) {
  return http.get("/sql-kit/results", { params: { tool } });
}
