# LegalShield

FastAPI backend and static frontend for authentication, account management, legal chat, and PPC/CrPC section lookup. Modules 4-10 remain prototype-only UI screens.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The app is served at `http://127.0.0.1:8000/`; API docs are at `/docs`. Python 3.11+ is recommended.

## Firebase setup

The application uses Firebase Authentication and Cloud Firestore; SQLite and PostgreSQL are not runtime databases. The checked-in `google-services (1).json` contains browser-safe client configuration only. Configure Firebase Admin credentials on the server using one of:

```dotenv
FIREBASE_SERVICE_ACCOUNT_JSON=<service-account-json-or-base64-json>
```

or `GOOGLE_APPLICATION_CREDENTIALS` pointing to a service-account file outside the repository. Never place service-account credentials in frontend files or commit them. Set `FIREBASE_STORAGE_BUCKET` if the bucket is not specified in the Firebase project configuration. Enable Firestore and Storage in Firebase.

Enable the **Email/Password** provider in Firebase Console under **Authentication → Sign-in method**, and add the app's domain under **Authorized domains**. The app uses Firebase Authentication for password sign-in and account identities. Registration, password recovery, and phone-number changes use backend-generated six-digit email codes delivered through the configured SMTP server.

Add your SMTP provider's settings to the backend `.env` file for registration, password recovery, and phone-number changes. The application uses standard authenticated SMTP and supports STARTTLS or implicit TLS:

```dotenv
EMAIL_SMTP_HOST=<provider-smtp-host>
EMAIL_SMTP_PORT=587
EMAIL_SMTP_STARTTLS=true
EMAIL_SMTP_SSL=false
EMAIL_SMTP_USERNAME=<provider-smtp-username>
EMAIL_SMTP_PASSWORD=<provider-smtp-password>
EMAIL_FROM_ADDRESS=<verified-sender-address>
```

Use the SMTP host, port, username, password, sender address, and TLS mode supplied by your provider (including ServerSMTP). For implicit TLS, set `EMAIL_SMTP_STARTTLS=false` and `EMAIL_SMTP_SSL=true`; otherwise use STARTTLS as shown. If `EMAIL_FROM_ADDRESS` is omitted, the authenticated SMTP username is used as the sender. Keep `.env` private and never commit SMTP credentials. `.env.example` contains placeholders only. Email codes expire after five minutes by default (`OTP_MINUTES=5`), are stored hashed, and are never returned to the browser or generated as a demo fallback. Email delivery fails explicitly when SMTP is unavailable; no code or success response is fabricated.

`firestore.rules` restricts browser access to the signed-in user's `users/{uid}/settings/app` preferences document. Deploy it with:

```powershell
firebase deploy --only firestore:rules
```

The Admin SDK bypasses these client rules. Backend endpoints verify Firebase ID tokens and enforce application roles. User, profile, contact, device, OTP, refresh-token, password-reset-grant, and statute records are persisted to Firestore. Verification uploads use Firebase Storage. Preferences and Firebase auth persistence survive browser restarts and sync across devices.

Server-backed operations return a clear service-unavailable error until Admin credentials are configured; there is no local database fallback.

## Migrate legacy data once

The runtime contains no SQLite database layer. The one-time migration script is the only SQLite reader. It copies records from the legacy `legalshield.db` into the corresponding Firestore collections and never overwrites a destination document with the same ID. Run a dry run first:

```powershell
python -m scripts.migrate_sqlite_to_firestore --source legalshield.db --dry-run
python -m scripts.migrate_sqlite_to_firestore --source legalshield.db
```

The command reports counts only, not record contents. If existing CNIC values were encrypted, configure the same `DATA_ENCRYPTION_KEY` (or legacy `JWT_SECRET`) used by the old application before reading those fields. Review the report and validate the app against Firestore before archiving or removing the SQLite source. Migration is explicit and is never performed at startup.

## Authentication and development

- Registration requires an email address and is blocked from account access until the user enters the emailed six-digit OTP. Codes expire, are stored hashed, can only be used once, and can be resent after the 60-second cooldown. Users sign in with Firebase email/password after OTP verification. The Firebase identity-exchange endpoint maps verified identities to the matching registered account. Protected API calls use Firebase ID tokens. The backend tolerates up to five seconds of clock skew when verifying ID tokens.
- Password recovery and phone-number changes use six-digit email codes with a five-minute validity period by default. The resend control is disabled for 60 seconds, and a successful resend invalidates the previous code. Password recovery requires OTP verification before allowing a new password.
- `DATA_ENCRYPTION_KEY` should be a stable secret in production; it protects CNIC values in Firestore.
- `JWT_SECRET` is still used for application refresh-token hashing/signing internals. Set a strong secret in production.

Admin users cannot self-register. Create or update one with:

```powershell
python -m scripts.seed_admin --phone 03001112233 --name "Admin" --password "a-long-password"
```

Statute data can be loaded with `python -m scripts.load_statutes path\to\statutes.json`. Records must be advisor-reviewed unless `--allow-unreviewed` is explicitly supplied. The checked-in sample statutes are unverified development placeholders and should not be served to real users.

The chatbot defaults to the offline mock provider. To use Anthropic, install `requirements-optional.txt` and configure `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, and `LLM_MODEL`.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest
```

The test suite uses an in-memory Firestore test double. It exercises repository and API behavior without cloud credentials; it does not replace Firebase Emulator or production-project validation.
"# Legalshield" 
