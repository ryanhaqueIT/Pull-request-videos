# Google Calendar Availability Check — Investigation Report

## Investigation Date: March 22, 2026

## Summary

The WeddingOS platform (AWS-Hackathon) has a **complete but not fully functional** Google Calendar integration. The code is architecturally correct but has never successfully checked real Google Calendar availability during an actual voice call via Amazon Connect.

## Architecture

### Full Call Chain

```
Caller asks "Are you available October 4th?"
  → Amazon Connect / Bedrock Agent → check_availability Lambda
  → Lambda queries DynamoDB (weddingos-calls) for confirmed bookings
  → Lambda checks Google Calendar (if vendor has OAuth token):
      → Read weddingos-oauth-tokens[vendor_id] from DDB
      → Check is_valid == True
      → Decrypt refresh_token with Fernet
      → Build google.oauth2.credentials.Credentials
      → creds.refresh(GoogleRequest())
      → service.events().list(calendarId="primary", ...)
  → Merge: booked = (DDB bookings > 0) OR (GCal has events)
  → Return "available" or "booked"
```

### Token Storage (DynamoDB: weddingos-oauth-tokens)

14 vendors with valid OAuth tokens as of investigation date:
- `calendar_connected: True`, `is_valid: True`
- Tokens Fernet-encrypted at rest
- Fernet key from env var (dev) or AWS Secrets Manager (prod)

### Cross-Cloud Bridge (GCP → AWS)

The GCP project calls AWS Lambda (`bridge_calendar`) via WIF-authenticated Function URL. This Lambda decrypts the vendor's OAuth token and calls Google Calendar API from AWS.

## Issues Found from CloudWatch Logs

### Issue 1: Connect Lambda NEVER Hits Google Calendar

All `weddingos-check-availability` logs show **zero `gcal_*` entries**. Pattern:
```
check_availability_invoked → check_availability_ddb_query → check_availability_done
```

The test vendor `14d8b418-4041-703b-c00a-b32e4af0b7cf` has **no OAuth token in DDB**. GCal path silently returns empty set → DDB-only result every time.

### Issue 2: Bridge Lambda Had Cryptography Library Breakage

```
[ERROR] Fernet decryption failed: cannot import name 'exceptions'
        from 'cryptography.hazmat.bindings._rust' (unknown location)
```

`cryptography` package version mismatch with Python 3.12 Lambda runtime. Hit vendor `94c8e418-e031-705f-b627-205b30936a79` on 3 consecutive invocations before a redeployment fixed it.

### Issue 3: Raw Natural Language Passed as Date

Bridge Lambda receives:
```json
{"date": " Are you available October 4th next year?"}
```

GCP side passes the **entire question** as the date parameter. The bridge has fallback parsing (dateutil + regex) but it produced a malformed datetime on one invocation:
```
timeMin=2026-10-04T00:00:00T00:00:00Z  ← double time component → Google 400 error
```

### One Successful Call

```
2026-03-19T21:56:28 — bridge_calendar_check_done
vendor_id: 94c8e418-e031-705f-b627-205b30936a79
total_events: 0, available_slots: 3
```

Proves the pipeline CAN work end-to-end when dependencies align.

## Status Table

| Component | Status | Issue |
|-----------|--------|-------|
| OAuth token storage (DDB) | Working | 14 vendors with valid tokens |
| Fernet encryption/decryption | Intermittent | cryptography version mismatch in Lambda layer |
| Connect → check_availability | DDB-only | Test vendor has no OAuth token |
| Bridge → Google Calendar API | Fragile | Raw NL dates + datetime formatting bug |
| Actual GCal API call | 1 success / ~6 attempts | Works when all dependencies align |

## Email Search Result

`hinasasuga@gmail.com` is **NOT** in the OAuth tokens table. The 14 connected emails are:
- ryanhaque000@gmail.com (8 vendors)
- yesminrinda@gmail.com (1)
- arzukhanna@gmail.com (1)
- nazhaqit@gmail.com (1)
- p32788276@gmail.com (1)
- 1 vendor with empty email
