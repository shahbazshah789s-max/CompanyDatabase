# Company Database living spec

Company Database is an English, dark-mode internal data search portal. Users sign in with an httpOnly cookie session. Owners manage users, departments, file uploads and records; admins are limited to pending approval actions; normal users only see records in assigned departments. CSV originals up to 1 GB use resumable 4 MB chunks, background row indexing, and MongoDB GridFS storage.

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
- Owners can select and bulk-delete files with their attached records, bulk-delete users, block/unblock accounts, and edit company name, logo, and navigation labels.
- Search is paginated and indexed by search_text and department scope; bulk lookup handles newline-separated values.

## Role permissions
- Owner: global data, every team, branding, and all account controls; only Owner can create Pro Admins.
- Pro Admin: dashboard/search plus full file, team, and Admin/User management inside assigned teams; can create teams and delete only teams they created.
- Admin: approval queue only; may grant all or selected teams from their own assigned scope.
- User: Dashboard and Search only, limited to assigned teams.
- Normal User privacy: blank or shorter-than-3-character searches always return zero rows; only matching search results are exposed, file download/list routes are blocked, and all select/delete controls are hidden.

No third-party integrations are used. ChatGPT is not connected because consumer Google login is not an API credential and no paid API key was authorized.