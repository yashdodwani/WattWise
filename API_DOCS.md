# WattWise — Frontend Integration API Docs

> **Base URL:** `http://localhost:8000`
> **Auth:** All protected endpoints require `Authorization: Bearer <token>` header.
> **Content-Type:** `application/json`

---

## Table of Contents
1. [Authentication](#1-authentication)
2. [Meter](#2-meter)
3. [Appliances](#3-appliances)
4. [Tariffs](#4-tariffs)
5. [Dashboard](#5-dashboard)
6. [Recommendations](#6-recommendations)

---

## 1. Authentication

### POST `/auth/register`
**One-step registration. Returns a JWT immediately — no separate login needed.**

**Request Body:**
```json
{
  "name": "Ravi Kumar",
  "username": "ravikumar",
  "password": "secret123",
  "phone_number": "9876543210",
  "consumer_number": "1234567890"
}
```

**Validations:**
- `username` — min 3 characters, must be unique
- `password` — min 6 characters
- `phone_number` — exactly 10 digits
- `consumer_number` — 10–13 digits

**Response `200`:**
```json
{
  "id": 1,
  "name": "Ravi Kumar",
  "username": "ravikumar",
  "phone_number": "9876543210",
  "consumer_number": "1234567890",
  "created_at": "2026-03-05T10:00:00",
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "message": "Registration successful! You are now logged in."
}
```

---

### POST `/auth/login`
**Login with username + password.**

**Request Body:**
```json
{
  "username": "ravikumar",
  "password": "secret123"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "ravikumar"
}
```

---

### POST `/auth/otp/request`
**Request an OTP for phone-based login.**

**Request Body:**
```json
{
  "phone_number": "9876543210"
}
```

**Response `200`:**
```json
{
  "message": "OTP sent successfully to your phone number",
  "phone_number": "9876543210"
}
```
> ⚠️ In dev mode, OTP is printed to server console. SMS integration is pending.

---

### POST `/auth/otp/verify`
**Verify OTP and receive a JWT token.**

**Request Body:**
```json
{
  "phone_number": "9876543210",
  "otp_code": "482910"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_id": 1,
  "username": "ravikumar"
}
```

---

### GET `/auth/profile` 🔒
**Get the logged-in user's profile.**

**Response `200`:**
```json
{
  "id": 1,
  "name": "Ravi Kumar",
  "username": "ravikumar",
  "phone_number": "9876543210",
  "consumer_number": "1234567890",
  "is_active": true,
  "created_at": "2026-03-05T10:00:00"
}
```

---

### POST `/auth/logout` 🔒
**Logout current user (client should discard the token).**

**Response `200`:**
```json
{
  "message": "Logged out successfully"
}
```

---

## 2. Meter

> All meter endpoints require authentication. Meters are scoped to the logged-in user.

### GET `/meter/readings` 🔒
**Get all meter readings for the current user.**

**Response `200`:**
```json
[
  {
    "id": 1,
    "meter_id": 1,
    "timestamp": "2026-03-05T09:45:00",
    "energy_kwh": 0.35
  }
]
```

---

### GET `/meter/readings/{meter_id}` 🔒
**Get readings for a specific meter (must belong to current user).**

| Param | Type | Description |
|-------|------|-------------|
| `meter_id` | path `int` | Meter ID |

**Response `200`:**
```json
[
  {
    "id": 1,
    "meter_id": 1,
    "timestamp": "2026-03-05T09:45:00",
    "energy_kwh": 0.35
  }
]
```

**Error `403`:** Meter not owned by user.

---

### GET `/meter/today-usage/{meter_id}` 🔒
**Today's total energy usage for a meter.**

**Response `200`:**
```json
{
  "meter_id": 1,
  "date": "2026-03-05",
  "total_energy_kwh": 4.80,
  "reading_count": 32
}
```

---

### GET `/meter/weekly-usage/{meter_id}` 🔒
**Last 7 days' energy summary.**

**Response `200`:**
```json
{
  "meter_id": 1,
  "period": "2026-02-26 to 2026-03-05",
  "total_energy_kwh": 38.40,
  "average_daily_kwh": 5.49,
  "reading_count": 224
}
```

---

### GET `/meter/monthly-usage/{meter_id}` 🔒
**Current month's energy summary.**

**Response `200`:**
```json
{
  "meter_id": 1,
  "period": "March 2026",
  "total_energy_kwh": 24.50,
  "reading_count": 160
}
```

---

## 3. Appliances

> All appliance endpoints require authentication. Appliances are scoped to the logged-in user.

### GET `/appliances/` 🔒
**List all appliances for the current user.**

**Response `200`:**
```json
[
  {
    "id": 1,
    "name": "AC",
    "power_kw": 2.0,
    "status": "ON"
  },
  {
    "id": 2,
    "name": "Washing Machine",
    "power_kw": 0.8,
    "status": "OFF"
  }
]
```

---

### POST `/appliances/{appliance_id}/on` 🔒
**Turn an appliance ON. Records the start time.**

| Param | Type | Description |
|-------|------|-------------|
| `appliance_id` | path `int` | Appliance ID |

**Response `200`:**
```json
{
  "message": "AC turned ON"
}
```

**Response (already on):**
```json
{
  "message": "Already ON"
}
```

**Error `403`:** Appliance not owned by user.

---

### POST `/appliances/{appliance_id}/off` 🔒
**Turn an appliance OFF. Calculates and logs energy used since it was turned ON.**

**Response `200`:**
```json
{
  "message": "AC turned OFF",
  "energy_used_kwh": 0.532
}
```

**Error `403`:** Appliance not owned by user or already OFF.

---

### GET `/appliances/{appliance_id}/usage` 🔒
**Get today's total energy used by a specific appliance.**

**Response `200`:**
```json
{
  "appliance_id": 1,
  "today_usage_kwh": 2.640
}
```

---

## 4. Tariffs

> All tariff endpoints require authentication.

### GET `/tariffs/current` 🔒
**Get the tariff slab active right now (IST).**

**Response `200`:**
```json
{
  "current_price": 6,
  "time_range": "06:00 - 10:00"
}
```

---

### GET `/tariffs/` 🔒
**Get the full tariff schedule ordered by time.**

**Response `200`:**
```json
[
  { "start": "06:00", "end": "10:00", "price": 6 },
  { "start": "10:00", "end": "18:00", "price": 5 },
  { "start": "18:00", "end": "22:00", "price": 8 },
  { "start": "22:00", "end": "06:00", "price": 3 }
]
```

---

### GET `/tariffs/today-cost` 🔒
**Today's electricity bill calculated from actual meter readings × tariff slabs.**

**Response `200`:**
```json
{
  "today_kwh": 14.20,
  "today_cost": 72.35
}
```

---

### POST `/tariffs/simulate` 🔒
**Simulate the cost of running an appliance at a specific time.**

**Request Body:**
```json
{
  "power_kw": 1.5,
  "duration_minutes": 60,
  "start_time": "23:00"
}
```

**Response `200`:**
```json
{
  "energy_used": 1.5,
  "cost": 4.50,
  "price_per_unit": 3
}
```

---

### POST `/tariffs/cheapest-slot` 🔒
**Find the cheapest continuous time window to run an appliance. Supports overnight windows.**

**Request Body:**
```json
{
  "power_kw": 2.0,
  "duration_minutes": 60,
  "window_start": "18:00",
  "window_end": "06:00"
}
```

**Response `200`:**
```json
{
  "recommended_start": "22:15",
  "expected_cost": 3.20,
  "savings_vs_now": 5.70
}
```

---

## 5. Dashboard

> All dashboard endpoints require authentication. Read-only analytics layer.

### GET `/dashboard/summary` 🔒
**Main dashboard cards data.**

**Response `200`:**
```json
{
  "current_load_kw": 1.40,
  "today_kwh": 8.20,
  "predicted_bill": 57.40,
  "active_devices": 3
}
```

| Field | Description |
|-------|-------------|
| `current_load_kw` | Latest meter reading × 4 (15-min → hourly estimate) |
| `today_kwh` | Sum of all readings since midnight IST |
| `predicted_bill` | `today_kwh × ₹7` estimate |
| `active_devices` | Count of appliances currently ON |

---

### GET `/dashboard/consumption` 🔒
**Last 50 meter readings for the consumption graph.**

**Response `200`:**
```json
[
  { "time": "2026-03-05T08:00:00", "kwh": 0.30 },
  { "time": "2026-03-05T08:15:00", "kwh": 0.35 },
  { "time": "2026-03-05T08:30:00", "kwh": 0.28 }
]
```

---

### GET `/dashboard/appliances` 🔒
**Per-appliance energy breakdown for device usage cards.**

**Response `200`:**
```json
[
  {
    "name": "AC",
    "energy_kwh": 1.00,
    "power_kw": 2.0,
    "status": "ON"
  },
  {
    "name": "Washing Machine",
    "energy_kwh": 0.40,
    "power_kw": 0.8,
    "status": "OFF"
  }
]
```
> Runtime is simulated at **0.5 hours** per appliance.

---

### GET `/dashboard/savings` 🔒
**Cost savings achieved by WattWise optimisation.**

**Response `200`:**
```json
{
  "today_cost": 68.00,
  "savings_today": 12.00,
  "efficiency": 68
}
```

| Field | Description |
|-------|-------------|
| `today_cost` | Optimised cost (kWh × ₹6.8) |
| `savings_today` | vs un-optimised (kWh × ₹8) |
| `efficiency` | Fixed score (68%) |

---

### GET `/dashboard/today-cost` 🔒
**Tariff-accurate today's bill using actual tariff slabs.**

**Response `200`:**
```json
{
  "today_kwh": 14.20,
  "today_cost": 72.35
}
```

---

## 6. Recommendations

> Uses sliding-window algorithm to find optimal appliance run times across the full 24-hour tariff schedule.

### GET `/recommendations/` *(No auth required)*
**Best time slot for every appliance (summary list).**

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `duration_minutes` | `int` | `60` | Default run time for all appliances |

**Response `200`:**
```json
[
  {
    "appliance_id": 1,
    "appliance_name": "AC",
    "can_use_now": false,
    "best_slot": "22:15",
    "estimated_cost_inr": 6.00,
    "savings_vs_peak_inr": 8.50,
    "recommendation_message": "Wait until 22:15 to save ₹8.50",
    "reason": "Off-peak tariff ₹3/unit"
  }
]
```

---

### GET `/recommendations/{appliance_id}` *(No auth required)*
**Top N cheapest time slots for one appliance.**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `appliance_id` | path `int` | — | Appliance ID |
| `duration_minutes` | query `int` | `60` | Run time in minutes |
| `top_n` | query `int` (1–10) | `3` | Number of slots to return |

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "appliance_id": 1,
    "appliance_name": "AC",
    "power_kw": 2.0,
    "duration_minutes": 60,
    "current_time_ist": "14:30",
    "current_tariff": 5,
    "current_tod_label": "Normal",
    "can_use_now": false,
    "current_cost_inr": 10.00,
    "best_slot_start": "22:15",
    "best_slot_cost_inr": 6.00,
    "savings_if_you_wait_inr": 4.00,
    "recommendation_message": "Wait until 22:15 to save ₹4.00",
    "top_slots": [
      {
        "rank": 1,
        "start_time": "22:15",
        "end_time": "23:15",
        "slot_label": "22:15 – 23:15",
        "estimated_cost_inr": 6.00,
        "avg_tariff": 3,
        "energy_kwh": 2.0,
        "savings_vs_now_inr": 4.00,
        "is_cheapest": true,
        "reason": "Off-peak tariff ₹3/unit"
      }
    ]
  }
}
```

---

### GET `/recommendations/{appliance_id}/best` *(No auth required)*
**Single best slot with voice-assistant-ready message.**

**Response `200`:**
```json
{
  "success": true,
  "appliance_name": "Washing Machine",
  "can_use_now": false,
  "current_tod_label": "Peak",
  "current_tariff": 8,
  "current_cost_inr": 9.60,
  "best_slot": "22:00",
  "slot_label": "22:00 – 23:00",
  "best_cost_inr": 3.60,
  "savings_vs_now_inr": 6.00,
  "reason": "Off-peak tariff ₹3/unit",
  "voice_message": "Run your Washing Machine at 22:00 to save ₹6.00 compared to running it right now."
}
```

---

### POST `/recommendations/{appliance_id}/compare` *(No auth required)*
**Compare cost of running an appliance at specific user-chosen times.**

**Request Body:**
```json
{
  "duration_minutes": 60,
  "times": ["08:00", "14:00", "22:00"]
}
```

**Response `200`:** Ranked list of the provided times, cheapest first, with savings vs the most expensive option.

---

## Error Reference

| Code | Meaning |
|------|---------|
| `400` | Bad request / validation failed |
| `401` | Missing, invalid or expired token |
| `403` | Resource not owned by current user |
| `404` | Resource not found |

---

## Auth Header Format

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Quick Integration Checklist

- [ ] Register user → store `access_token`
- [ ] Attach token to every request in the `Authorization` header
- [ ] `/dashboard/summary` → top 4 cards
- [ ] `/dashboard/consumption` → line/bar chart
- [ ] `/dashboard/appliances` → device usage cards
- [ ] `/dashboard/savings` → savings widget
- [ ] `/appliances/` → device list with ON/OFF toggles
- [ ] `/appliances/{id}/on` + `/off` → toggle calls
- [ ] `/recommendations/` → recommendation cards
- [ ] `/tariffs/current` → live tariff badge
- [ ] `/tariffs/today-cost` → bill widget

