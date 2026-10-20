/**
 * Minimal typed fetch wrapper for the core API (IMPLEMENTATION.md §13).
 * Always sends cookies (`credentials: "include"`) since auth is httpOnly
 * JWT cookies, not a bearer token the client holds. Errors are normalized
 * to the `{ error: { code, params } }` envelope the backend returns
 * (`app.core.errors`) so callers can translate `error.code` via i18n.
 *
 * A fuller typed client (openapi-fetch generated from
 * packages/contracts/openapi.json, per §3/§5) replaces this once enough of
 * the API surface exists to make codegen worthwhile — this hand-written
 * version covers Phase P1's auth/me/clock endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  code: string;
  params: Record<string, unknown>;
  status: number;

  constructor(status: number, code: string, params: Record<string, unknown> = {}) {
    super(code);
    this.status = status;
    this.code = code;
    this.params = params;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let code = "HTTP_ERROR";
    let params: Record<string, unknown> = { status: res.status };
    try {
      const body = await res.json();
      if (body?.error?.code) {
        code = body.error.code;
        params = body.error.params ?? {};
      }
    } catch {
      // response had no JSON body — keep the generic HTTP_ERROR code
    }
    throw new ApiError(res.status, code, params);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PUT", body: body !== undefined ? JSON.stringify(body) : undefined }),
};

// ---------------------------------------------------------------------------
// Types used by Phase P1 screens
// ---------------------------------------------------------------------------

export type UserRole =
  | "INSTITUTION"
  | "SCRUTINY_OFFICER"
  | "REGIONAL_OFFICER"
  | "BUREAU_HEAD"
  | "COMMITTEE_MEMBER"
  | "EVC_EXPERT"
  | "ADMIN";

export interface RegionOut {
  id: string;
  code: string;
  name: string;
}

export interface MeOut {
  id: string;
  name: string;
  role: UserRole;
  preferred_language: string;
  theme: "light" | "dark" | "system";
  institution_id: string | null;
  regions: RegionOut[];
}

export function sendOtp(identifier: string, role: UserRole) {
  return api.post<{ sent: boolean; expires_in_seconds: number }>("/api/v1/auth/otp/send", {
    identifier,
    role,
  });
}

export function verifyOtp(identifier: string, role: UserRole, code: string) {
  return api.post<MeOut>("/api/v1/auth/otp/verify", { identifier, role, code });
}

export function logout() {
  return api.post<{ ok: boolean }>("/api/v1/auth/logout");
}

export function getMe() {
  return api.get<MeOut>("/api/v1/me");
}

export function updateMe(body: Partial<Pick<MeOut, "name" | "preferred_language" | "theme">>) {
  return api.patch<MeOut>("/api/v1/me", body);
}

// ---------------------------------------------------------------------------
// Types used by Phase P2 screens (IMPLEMENTATION.md §13.2, §13.3)
// ---------------------------------------------------------------------------

export type ApplicationType =
  | "NEW_INSTITUTION"
  | "EXTENSION_OF_APPROVAL"
  | "INTAKE_INCREASE"
  | "NEW_COURSE"
  | "CHANGE_OF_NAME"
  | "CHANGE_OF_SITE"
  | "COLLABORATION"
  | "CLOSURE";

export type ApplicationStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "IN_PROCESS"
  | "DECISION_RECORDED"
  | "APPROVED"
  | "APPROVED_WITH_CONDITIONS"
  | "REJECTED"
  | "WITHDRAWN";

export type StageStatus = "PENDING" | "ACTIVE" | "COMPLETED" | "RETURNED" | "REFERRED" | "SKIPPED";

export interface ApplicationTypeOut {
  code: ApplicationType;
  name_key: string;
  required_document_types: string[];
}

export interface ApplicationCourse {
  id?: string;
  course_name: string;
  level: string;
  existing_intake: number;
  proposed_intake: number;
}

export interface ApplicationOut {
  id: string;
  app_no: string | null;
  institution_id: string;
  application_type: ApplicationType;
  academic_year: string;
  status: ApplicationStatus;
  current_stage_key: string | null;
  payload: Record<string, unknown>;
  submitted_at: string | null;
  decided_at: string | null;
  final_decision: string | null;
  courses: ApplicationCourse[];
}

export interface DeadlineOut {
  id: string;
  due_at: string;
  status: "ACTIVE" | "PAUSED" | "CLOSED";
  owner_party: string;
}

export interface StageInstanceOut {
  id: string;
  application_id: string;
  app_no: string | null;
  institution_name: string;
  stage_key: string;
  seq: number;
  status: StageStatus;
  activated_at: string | null;
  completed_at: string | null;
  returns_count: number;
  assigned_user_id: string | null;
  deadline: DeadlineOut | null;
  allowed_actions: string[];
  ai_flag_count: number;
}

export interface DeficiencyOut {
  id: string;
  reason_code: string | null;
  custom_text: string | null;
  status: string;
  response_text: string | null;
}

export interface DeficiencyLetterOut {
  id: string;
  stage_instance_id: string;
  language: string;
  body_md: string;
  ai_generated: boolean;
  edited: boolean;
  sent_at: string | null;
  sent_by: string | null;
}

export interface TimelineEntryOut {
  id: string;
  actor: string;
  action: string;
  at: string;
  channel: string | null;
}

export interface InstitutionOut {
  id: string;
  aicte_id: string;
  name: string;
  type: "GOVT" | "PRIVATE" | "AIDED" | "DEEMED";
  city: string;
  address: string;
  health_score: number | null;
}

export function getInstitution(id: string) {
  return api.get<InstitutionOut>(`/api/v1/institutions/${id}`);
}

export function listApplicationTypes() {
  return api.get<ApplicationTypeOut[]>("/api/v1/application-types");
}

export function listApplications() {
  return api.get<ApplicationOut[]>("/api/v1/applications");
}

export function getApplication(id: string) {
  return api.get<ApplicationOut>(`/api/v1/applications/${id}`);
}

export function createApplication(body: {
  application_type: ApplicationType;
  academic_year: string;
  payload?: Record<string, unknown>;
  courses?: ApplicationCourse[];
}) {
  return api.post<ApplicationOut>("/api/v1/applications", body);
}

export function updateApplication(
  id: string,
  body: { payload?: Record<string, unknown>; courses?: ApplicationCourse[] }
) {
  return api.patch<ApplicationOut>(`/api/v1/applications/${id}`, body);
}

export function precheckApplication(id: string) {
  return api.post<{ status: string; message_key: string }>(`/api/v1/applications/${id}/precheck`);
}

export function sendSubmitOtp(id: string) {
  return api.post<{ sent: boolean; expires_in_seconds: number }>(`/api/v1/applications/${id}/submit/otp`);
}

export function submitApplication(id: string, code: string) {
  return api.post<ApplicationOut>(`/api/v1/applications/${id}/submit`, { code });
}

export function withdrawApplication(id: string) {
  return api.post<ApplicationOut>(`/api/v1/applications/${id}/withdraw`);
}

export function resubmitApplication(
  id: string,
  responses: { deficiency_id: string; response_text: string }[]
) {
  return api.post<ApplicationOut>(`/api/v1/applications/${id}/resubmit`, { responses });
}

export function getApplicationStages(id: string) {
  return api.get<StageInstanceOut[]>(`/api/v1/applications/${id}/stages`);
}

export function getApplicationTimeline(id: string) {
  return api.get<TimelineEntryOut[]>(`/api/v1/applications/${id}/timeline`);
}

export function getQueue() {
  return api.get<StageInstanceOut[]>("/api/v1/queue");
}

export function getStage(id: string) {
  return api.get<StageInstanceOut>(`/api/v1/stages/${id}`);
}

export function getStageDeficiencies(stageId: string) {
  return api.get<DeficiencyOut[]>(`/api/v1/stages/${stageId}/deficiencies`);
}

export function performStageAction(
  stageId: string,
  body: {
    action: string;
    reason?: string;
    deficiencies?: { reason_code?: string | null; custom_text?: string | null }[];
    letter_body_md?: string;
  }
) {
  return api.post<StageInstanceOut>(`/api/v1/stages/${stageId}/actions`, body);
}

export function draftDeficiencyLetter(
  stageId: string,
  body: { reason: string; deficiencies: { reason_code?: string | null; custom_text?: string | null }[] }
) {
  return api.post<DeficiencyLetterOut>(`/api/v1/stages/${stageId}/deficiency-letter/draft`, body);
}

export function updateDeficiencyLetter(letterId: string, bodyMd: string) {
  return api.put<DeficiencyLetterOut>(`/api/v1/deficiency-letters/${letterId}`, { body_md: bodyMd });
}

export function sendDeficiencyLetter(letterId: string) {
  return api.post<DeficiencyLetterOut>(`/api/v1/deficiency-letters/${letterId}/send`);
}
