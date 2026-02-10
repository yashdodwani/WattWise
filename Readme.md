Here’s a **clear, in-depth README.md** written so **you, your teammates, and judges** can understand the project without any prior smart-meter or IoT knowledge.
You can copy-paste this directly.

---

# ⚡ GridFlow — Smart Energy Optimization Super App (PoC)

GridFlow is a **Smart Metering Super App Proof of Concept (PoC)** that helps households **monitor electricity usage, control appliances, and reduce energy bills** by automatically shifting appliance usage to **cheaper Time-of-Day (ToD) tariff periods**.

This project demonstrates how a **single unified platform** can replace multiple fragmented energy and appliance apps, while being scalable for real-world integration with electricity distribution companies (DISCOMs) and smart meters.

---

## 📌 Problem Statement

Modern consumers use:

* One app for electricity meter data
* Separate apps for AC, washing machines, smart plugs
* No single view of energy usage or cost optimization

At the same time:

* Electricity tariffs are becoming **dynamic** (Time-of-Day pricing)
* Users want **lower bills, automation, and sustainability**

**GridFlow solves this by combining:**

* Smart meter–like energy data
* Appliance control and scheduling
* Cost-saving recommendations
* Carbon footprint insights
  into **one simple app**.

---

## 🎯 Objectives

* Provide **real-time energy usage visibility**
* Enable **remote appliance control and scheduling**
* Optimize appliance usage based on **cheapest electricity hours**
* Show **estimated bill savings and CO₂ reduction**
* Demonstrate a **scalable, production-ready architecture**

---

## 🧠 How the System Works (High Level)

1. **Meter Simulator** generates live electricity usage data (every 15 minutes)
2. **Tariff Engine** defines electricity prices for different times of day
3. **Optimizer Service** finds the cheapest time to run appliances
4. **Savings Engine** calculates money and carbon savings
5. **FastAPI Backend** exposes clean APIs
6. **Frontend Dashboard** visualizes data and controls appliances

> ⚠️ Note:
> This PoC uses **simulated smart meter data**.
> In production, this can be replaced with real DISCOM / smart meter APIs.

---

## 🏗️ Backend Architecture

```
backend/
├── main.py                     # FastAPI entry point
│
├── api/                        # HTTP routes (no business logic)
│   ├── meter.py                # Live meter data APIs
│   ├── appliances.py           # Appliance ON/OFF & scheduling
│   ├── tariffs.py              # Time-of-Day tariffs
│   ├── recommendations.py      # Best time & savings
│   └── dashboard.py            # Aggregated dashboard data
│
├── services/                   # Core business logic
│   ├── meter_simulator.py      # Dummy smart meter generator
│   ├── optimizer.py            # Cheapest time calculation
│   ├── savings.py              # Cost & CO₂ calculations
│
├── db/
│   ├── session.py              # PostgreSQL connection
│   ├── models.py               # SQLAlchemy models
│   └── seed.py                 # Dummy seed data
│
├── schemas/                    # Pydantic response schemas
│   ├── meter.py
│   ├── appliance.py
│   ├── recommendation.py
│
├── utils/
│   └── time_slots.py           # 15-minute time slot helpers
│
└── requirements.txt
```

---

## 🔧 Technology Stack

| Layer           | Tech                       |
| --------------- | -------------------------- |
| Backend         | Python, FastAPI            |
| Database        | PostgreSQL                 |
| ORM             | SQLAlchemy                 |
| API Validation  | Pydantic                   |
| Data Simulation | Python background tasks    |
| Frontend        | Web UI (Smart-Flow UI Kit) |

---

## ⚙️ Core Components Explained

### 🔹 1. Smart Meter Simulator

* Generates electricity consumption every **15 minutes**
* Mimics real AMI (Advanced Metering Infrastructure) behavior
* Stores readings in the database

Example:

```
0.18 kWh at 10:00 AM
0.22 kWh at 10:15 AM
```

---

### 🔹 2. Time-of-Day Tariffs

Electricity price varies by time.

Example:

| Time         | Price (₹/unit) |
| ------------ | -------------- |
| 6 AM – 10 AM | 6              |
| 10 AM – 6 PM | 5              |
| 10 PM – 6 AM | 3              |

These tariffs are used by the optimizer.

---

### 🔹 3. Optimization Engine

For each appliance:

* Checks allowed run time
* Calculates cost for every possible time slot
* Picks the **cheapest slot**

Result:

> “Run washing machine at 11:15 PM → save ₹18.5”

No machine learning — just **transparent, explainable logic**.

---

### 🔹 4. Savings & Carbon Calculator

* Cost Savings = price difference × energy usage
* Carbon Savings = energy shifted × emission factor

Example:

```
CO₂ = energy_kwh × 0.82 kg
```

---

### 🔹 5. Appliance Control (Simulated)

* Appliances support:

  * ON / OFF
  * Scheduled runs
* Status is stored and reflected in the dashboard

---

## 🌐 API Overview

### Get live meter data

```
GET /meter/live
```

### Get appliances

```
GET /appliances
```

### Toggle appliance

```
POST /appliances/{id}/toggle
```

### Get best time recommendations

```
GET /recommendations
```

### Schedule appliance

```
POST /appliances/{id}/schedule
```

### Dashboard summary

```
GET /dashboard
```

---

## 📊 Dashboard Features

* Real-time energy usage
* Current electricity price
* Appliance status
* Recommended run times
* Estimated bill savings
* Carbon footprint reduction

---

## 🧪 Dummy Data & Seeding

The project includes seed data for:

* Users
* Appliances
* Tariff schedules

This allows the app to run **immediately without setup**.

---

## 🔐 Security & Privacy (PoC Scope)

* No personal data exposed
* All data is local and simulated
* Architecture supports:

  * Secure APIs
  * Role-based access
  * Encryption (future)

---

## 🚀 Future Scope (Post-Hackathon)

* Real smart meter integration (DISCOM MDMS / HES)
* Industry protocols (DLMS/COSEM)
* Demand response automation
* AI-based consumption prediction
* Voice assistant integration
* Multi-household scaling

---

## 🏁 Success Metrics (Demo Targets)

* Appliance onboarding in under **5 minutes**
* Control at least **3 appliances**
* Show **10–15% bill savings**
* Real-time control reliability
* Visible CO₂ reduction per household

---

## 🧠 Why This Matters

GridFlow empowers consumers to:

* Understand electricity usage
* Save money automatically
* Reduce environmental impact
* Move toward smarter, sustainable energy consumption

---

