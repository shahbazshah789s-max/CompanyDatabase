export interface UserPublic {
  id: string; name: string; email: string; role: "owner" | "pro_admin" | "admin" | "user";
  status: "active" | "pending" | "disabled"; department_ids: string[];
  created_at: string; last_login?: string | null;
}
export interface LoginRequest { email: string; password: string }
export interface SignupRequest { name: string; email: string; password: string }
export interface PasswordChangeRequest { current_password: string; new_password: string }
export interface ForgotPasswordRequest { email: string }
export interface ResetPasswordRequest { token: string; new_password: string }
export interface AuthResponse { user: UserPublic; message: string }
export interface Department { id: string; name: string; description: string; record_count: number; user_count: number; created_at: string; created_by?: string | null }
export interface DepartmentCreate { name: string; description: string }
export interface FileAsset { id: string; name: string; department_id: string; department_name: string; size_bytes: number; row_count: number; inserted_count: number; skipped_count: number; uploaded_by: string; uploaded_at: string }
export interface FileUploadResponse { file: FileAsset; message: string }
export interface UploadInitRequest { filename: string; size_bytes: number; department_id: string; total_chunks: number; replace_file_id?: string | null }
export interface UploadSession { id: string; filename: string; size_bytes: number; department_id: string; total_chunks: number; uploaded_chunks: number; status: "uploading" | "processing" | "complete" | "failed"; progress: number; message: string; file_id?: string | null }
export interface BrandSettings { company_name: string; logo_data_url?: string | null; nav_labels: Record<string, string> }
export interface BrandSettingsUpdate extends BrandSettings {}
export interface DashboardStats { total_records: number; active_departments: number; active_users: number; pending_requests: number; recent_files: FileAsset[]; department_breakdown: Array<{ department_id: string; name: string; count: number }> }
export interface RecordRow { id: string; file_id: string; file_name: string; department_id: string; department_name: string; data: Record<string, string>; created_at: string }
export interface RecordSearchResponse { items: RecordRow[]; total: number; page: number; page_size: number; fields: string[] }
export interface BulkLookupRequest { query: string; department_id?: string | null }
export interface BulkLookupResponse { items: RecordRow[]; total_queries: number; matched_queries: number }
export interface ActionResponse { message: string; affected: number }
export interface UserCreate { name: string; email: string; password: string; role: "pro_admin" | "admin" | "user"; department_ids: string[] }
export interface UserUpdate { status?: "active" | "disabled"; role?: "pro_admin" | "admin" | "user"; department_ids?: string[] }
export interface BulkAccessRequest { user_ids: string[]; department_ids: string[]; mode: "replace" | "grant" | "revoke" }
export interface ApprovalAction { action: "approve" | "decline"; department_ids?: string[] | null }
export interface ApprovalSummary { id: string; name: string; email: string; created_at: string }