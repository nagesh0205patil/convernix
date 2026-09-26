# Meta WhatsApp WABA Recovery Runbook

**Purpose:** Resolve Meta Cloud API `HTTP 403`, error code `200`:

> You do not have the necessary permissions to send messages on behalf of this WhatsApp Business Account.

**Prepared:** 28 August 2026  
**Environment:** Arcitech WhatsApp notification service

## 1. Account identifiers

Verify every identifier before changing anything in Meta.

| Resource | Expected value |
|---|---|
| Meta app | WA Router |
| Meta App ID | `1892900065001354` |
| WABA name | Arcitech.ai |
| WABA ID | `1554264889756785` |
| Sender number | `+91 80 3526 0741` |
| Phone Number ID | `1195399166988483` |
| System User | `wa-router` |
| Template | `whatsapp_lead_notification` |
| Template language | `en` |
| Graph API version | `v23.0` |

## 2. Important findings

The configured token is valid and currently reports both permissions as granted:

- `whatsapp_business_management`
- `whatsapp_business_messaging`

The token can read the WABA and Phone Number ID. The sender is a Cloud API number with green quality. However, Meta rejected outbound messages with error `#200`.

Two applications are subscribed to the WABA:

- `WA Router` (`1892900065001354`)
- `WABA Connect` (`1839036260238754`)

The phone also reported `code_verification_status: EXPIRED`. This describes an expired ownership-verification flow. The temporary verification code cannot be kept alive permanently. The durable solution is to complete ownership verification and phone registration, while ensuring the correct System User and app control the WABA.

## 3. Safety rules

- Never paste an access token or registration PIN into Git, source code, tickets, chat, screenshots, or logs.
- Use a permanent System User token for production, not a temporary API Setup token.
- Do not remove `WABA Connect` until its ownership and current production role are confirmed.
- Do not automatically register the phone from the Celery message-sending task.
- Back up the six-digit two-step-verification PIN in a password manager or secrets manager.
- Use placeholders in all commands below.

## 4. Confirm business and WABA status

1. Open [Meta Business Settings](https://business.facebook.com/settings/).
2. Select the Arcitech business portfolio.
3. Go to **Accounts > WhatsApp accounts**.
4. Select WABA `1554264889756785`.
5. Confirm that the WABA is owned by, or correctly shared with, this portfolio.
6. Confirm the WABA is active and not restricted.
7. Open **WhatsApp Manager** and review:
   - Account quality
   - Business verification
   - Payment method
   - Phone-number status
8. Resolve any restriction shown by Meta before proceeding.

## 5. Resolve the WABA Connect relationship

1. Determine whether `WABA Connect` is still the official BSP/provider for this number.
2. If it is still in use, contact the provider before changing phone registration, two-step verification, or asset assignments.
3. If the company migrated away from WABA Connect, use the provider's official disconnect/offboarding procedure.
4. Do not blindly delete or unsubscribe the provider. An incomplete migration can interrupt inbound webhooks or leave the sender under the wrong integration.
5. Continue only after confirming that `WA Router` is intended to send directly through Meta Cloud API.

## 6. Assign the WABA to the System User

1. In Meta Business Settings, go to **Users > System users**.
2. Select `wa-router`.
3. Choose **Add assets** or **Assign assets**.
4. Select **WhatsApp accounts**.
5. Select WABA `1554264889756785`.
6. Grant **Full control** or **Manage WhatsApp account**.
7. Save.
8. Go to **Accounts > WhatsApp accounts > Arcitech.ai**.
9. Open **People**, **Partners**, or **Assigned users**.
10. Confirm `wa-router` is present with management access.

For API-based assignment checks, Meta exposes:

```text
GET /v23.0/1554264889756785/assigned_users?business={BUSINESS_ID}
```

The System User should have the `MANAGE` task.

## 7. Generate a permanent System User token

Generate a new token only after the asset assignment is correct.

1. Go to **Business Settings > Users > System users**.
2. Select `wa-router`.
3. Select **Generate new token**.
4. Choose app `WA Router` (`1892900065001354`).
5. Grant:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
6. Grant `business_management` only if the account-management workflow requires it.
7. Generate the token and place it directly into an approved secrets manager.
8. Do not send the token by email or messaging applications.

## 8. Verify the app webhook

1. Open [Meta for Developers](https://developers.facebook.com/apps/).
2. Open app `WA Router`.
3. Go to **WhatsApp > Configuration**.
4. Confirm the callback URL is the production endpoint:

   ```text
   https://YOUR-DOMAIN/api/whatsapp/webhook/
   ```

5. Confirm the Meta verify token matches the backend `WHATSAPP_VERIFY_TOKEN`.
6. Confirm the `messages` webhook field is subscribed.
7. Avoid changing the callback if it belongs to an active provider integration until the provider relationship is resolved.

## 9. Verify the WABA app subscription

List subscribed applications:

```bash
curl \
  "https://graph.facebook.com/v23.0/1554264889756785/subscribed_apps" \
  -H "Authorization: Bearer ${SYSTEM_USER_TOKEN}"
```

The response must include `WA Router`, app ID `1892900065001354`.

If it is absent, subscribe the app:

```bash
curl -X POST \
  "https://graph.facebook.com/v23.0/1554264889756785/subscribed_apps" \
  -H "Authorization: Bearer ${SYSTEM_USER_TOKEN}"
```

Expected response:

```json
{"success": true}
```

## 10. Complete phone ownership verification

In **WhatsApp Manager > Phone numbers**, select `+91 80 3526 0741`.

1. If Meta displays **Verify**, **Finish setup**, or **Register**, start the flow.
2. Select SMS or voice verification.
3. Ensure the company can receive the code on the sender number.
4. Enter the temporary verification code immediately.
5. Do not confuse this temporary SMS/voice code with the durable six-digit two-step-verification PIN.

If Embedded Signup was completed more than 14 days ago and registration was never completed, repeat Embedded Signup before attempting registration.

## 11. Set or recover the two-step-verification PIN

1. In WhatsApp Manager, select Phone Number ID `1195399166988483`.
2. Open **Settings > Two-step verification**.
3. Set or reset a six-digit PIN.
4. Save a backup in a password manager or secrets manager.
5. Do not store the PIN in the Django database unless an approved encryption mechanism is used.

Meta stores the active PIN. The application needs it only for registration or specific administrative operations; routine messages do not include it.

## 12. Register the phone with Cloud API

Use the newly generated System User token and the two-step-verification PIN:

```bash
curl -X POST \
  "https://graph.facebook.com/v23.0/1195399166988483/register" \
  -H "Authorization: Bearer ${SYSTEM_USER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "pin": "REPLACE_WITH_6_DIGIT_PIN"
  }'
```

Expected response:

```json
{"success": true}
```

This is a controlled administrative operation. Do not call it for every outgoing message.

## 13. Validate token permissions

```bash
curl \
  "https://graph.facebook.com/v23.0/me/permissions" \
  -H "Authorization: Bearer ${SYSTEM_USER_TOKEN}"
```

Confirm the response contains:

```text
whatsapp_business_management: granted
whatsapp_business_messaging: granted
```

## 14. Validate sender access

```bash
curl \
  "https://graph.facebook.com/v23.0/1195399166988483?fields=id,display_phone_number,verified_name,quality_rating,platform_type" \
  -H "Authorization: Bearer ${SYSTEM_USER_TOKEN}"
```

Confirm:

- ID is `1195399166988483`.
- Display number is `+91 80 3526 0741`.
- Platform is `CLOUD_API`.
- Quality rating is acceptable.

## 15. Test Meta's standard template

Test authorization and sender registration before using the custom template:

```bash
curl -X POST \
  "https://graph.facebook.com/v23.0/1195399166988483/messages" \
  -H "Authorization: Bearer ${SYSTEM_USER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "RECIPIENT_NUMBER_WITH_COUNTRY_CODE",
    "type": "template",
    "template": {
      "name": "hello_world",
      "language": {"code": "en_US"}
    }
  }'
```

Interpret the result:

- `HTTP 200` with a message ID: authorization and sender registration work.
- `HTTP 403`, error `#200`: System User, WABA ownership, app, or provider assignment is still incorrect.
- Accepted message followed by a failed status webhook: inspect the asynchronous WhatsApp error code.

## 16. Test the approved application template

The application currently sends five body parameters in this order:

1. Customer name
2. Customer WhatsApp number
3. Department name
4. Enquiry message
5. Received date/time

Confirm the approved Meta template has exactly five body variables in this order, then test:

```bash
curl -X POST \
  "https://graph.facebook.com/v23.0/1195399166988483/messages" \
  -H "Authorization: Bearer ${SYSTEM_USER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "RECIPIENT_NUMBER_WITH_COUNTRY_CODE",
    "type": "template",
    "template": {
      "name": "whatsapp_lead_notification",
      "language": {"code": "en"},
      "components": [{
        "type": "body",
        "parameters": [
          {"type": "text", "text": "Test Customer"},
          {"type": "text", "text": "+919999999999"},
          {"type": "text", "text": "Support"},
          {"type": "text", "text": "Test enquiry"},
          {"type": "text", "text": "28-Aug-2026 01:00 PM"}
        ]
      }]
    }
  }'
```

If the approved template uses a different parameter count or order, update the backend parameter list to match it exactly.

## 17. Update application configuration

In Django admin, update the `WhatsAppConfiguration` record for `+918035260741`:

| Setting | Required value |
|---|---|
| Meta App ID | `1892900065001354` |
| WABA ID | `1554264889756785` |
| Phone Number ID | `1195399166988483` |
| API version | `v23.0` |
| Template | `whatsapp_lead_notification` |
| Language | `en` |
| Access token | New permanent `wa-router` System User token |

The database-backed token takes priority over `WHATSAPP_ACCESS_TOKEN` from the environment. Updating `.env` alone will not change the token used by the worker while a database token exists.

Set TLS verification back to the secure value:

```text
WHATSAPP_DISABLE_TLS_VERIFY=False
```

Restart the backend and Celery worker if environment configuration changed.

## 18. Final application test

1. Confirm the direct `hello_world` test succeeds.
2. Confirm the direct `whatsapp_lead_notification` test succeeds.
3. Send a new inbound customer message to the company number.
4. Confirm the webhook returns `HTTP 200`.
5. Confirm `process_webhook_payload` succeeds.
6. Confirm `send_department_notification` logs `Meta message accepted` and a Meta message ID.
7. Confirm later webhook events change the notification to `delivered` and then `read`, where applicable.
8. Confirm no access token, PIN, or full personal recipient number appears in logs.

## 19. Troubleshooting decision table

| Result | Likely cause | Action |
|---|---|---|
| `403 / #200` | System User lacks effective WABA sending assignment, wrong owning app/provider, or incomplete migration | Recheck Sections 5–7 |
| Registration says permission denied | Token is not from the assigned System User or lacks messaging permission | Generate a new token after asset assignment |
| Registration window expired | Embedded Signup was not completed within 14 days | Repeat Embedded Signup, verify ownership, then register |
| `hello_world` succeeds but custom template fails | Template name, language, status, or parameters do not match | Compare exact template structure in WhatsApp Manager |
| Request accepted but delivery later fails | Recipient, payment, quality, policy, or conversation-level issue | Read the failed status webhook error code |
| Inbound webhook stops after provider changes | Wrong app subscription or callback ownership | Restore/repair WABA subscription and webhook configuration |

## 20. Completion checklist

- [ ] WABA is active and unrestricted.
- [ ] WABA Connect ownership/usage is confirmed and any migration is complete.
- [ ] `wa-router` has full management access to the WABA.
- [ ] A new permanent token was generated after asset assignment.
- [ ] Required WhatsApp permissions are granted.
- [ ] WA Router is subscribed to the WABA.
- [ ] Phone ownership verification is complete.
- [ ] Two-step-verification PIN is securely backed up.
- [ ] Phone registration returned `{"success": true}`.
- [ ] `hello_world` direct API test succeeds.
- [ ] Custom template direct API test succeeds.
- [ ] Django database configuration contains the new token.
- [ ] TLS certificate verification is enabled.
- [ ] End-to-end webhook and Celery delivery succeeds.

## 21. Official references

- [Meta WhatsApp Cloud API documentation](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api)
- [Register Phone](https://www.postman.com/meta/whatsapp-business-platform/request/zb2u18b/register-phone)
- [Registration requirements](https://www.postman.com/meta/whatsapp-business-platform/folder/zuoeksl/registration)
- [Subscribe an app to a WABA](https://www.postman.com/meta/whatsapp-business-platform/request/c1ai24q/subscribe-to-your-waba)
- [Embedded Signup and assigned System Users](https://www.postman.com/meta/whatsapp-business-platform/documentation/du6gzjv/embedded-signup?entity=request-13382743-656e8eed-45ed-4740-aba1-c632dc1f64df)

