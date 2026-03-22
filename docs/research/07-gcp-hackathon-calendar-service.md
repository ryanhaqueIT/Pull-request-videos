# GCP-Hackathon Calendar Service — Code Analysis

## Overview

The GCP-Hackathon project has its own Google Calendar integration that:
1. Manages OAuth token storage (Fernet-encrypted in Firestore)
2. Checks availability via Google Calendar API v3 `events.list`
3. Creates events for consultation bookings
4. Falls back gracefully when calendar isn't connected

## Key Files

| File | Responsibility |
|------|---------------|
| `backend/services/calendar_service.py` | OAuth, token encryption, calendar API calls |
| `backend/agent/tools.py` | Gemini-callable tool functions (check_availability, get_packages, book_consultation) |
| `backend/bridge/aws_client.py` | Cross-cloud bridge to AWS Lambda for calendar operations |
| `backend/voice/pipeline.py` | Registers tools with Gemini Live session |
| `backend/routers/oauth.py` | OAuth endpoints (/connect, /callback) |

## check_availability Flow (agent/tools.py)

Three-tier fallback:

```
1. AWS Lambda bridge (preferred, cross-cloud)
   → _run_async(_aws_bridge.check_calendar_availability(vendor_id, date))
   → If error → fall through

2. GCP Google Calendar API (direct)
   → calendar_service.check_availability(vendor_id, date)
   → If simulated or error → fall through

3. Hardcoded "available" with vendor name
   → Always returns available (never tells caller "I don't know")
```

## calendar_service.check_availability (services/calendar_service.py)

1. Load agent doc from Firestore
2. Decrypt OAuth token with Fernet
3. Build google.oauth2.credentials.Credentials
4. Parse date (tries: ISO, "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%d/%m/%Y")
5. Call `events.list(calendarId="primary", timeMin=midnight, timeMax=next_midnight)`
6. Return: `{available: len(events)==0, events: [summaries], simulated: False}`

### Issues Noted

- **Timezone**: Uses UTC (`"Z"` suffix) not vendor's local timezone
- **Binary check**: Any event on the day = entire day unavailable (no time-slot granularity)
- **Fallback**: Always returns "available" if anything fails

## OAuth Flow

```
Vendor visits /api/oauth/calendar/{agent_id}
  → Redirect to Google consent (calendar.readonly + calendar.events scopes)
  → Google callback → exchange_and_store_token
  → Fernet encrypt → store in Firestore agent doc
  → Redirect to frontend with ?calendar=connected
```

## Comparison: GCP vs AWS Calendar Integration

| Aspect | GCP-Hackathon | AWS-Hackathon |
|--------|--------------|---------------|
| Token storage | Firestore (agent doc) | DynamoDB (weddingos-oauth-tokens) |
| Encryption | Fernet | Fernet |
| API call | events.list (UTC) | events.list (Australia/Melbourne TZ) |
| PKCE | No | Yes |
| CSRF protection | state=agent_id | Random UUID in DDB with TTL |
| Gmail integration | No | Yes (unified OAuth) |
| Scopes | calendar.readonly + calendar.events | calendar + gmail.modify + gmail.readonly + userinfo.email |
| Granularity | Whole-day binary | Whole-day binary |
