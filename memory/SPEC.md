# Wingman living spec

Wingman is an English, dark-mode internal data search portal. Users sign in with an httpOnly cookie session. Owners manage users, departments, file uploads and records; admins are limited to pending approval actions; normal users only see records in assigned departments.

## Data model
- users: id, name, email, password_hash, role, status, department_ids, timestamps
- departments: id, name, description, timestamps
- files: id, original CSV content, department, upload summary and timestamps
- records: id, file_id, department_id, generic CSV data, indexed search_text, fingerprint
- sessions/password_tokens: short-lived access and demo password reset records

## Key flows
- Owner signs in, views dashboard, searches records, uploads CSVs, manages files/departments/users, approves requests and changes password.
- Users can request access, sign in after approval, search scoped data, and change/reset passwords.
- File uploads persist in MongoDB and support duplicate skipping, download, delete and re-upload.
- Search is paginated and indexed by search_text and department scope; bulk lookup handles newline-separated values.

## Demo permissions
Owner: full access. Admin: approval queue only. User: dashboard/search within assigned departments. No third-party integrations are used.