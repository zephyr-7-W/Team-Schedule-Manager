# API Reference

Base URL: `http://127.0.0.1:8001` (the port the frontend dev proxy expects).
All request and response bodies are JSON.

Interactive documentation is served by FastAPI at `/docs` (Swagger UI) and
`/redoc`.

Error responses use FastAPI's standard shape and a `4xx` status:

```json
{ "detail": "日程标题不能为空" }
```

Literal field values and error strings returned by the API are in Chinese,
matching the UI. Descriptions here are in English.

---

## Health

### `GET /api/health`

Response `200`:

```json
{ "status": "ok" }
```

---

## Members

### `GET /api/users`

List all members, ordered by `id`.

Response `200`:

```json
[
  { "id": 1, "name": "张三", "role": "产品经理", "color": "#5470c6" }
]
```

### `POST /api/users`

Create a member.

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `name` | string | yes | 1-30 characters, must be unique |
| `role` | string | no | up to 50 characters, defaults to `""` |
| `color` | string | no | hex colour, defaults to `#5470c6` |

Response `201` with the created member. Returns `400` if the name already exists.

### `GET /api/users/{user_id}`

Fetch a single member. Returns `404` if the member does not exist.

### `DELETE /api/users/{user_id}`

Delete a member. The member's schedules are removed, along with every schedule
sharing a `shared_id` with one of them. Returns `404` if the member does not
exist.

Response `200`:

```json
{ "ok": true }
```

### `GET /api/users/{user_id}/schedules`

Schedules owned by one member.

| Query | Type | Required | Description |
| --- | --- | --- | --- |
| `date` | string | no | `YYYY-MM-DD`; when omitted, returns all dates |

Response `200` is an array of [schedule objects](#schedule-object). Returns `400`
on a malformed date and `404` if the member does not exist.

### `POST /api/users/{user_id}/schedules/share`

Render a member's day as a plain-text digest and dispatch it to the chosen
channel.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `date` | string | yes | `YYYY-MM-DD` |
| `channel` | string | no | `internal` (default), `feishu`, or `dingtalk` |
| `message` | string | no | Free-text line appended to the digest |

Response `200`:

```json
{
  "ok": true,
  "channel": "internal",
  "message": "分享内容已生成，可复制转发给同事",
  "content": "【2026-09-22】张三 的日程\n09:30-10:15  每日站会  @会议室 A",
  "payload": {
    "channel": "internal",
    "code": "OK",
    "delivered": true,
    "action": "internal_share",
    "note": "分享内容已生成，可直接复制转发",
    "content": "【2026-09-22】张三 的日程\n09:30-10:15  每日站会  @会议室 A"
  }
}
```

Returns `400` for an unsupported `channel` or a malformed `date`.

---

## Schedules

### `GET /api/schedules`

Schedules for a date, across all members unless filtered.

| Query | Type | Required | Description |
| --- | --- | --- | --- |
| `date` | string | no | `YYYY-MM-DD`; defaults to today |
| `user_id` | integer | no | Restrict to one member |

Response `200` is an array of [schedule objects](#schedule-object).

### `POST /api/schedules`

Create a schedule. When `participants` contains extra member IDs, one linked row
is created per participant under a fresh `shared_id`, and the response returns
the row belonging to `user_id`.

| Field | Type | Required | Default |
| --- | --- | --- | --- |
| `user_id` | integer | yes | - |
| `title` | string | yes | - (1-100 characters) |
| `date` | string | yes | `YYYY-MM-DD` |
| `start_time` | string | yes | `HH:MM` |
| `end_time` | string | yes | `HH:MM`, must be after `start_time` |
| `location` | string | no | `""` |
| `note` | string | no | `""` |
| `category` | string | no | `其他` |
| `recurrence` | string | no | `none` |
| `participants` | integer[] | no | `[]` |
| `reminder` | integer | no | `10` |

Response `201` with the created [schedule object](#schedule-object). Returns
`400` when validation fails, for example an empty title, a malformed date, a
`start_time` that is not before `end_time`, or an unknown member ID.

### `PUT /api/schedules/{id}`

Partial update. Only the fields present in the body are changed; accepted fields
are the same as for creation. When the row belongs to a shared group, the
updates propagate to every row in that group, except `user_id`, which moves only
the addressed row.

Response `200` with the updated [schedule object](#schedule-object). Returns
`400` if the schedule does not exist.

### `DELETE /api/schedules/{id}`

Delete a schedule. If it belongs to a shared group, every row in that group is
deleted.

Response `200`:

```json
{ "ok": true }
```

Returns `400` if the schedule does not exist.

### `POST /api/schedules/{id}/share`

Share a single schedule as text.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `channel` | string | no | `internal` (default), `feishu`, or `dingtalk` |
| `message` | string | no | Free-text line appended to the digest |

Responds with the same envelope as the member-day share endpoint above.

### Schedule object

```json
{
  "id": 3,
  "user_id": 3,
  "title": "后端联调",
  "date": "2026-09-22",
  "start_time": "10:00",
  "end_time": "12:00",
  "location": "线上",
  "note": "",
  "source": "manual",
  "category": "开发",
  "recurrence": "none",
  "participants": [3, 2],
  "reminder": 10,
  "shared_id": "6f1c9a2b8d4e4f0a9c3b5d7e8f1a2b3c",
  "user": {
    "id": 3,
    "name": "王五",
    "role": "后端开发",
    "color": "#fac858"
  }
}
```

`source` is `manual` for rows created through the API and `seed` for the demo
data written on first start. `shared_id` is empty for non-shared schedules.

---

## AI

### `POST /api/ai/parse`

Parse one sentence into a structured schedule, then check the candidate slot for
conflicts.

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `text` | string | yes | 1-500 characters |

Example request:

```json
{ "text": "明天下午3点到4点 王五 和后端对接口" }
```

Response `200`:

```json
{
  "schedule": {
    "user_id": 3,
    "user_name": "王五",
    "title": "和后端对接口",
    "date": "2026-09-23",
    "start_time": "15:00",
    "end_time": "16:00",
    "location": "",
    "note": "",
    "source": "local"
  },
  "conflicts": [],
  "message": "未配置 LLM_API_KEY，已使用本地规则解析",
  "source": "local"
}
```

- `source` is `llm` when the configured model answered, and `local` when the
  rule-based parser was used. An LLM failure silently degrades to `local`.
- Any field the parser could not determine is `null`; the UI asks you to fill it
  in before saving.
- `conflicts` lists overlapping schedules for the same member and day. The
  candidate is not saved automatically; `POST /api/schedules` does that.

---

## Integrations

These endpoints are placeholders. They validate the channel and return a stub
payload without contacting Feishu or DingTalk.

`{channel}` must be `feishu` or `dingtalk`; anything else returns `404`.

### `GET /api/integration/{channel}/status`

```json
{
  "channel": "feishu",
  "status": "placeholder",
  "note": "[占位] 待接入 feishu 开放平台"
}
```

### `POST /api/integration/{channel}/messages/push`

| Field | Type | Required |
| --- | --- | --- |
| `content` | string | no, defaults to `""` |

```json
{
  "channel": "feishu",
  "code": "PLACEHOLDER",
  "delivered": false,
  "action": "message_push",
  "note": "[占位] 已预留接口，未接入真实 feishu 业务",
  "content": "hello"
}
```

### `POST /api/integration/{channel}/org/sync`

```json
{
  "channel": "dingtalk",
  "code": "PLACEHOLDER",
  "delivered": false,
  "action": "org_sync",
  "note": "[占位] 已预留接口，未接入真实 dingtalk 业务",
  "content": { "synced_members": 0 }
}
```

To implement either integration, replace the bodies in
`backend/app/services/integration_service.py`, where the TODO comments mark the
intended extension points.