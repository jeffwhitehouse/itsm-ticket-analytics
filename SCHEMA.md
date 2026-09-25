# Normalized ticket schema

One CSV row per ticket, UTF-8, header row required. The adapters in `adapters/` produce this from
Freshservice and ServiceDesk Plus API exports; anything else just needs a small mapping script.

| Column | Required | Notes |
|---|---|---|
| `system` | | Source system label, e.g. `Freshservice`. Lets you mix exports across a migration. |
| `id` | | Display id. |
| `created` | yes | Local time, `YYYY-MM-DD HH:MM:SS` (ISO `T` separator also accepted). |
| `first_responded` | | Same format. Empty if unknown. |
| `resolved` | | Resolved or closed time. Empty = still open. |
| `status` | | Free text. `Closed`/`Resolved`/`Cancelled` count as not open. |
| `technician` | | Assignee at close. Aliases are normalized via `technician_aliases` in the config. |
| `group` | | Queue / group name. |
| `requester`, `requester_email` | `requester_email` yes | The sender address drives stream detection (machine mail vs people). |
| `subject` | yes | |
| `description` | | Plain text; the first ~800 chars are used for fallback classification. |
| `is_overdue`, `is_fr_overdue` | | `true`/`false`. |

Times should already be in the helpdesk's local time zone (the adapters convert with `--tz`), so
hour-of-day and business-day numbers mean what people expect.
