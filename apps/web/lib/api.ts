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

// ---------------------------------------------------------------------------
// Types used by Phase P3 screens (IMPLEMENTATION.md §13.4, §14, §15.3)
// ---------------------------------------------------------------------------

export interface DocumentTypeOut {
  code: string;
  name_key: string;
  has_expiry: boolean;
  extraction_schema: string[];
  min_validity_years: number | null;
}

export interface DocumentVersionOut {
  id: string;
  version: number;
  mime: string;
  size: number;
  sha256: string;
  source: string;
  at: string;
}

export type ExtractionFieldValue = { value: string; confidence: number; page: number; human_verified?: boolean };

export interface ExtractionBox {
  page: number;
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  status: string;
}

export interface ExtractionOut {
  id: string;
  model_id: string;
  fields: Record<string, ExtractionFieldValue>;
  boxes: ExtractionBox[];
  confidence: number;
  page_count: number;
  status: "PENDING" | "DONE" | "FAILED";
}

export interface DocumentOut {
  id: string;
  institution_id: string;
  application_id: string | null;
  document_type: string;
  current_version_id: string | null;
  expiry_date: string | null;
  verified_status: "UNVERIFIED" | "VERIFIED" | "REJECTED";
  verified_by: string | null;
  verified_at: string | null;
  versions: DocumentVersionOut[];
  extraction: ExtractionOut | null;
  preview_url: string | null;
  download_url: string;
}

export interface AiCheckOut {
  check_key: string;
  status: "PASS" | "WARN" | "FAIL";
  message_key: string;
  params: Record<string, unknown>;
}

export interface AiReportOut {
  application_id: string;
  confidence: number;
  checks: AiCheckOut[];
}

function absoluteApiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** Multipart upload — bypasses `api.post`, which always sets a JSON
 * Content-Type; the browser must set its own multipart boundary for FormData.
 */
async function uploadMultipart<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(absoluteApiUrl(path), { method: "POST", credentials: "include", body: form });
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
      // no JSON body
    }
    throw new ApiError(res.status, code, params);
  }
  return (await res.json()) as T;
}

export function listDocumentTypes() {
  return api.get<DocumentTypeOut[]>("/api/v1/document-types");
}

export function uploadDocument(args: { applicationId: string; documentType: string; file: File }) {
  const form = new FormData();
  form.set("application_id", args.applicationId);
  form.set("document_type", args.documentType);
  form.set("file", args.file);
  return uploadMultipart<DocumentOut>("/api/v1/documents", form);
}

export function getDocument(id: string) {
  return api.get<DocumentOut>(`/api/v1/documents/${id}`);
}

export function getApplicationDocuments(applicationId: string) {
  return api.get<DocumentOut[]>(`/api/v1/applications/${applicationId}/documents`);
}

export function verifyDocument(
  id: string,
  body: { fields?: Record<string, string>; expiry_date?: string; result?: "VERIFIED" | "REJECTED" }
) {
  return api.post<DocumentOut>(`/api/v1/documents/${id}/verify`, body);
}

export function getAiReport(applicationId: string) {
  return api.get<AiReportOut>(`/api/v1/applications/${applicationId}/ai-report`);
}

/** Absolute URL for an `<img>`/download link — these stream bytes, not JSON,
 * so they're fetched directly by the browser (with its own session cookie)
 * rather than through the `api` JSON client.
 */
export function documentAssetUrl(relativeUrl: string): string {
  return absoluteApiUrl(relativeUrl);
}
