# Gear API – FE AI Agent

**Base URL:** `{API_BASE}/api`  
**Auth:** All endpoints require `Authorization: Bearer <JWT>`

---

## List Gear

**`GET /api/gear`**

Lists the current user's gear. Optional query params: `activity_type`, `gear_type`. Each item includes `components_count` (number of currently installed components; 0 for components, since they cannot have children).

**Example:** `GET /api/gear?activity_type=bike&gear_type=component`

**Response (200):**
```json
{
  "success": true,
  "gear": [
    {
      "id": 5,
      "activity_type": "bike",
      "gear_type": "bike",
      "brand": "Trek",
      "model": "Domane",
      "nick": "Road bike",
      "metric_type": "distance",
      "max_value": null,
      "value_covered": 1200,
      "is_default": true,
      "status": "active",
      "created_at": "2026-03-11T10:00:00",
      "components_count": 2
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `components_count` | Number of components currently installed on this gear (0 for components; shoes and bikes can have components) |

---

## Get Gear

**`GET /api/gear/:id`**

Returns a single gear with `installations` and `services`.

**Response (200):**
```json
{
  "success": true,
  "gear": {
    "id": 12,
    "activity_type": "bike",
    "gear_type": "component",
    "brand": "Shimano",
    "model": "HG-11",
    "nick": "Chain",
    "metric_type": "distance",
    "max_value": 3000,
    "value_covered": 1200,
    "is_default": false,
    "status": "active",
    "created_at": "2026-03-11T10:00:00",
    "installations": [
      {
        "id": 2,
        "parent_gear_id": 5,
        "installed_at": "2026-03-10T09:00:00",
        "removed_at": null
      }
    ],
    "services": [
      {
        "id": 3,
        "name": "Chain replacement",
        "interval_value": 3000,
        "interval_unit": "km",
        "early_warning_ratio": 0.8,
        "last_performed_value": 1200
      }
    ]
  }
}
```

---

## List Parent Gear Components

**`GET /api/gear/:id/components`**

Returns components currently installed on this parent gear. Only valid for parent gear (`gear_type` `shoe` or `bike`). Components cannot have child components (one level of hierarchy only).

**Example:** `GET /api/gear/5/components` (for a bike with id 5)

**Response (200):**
```json
{
  "success": true,
  "components": [
    {
      "id": 12,
      "activity_type": "bike",
      "gear_type": "component",
      "brand": "Shimano",
      "model": "HG-11",
      "nick": "Chain",
      "metric_type": "distance",
      "max_value": 3000,
      "value_covered": 1200,
      "is_default": false,
      "status": "active",
      "created_at": "2026-03-11T10:00:00",
      "installation_id": 2,
      "installed_at": "2026-03-10T09:00:00"
    },
    {
      "id": 13,
      "activity_type": "bike",
      "gear_type": "component",
      "brand": "Continental",
      "model": "GP 5000",
      "nick": "Rear tire",
      "metric_type": "distance",
      "max_value": 5000,
      "value_covered": 800,
      "is_default": false,
      "status": "active",
      "created_at": "2026-03-11T10:00:00",
      "installation_id": 3,
      "installed_at": "2026-03-09T14:00:00"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `installation_id` | ID of the installation record (use with `DELETE /api/gear/:child_id/installations/:installation_id` to detach) |
| `installed_at` | When the component was attached to this parent |

**Errors:**
- `404` – Gear not found
- `400` – Gear is a component (components cannot have children)

---

## Create Gear

**`POST /api/gear`**

Creates a new gear item. For components, you can link to a parent in the same request.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `brand` | string | **Yes** | Brand name |
| `model` | string | **Yes** | Model name |
| `activity_type` | string | No | `run`, `bike`, `swim`, `other` (default: `run`) |
| `gear_type` | string | No | `shoe`, `bike`, `component` (default: `shoe`) |
| `nick` | string | No | User nickname |
| `metric_type` | string | No | `distance`, `hours`, `sessions` (default: `distance`) |
| `max_value` | number | No | Max value before alert (e.g. 500 km for shoes) |
| `value_covered` | number | No | Initial value (e.g. existing mileage) |
| `parent_gear_id` | integer | No | **Component only.** Links component to parent gear in one request. Omit for shoe/bike. |

### Examples

**Create a shoe:**
```json
{
  "brand": "Nike",
  "model": "Pegasus 40",
  "activity_type": "run",
  "gear_type": "shoe",
  "nick": "Daily trainers",
  "max_value": 500,
  "value_covered": 0
}
```

**Create a component and link to parent bike:**
```json
{
  "brand": "Shimano",
  "model": "HG-11",
  "activity_type": "bike",
  "gear_type": "component",
  "nick": "Chain",
  "metric_type": "distance",
  "max_value": 3000,
  "parent_gear_id": 5
}
```

### Validation (parent_gear_id)

- Parent must exist and belong to the user
- Parent must not be a component (only one level of hierarchy)
- Gear cannot be its own parent
- Only applies when `gear_type` is `component`

### Response (201)

```json
{
  "success": true,
  "gear": {
    "id": 12,
    "activity_type": "bike",
    "gear_type": "component",
    "brand": "Shimano",
    "model": "HG-11",
    "nick": "Chain",
    "metric_type": "distance",
    "max_value": 3000,
    "value_covered": 0,
    "is_default": false,
    "status": "active",
    "created_at": "2026-03-11T10:00:00"
  }
}
```

To get installations (including the new link), use `GET /api/gear/:id`.

---

## Update Gear

**`PUT /api/gear/:id`**

Updates gear fields. For components, you can change the parent (or detach) in the same request.

### Request Body

All fields are optional. Only included fields are updated.

| Field | Type | Description |
|-------|------|-------------|
| `activity_type` | string | `run`, `bike`, `swim`, `other` |
| `gear_type` | string | `shoe`, `bike`, `component` |
| `brand` | string | Brand name |
| `model` | string | Model name |
| `nick` | string | User nickname |
| `metric_type` | string | `distance`, `hours`, `sessions` |
| `max_value` | number | Max value before alert; `null` to clear |
| `value_covered` | number | Manual total (affects gear total) |
| `parent_gear_id` | integer \| null | **Component only.** `5` = link to gear 5; `null` = detach from current parent. Omit = no change. |

### Examples

**Update basic fields:**
```json
{
  "nick": "Race shoes",
  "max_value": 400
}
```

**Link component to a different parent:**
```json
{
  "parent_gear_id": 7
}
```

**Detach component from parent:**
```json
{
  "parent_gear_id": null
}
```

### Validation (parent_gear_id)

Same as create: parent must exist, must not be a component, gear cannot be its own parent. Only applies when the gear’s `gear_type` is `component`.

### Response (200)

```json
{
  "success": true,
  "gear": {
    "id": 12,
    "activity_type": "bike",
    "gear_type": "component",
    "brand": "Shimano",
    "model": "HG-11",
    "nick": "Chain",
    "metric_type": "distance",
    "max_value": 3000,
    "value_covered": 150,
    "is_default": false,
    "status": "active",
    "created_at": "2026-03-11T10:00:00"
  }
}
```

---

## Default Gear

### Set default

**`PUT /api/gear/:id/default`**

Marks this gear as the default for **its current `activity_type`**. Any other gear for the same user and same `activity_type` has `is_default` cleared. **No request body.**

Use when the user sets “default” in the UI. This is **not** done via `PUT /api/gear/:id` (update gear does not accept `is_default`).

**Response (200):** Same shape as below; returned gear has `"is_default": true`.

### Clear default

**`DELETE /api/gear/:id/default`**

Sets **`is_default`** to **`false`** on this gear if it was set. **No request body.** Idempotent: if this gear was not default, responds **200** with the current gear unchanged.

After this call, that user may have **no** default gear for this gear’s `activity_type` (until they call **`PUT /api/gear/:id/default`** on some gear again).

**Response (200):**

```json
{
  "success": true,
  "gear": {
    "id": 12,
    "activity_type": "run",
    "gear_type": "shoe",
    "brand": "Nike",
    "model": "Pegasus",
    "nick": null,
    "metric_type": "distance",
    "max_value": 800,
    "value_covered": 120.5,
    "is_default": false,
    "status": "active",
    "created_at": "2026-03-11T10:00:00"
  }
}
```

### Errors

- **404** — Gear not found or not owned by the user: `{"success": false, "error": "Gear not found"}`

---

## Delete Gear

**`DELETE /api/gear/:id`**

Deletes gear and all related data (installations, services, usage).

**Response (200):**
```json
{
  "success": true
}
```

---

## Gear Services API

Service intervals let you define maintenance schedules (e.g. "Chain replacement every 3000 km"). Alerts fire when usage exceeds the interval (overdue) or reaches the early-warning threshold.

### List Services

**`GET /api/gear/:id/services`**

Returns all service schedules for the gear.

**Response (200):**
```json
{
  "success": true,
  "services": [
    {
      "id": 3,
      "name": "Chain replacement",
      "interval_value": 3000,
      "interval_unit": "km",
      "early_warning_ratio": 0.8,
      "last_performed_value": 1200
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `id` | Service ID |
| `name` | User-defined name (e.g. "Chain replacement", "Tire change") |
| `interval_value` | Interval value (e.g. 3000 for km) |
| `interval_unit` | Unit: `km`, `miles`, `hours`, `sessions` |
| `early_warning_ratio` | Ratio for early warning (e.g. 0.8 = warn at 80% of interval) |
| `last_performed_value` | Gear `value_covered` when service was last performed |

---

### Create Service

**`POST /api/gear/:id/services`**

Creates a service schedule for the gear.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Service name (e.g. "Chain replacement") |
| `interval_value` | number | **Yes** | Interval (e.g. 3000 for km) |
| `interval_unit` | string | No | `km`, `miles`, `hours`, `sessions` (default: `km`) |
| `early_warning_ratio` | number | No | Warn at this fraction of interval (e.g. 0.8 = 80%) |

**Example:**
```json
{
  "name": "Chain replacement",
  "interval_value": 3000,
  "interval_unit": "km",
  "early_warning_ratio": 0.8
}
```

**Response (201):**
```json
{
  "success": true,
  "service": {
    "id": 3,
    "name": "Chain replacement",
    "interval_value": 3000,
    "interval_unit": "km",
    "early_warning_ratio": 0.8,
    "last_performed_value": null
  }
}
```

---

### Update / Edit Service

**`PUT /api/gear/:id/services/:service_id`**

Updates a service schedule. All fields are optional.

**Request Body:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Service name |
| `interval_value` | number | Interval value |
| `interval_unit` | string | `km`, `miles`, `hours`, `sessions` |
| `early_warning_ratio` | number \| null | Warn at fraction of interval; `null` to clear |

**Example:**
```json
{
  "name": "Chain replacement",
  "interval_value": 3500,
  "early_warning_ratio": 0.85
}
```

**Response (200):** Same structure as create.

---

### Delete Service

**`DELETE /api/gear/:id/services/:service_id`**

Deletes a service schedule. Service logs are removed with it.

**Response (200):**
```json
{
  "success": true
}
```

---

### Log Service Performed

**`POST /api/gear/:id/services/:service_id/logs`**

Marks a service as performed. Sets `last_performed_value` to the gear’s current `value_covered`.

**Request Body:** None (empty `{}` or omit).

**Response (200):**
```json
{
  "success": true,
  "log": {
    "id": 7,
    "performed_at": "2026-03-11T14:30:00",
    "value_at_perform": 1200
  }
}
```

---

### Alerts

**`GET /api/gear/alerts`**

Returns gear alerts (max value exceeded, service overdue or due soon). Use this to show warnings in the UI.

**Response (200):**
```json
{
  "success": true,
  "alerts": [
    {
      "gear_id": 5,
      "type": "max_value",
      "message": "Max value exceeded"
    },
    {
      "gear_id": 8,
      "service_id": 3,
      "type": "service_overdue",
      "message": "Service 'Chain replacement' overdue"
    },
    {
      "gear_id": 8,
      "service_id": 3,
      "type": "service_warning",
      "message": "Service 'Chain replacement' due soon"
    }
  ]
}
```

---

## Activity API – Create, Get & Edit

### Create Activity

**`POST /api/activities`**

Creates an activity. Supports run, bike, swim, other. Optionally auto-adds default gear for the activity type.

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Activity name |
| `date` | string (ISO 8601) | **Yes** | Date, e.g. `2026-03-11` |
| `activity_type` | string | No | `run`, `bike`, `swim`, `other` (default: `run`) |
| `total_distance_km` | number | No | Distance in km (default: 0) |
| `total_hours` | number | No | Duration in hours (for bike/swim) |
| `total_sessions` | number | No | Number of sessions (e.g. for swim) |
| `auto_add_default_shoe` | boolean | No | Auto-add default gear for activity type (default: `true`) |

**Example – run:**
```json
{
  "name": "Morning run",
  "date": "2026-03-11",
  "activity_type": "run",
  "total_distance_km": 10,
  "auto_add_default_shoe": true
}
```

**Example – bike:**
```json
{
  "name": "Long ride",
  "date": "2026-03-11",
  "activity_type": "bike",
  "total_distance_km": 80,
  "total_hours": 3.5,
  "auto_add_default_shoe": true
}
```

**Example – swim:**
```json
{
  "name": "Pool session",
  "date": "2026-03-11",
  "activity_type": "swim",
  "total_hours": 1,
  "total_sessions": 20,
  "auto_add_default_shoe": true
}
```

**Response (201):** Activity with `shoes`, `gear`, `total_hours`, `total_sessions`.

**Auto-add default gear:** Uses the default gear for the given `activity_type`. For run, value = `total_distance_km`. For bike/swim/other, value = `total_hours` or `total_distance_km`. Only adds if user has a default gear for that type.

---

### Get Activity

**`GET /api/activities/:id`**

Returns activity detail with `shoes` and `gear`. For parent gear (shoe, bike), each item includes `active_component_ids` and `excluded_component_ids` so you can show which components are active (receive usage) vs inactive (excluded) for this activity.

**Response (200):**
```json
{
  "success": true,
  "activity": {
    "id": 1,
    "name": "Morning ride",
    "date": "2026-03-11",
    "total_distance_km": 50,
    "total_hours": null,
    "total_sessions": null,
    "activity_type": "bike",
    "source": "manual",
    "strava_activity_id": null,
    "created_at": "2026-03-11T10:00:00",
    "shoes": [],
    "gear": [
      {
        "gear_id": 5,
        "value": 50,
        "active_component_ids": [10, 11],
        "excluded_component_ids": [12]
      },
      {
        "gear_id": 10,
        "value": 50
      },
      {
        "gear_id": 11,
        "value": 50
      }
    ]
  }
}
```

| Field | Description |
|-------|-------------|
| `gear` | All gear in activity. Parent gear has `active_component_ids` and `excluded_component_ids`. Components appear as flat `{gear_id, value}` entries. |
| `active_component_ids` | Component IDs that receive usage from this activity (parent gear only) |
| `excluded_component_ids` | Component IDs installed on parent but excluded from this activity (do not receive usage) |

**Component status:**
- **Active** = in `active_component_ids` (or appears as separate gear entry) → receives usage
- **Inactive** = in `excluded_component_ids` → does not receive usage

---

### Edit Activity – Basic Fields

**`PUT /api/activities/:id`**

Updates name, date, activity_type, total_distance_km, total_hours, total_sessions. Does not change gear.

**Request Body:** All fields optional.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Activity name |
| `date` | string (ISO 8601) | Date |
| `activity_type` | string | `run`, `bike`, `swim`, `other` |
| `total_distance_km` | number | Distance in km |
| `total_hours` | number | Duration in hours |
| `total_sessions` | number | Number of sessions |

**Example:**
```json
{
  "name": "Updated ride",
  "date": "2026-03-11",
  "activity_type": "bike",
  "total_distance_km": 55,
  "total_hours": 3.2
}
```

---

### Edit Activity – Gear & Component Active/Inactive

**`PUT /api/activities/:id/gear`**

Assigns gear to the activity. Use `excluded_component_ids` to **deactivate** components; omit or remove from `excluded_component_ids` to **activate** them.

**Request Body:** Array of `{ gear_id, value?, excluded_component_ids? }`

| Field | Type | Description |
|-------|------|-------------|
| `gear_id` | integer | **Required.** Parent gear ID (shoe, bike). |
| `value` | number | Usage value. Optional when 1 gear; required when 2+ (sum must equal activity total). |
| `excluded_component_ids` | array | **Deactivate** these components for this activity. Omit or use `[]` to activate all. |

**Activate component:** Remove its ID from `excluded_component_ids` (or send `excluded_component_ids: []` to activate all).

**Deactivate component:** Add its ID to `excluded_component_ids`.

**Example – bike with chain (10) and tires (11) active, cassette (12) excluded:**
```json
[
  {
    "gear_id": 5,
    "value": 50,
    "excluded_component_ids": [12]
  }
]
```

**Example – activate all components (no exclusions):**
```json
[
  {
    "gear_id": 5,
    "value": 50,
    "excluded_component_ids": []
  }
]
```

**Example – deactivate chain and cassette:**
```json
[
  {
    "gear_id": 5,
    "value": 50,
    "excluded_component_ids": [10, 12]
  }
]
```

**Response (200):** Same structure as GET activity (includes `gear` with `active_component_ids` and `excluded_component_ids`).

---

## Summary

**Gear CRUD:** `GET /api/gear` (list), `GET /api/gear/:id` (get), `POST /api/gear` (create), `PUT /api/gear/:id` (update/edit), `PUT /api/gear/:id/default` / `DELETE /api/gear/:id/default` (set or clear default for this gear; no body), `DELETE /api/gear/:id` (delete gear)

**Parent gear components:** `GET /api/gear/:id/components` – list components installed on a parent gear (shoe/bike)

**Component linking (parent_gear_id):**

| Action | API | Use `parent_gear_id`? |
|--------|-----|------------------------|
| Create component + link | `POST /api/gear` | `parent_gear_id: 5` |
| Create component standalone | `POST /api/gear` | Omit or use `POST /api/gear/:id/installations` later |
| Update component → new parent | `PUT /api/gear/:id` | `parent_gear_id: 7` |
| Detach component | `PUT /api/gear/:id` | `parent_gear_id: null` |
| Link existing component | `POST /api/gear/:id/installations` | Body: `{ "parent_gear_id": 5 }` |
| Detach via installations | `DELETE /api/gear/:id/installations/:installation_id` | — |

**Services:** `GET /api/gear/:id/services` (list), `POST /api/gear/:id/services` (create), `PUT /api/gear/:id/services/:service_id` (edit), `DELETE /api/gear/:id/services/:service_id` (delete), `POST /api/gear/:id/services/:service_id/logs` (log performed)

**Component rule:** A component can only be attached to one parent at a time. Setting a new `parent_gear_id` detaches it from the previous parent.

**Activity:** `POST /api/activities` (create; supports activity_type run/bike/swim/other), `GET /api/activities/:id` (includes gear with active/excluded component IDs), `PUT /api/activities/:id` (basic fields), `PUT /api/activities/:id/gear` (assign gear; use `excluded_component_ids` to deactivate components)
