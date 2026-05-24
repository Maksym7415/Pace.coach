# Adaptive AI Endurance Coaching Platform — MVP PRD / Technical Specification

## 1. Product Vision

Build a multi-athlete endurance coaching platform with:

- coach and athlete roles
- adaptive training planning
- recovery-aware workout adjustments
- AI-assisted coaching
- Strava/FIT integrations

The system should focus on endurance sports (initially running), but architecture should support future extension to cycling, triathlon, etc.

### Core philosophy

- Training plans are living adaptive systems
- AI assists coaching decisions, but does not fully own training logic
- Athlete owns their account and historical data
- Coach operates on top of athlete state/history

---

## 2. Core Concepts

### 2.1 Athlete Ownership Model

Athlete is the primary entity.

Athlete owns:

- Workouts
- Training history
- Recovery data
- AI context/history
- Race history
- Performance metrics

Coach:

- Receives access to athlete
- Can manage plans/workouts
- Can add notes and modifications
- Can be removed/replaced

Future support:

- Multiple coaches per athlete
- Different coach roles

---

## 3. Roles

### 3.1 Athlete

Capabilities:

- Manage own profile
- Connect Strava
- Upload FIT files
- View calendar/workouts
- Log recovery metrics
- Communicate with AI assistant
- View history/progress
- Accept/decline coach invitations

---

### 3.2 Coach

Capabilities:

- Create/manage athletes
- Send athlete invitations
- Build training cycles
- Create/edit workouts
- Monitor recovery metrics
- Monitor training load
- Override/adapt workouts
- Interact with AI assistant
- View dashboards/alerts

---

## 4. MVP Functional Scope

### 4.1 Authentication

Required:

- Email/password auth
- Optional OAuth later

Entities:

- User
- Role (coach/athlete)

A single user may potentially have both roles in future.

---

## 5. Athlete ↔ Coach Relationship System

### 5.1 Invitation Flow

Coach can:

- Search athlete by nickname/email
- Send invitation

Athlete can:

- Accept invitation
- Reject invitation

After acceptance:

- Coach gains access to athlete workspace

---

### 5.2 Relationship Entity

**CoachAthleteRelation**

Fields:

- id
- coach_id
- athlete_id
- status
- permissions
- created_at

Statuses:

- pending
- active
- revoked
- rejected

---

## 6. Training Planning System

### 6.1 Training Hierarchy

Supports:

#### Macrocycle

- Goal
- Target race
- Start date
- End date
- Philosophy

#### Mesocycle

- Base
- Build
- Peak
- Taper

#### Microcycle

- Weekly structure
- Daily workouts

---

## 7. Workout Builder

### Workout Types

- Easy
- Recovery
- Long run
- Threshold
- Intervals
- Hills
- Race pace
- Rest day

---

### Workout Structure (example)

```json
{
  "type": "interval",
  "title": "6x800m @5k pace",
  "steps": [
    {
      "type": "warmup",
      "duration_min": 15
    },
    {
      "type": "repeat",
      "repeats": 6,
      "distance_m": 800
    },
    {
      "type": "recovery",
      "duration_min": 2
    },
    {
      "type": "cooldown",
      "duration_min": 10
    }
  ]
}
```

---

## 8. Recovery System

### Inputs

#### Objective

- HRV
- Body Battery
- Resting HR

#### Subjective

- Fatigue (1–10)
- Soreness (1–10)
- Mood (1–10)
- Sleep quality

---

### Logic

- Compute readiness score
- Detect fatigue trends
- Adjust load

Example rule:

```
if HRV ↓ + fatigue ↑ → reduce intensity
```

---

## 9. Training Adaptation Engine

### Principles

- Plans are NOT static
- Macrocycle is preserved
- Only execution layer adapts

### Examples

- Replace intervals with easy run if recovery low
- Increase load if adaptation positive

---

## 10. AI Layer

### AI SHOULD

- Explain decisions
- Summarize athlete state
- Assist coach
- Detect patterns
- Suggest adjustments

### AI SHOULD NOT

- Design full training cycles
- Override system logic

---

## 11. Integrations

### Strava API

- Import activities
- Sync workouts

### FIT file upload

- Garmin / COROS / Suunto / Wahoo support

---

## 12. Athlete UX

- Today workout view
- Readiness display
- Calendar
- Recovery input form
- AI assistant chat

---

## 13. Coach Dashboard

- Athlete overview
- Readiness monitoring
- Training cycle builder
- Workout editor
- AI assistant

---

## 14. Domain Model

Entities:

- User
- Athlete
- Coach
- CoachAthleteRelation
- TrainingPlan
- Macrocycle
- Mesocycle
- Microcycle
- Workout
- WorkoutStep
- RecoveryEntry
- Activity
- AIConversation

---

## 15. Non-goals

- Garmin write integration (initially)
- Wearable live sync
- ML-heavy models
- Social network features
- Payments (initially)

---

## 16. Key Differentiators

- Adaptive training system (not static plans)
- Coach OS (not just app)
- Athlete-owned data graph
- AI coaching layer (explanations + insights)

---

## 17. Success Criteria

- Coaches can manage athletes easily
- Athletes follow adaptive plans
- Recovery affects training decisions
- AI improves coaching clarity
- System feels better than spreadsheets/manual tools

