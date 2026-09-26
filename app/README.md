# Wavely mobile application

React Native (Expo + TypeScript) client for the existing Django API. It uses the same username/email and password as the web application. JWT access and refresh tokens are stored with the native encrypted keychain/keystore via Expo SecureStore.

After sign-in, the app restores the previously selected WhatsApp business number when it is still available. If the account can access multiple numbers, it asks the user to choose one before showing workspace data. The selected number is sent with every authenticated request, matching the web dashboard's workspace isolation.

## Run locally

```bash
cp .env.example .env
# Set EXPO_PUBLIC_API_URL to the reachable backend, including /api.
npm install
npm run typecheck
npm start
```

Use `http://10.0.2.2:9090/api` for an Android emulator talking to a backend on the host. A physical device needs the host's LAN address. Release builds must use HTTPS.

## Build and deploy

Install/login to EAS once (`npx eas-cli login`) and initialize the Expo project (`npx eas-cli init`) so `EAS_PROJECT_ID` is available. Then:

```bash
./scripts/build.sh apk       # Android installable test APK (preview profile)
./scripts/build.sh android   # Google Play AAB
./scripts/build.sh ios       # App Store IPA (requires Apple developer credentials)
./scripts/build.sh all       # Android and iOS production builds
```

EAS hosts the resulting artifact; download the preview output as an APK into `app/builds/`. Android store submission uses an AAB, while iOS distribution requires Apple signing and TestFlight/App Store.

## Configuration and secrets

Only `EXPO_PUBLIC_API_URL` is readable by application code; every `EXPO_PUBLIC_*` value is public. Do not place passwords, Meta tokens, Django secrets, signing keys, or database credentials in the mobile app.

Build/account values required from the owner:

- `EAS_PROJECT_ID` after `eas init`
- unique `ANDROID_PACKAGE` and `IOS_BUNDLE_IDENTIFIER`
- Expo account authentication for cloud builds
- Google Play service-account JSON only for automated store submission
- Apple Developer Team/App Store Connect credentials only for iOS signing/submission

Existing backend production values that must remain configured in `Backend/.env` include `DJANGO_SECRET_KEY`, database credentials, `ALLOWED_HOSTS`, HTTPS/security settings, platform-admin bootstrap credentials, and mail settings. WhatsApp access token, app signing secret, verify token, phone-number ID, business-account ID, and notification template settings are managed per business number in Django Admin.
