# AI Agent – Planning Gear Tracker Extension

## Goal

Plan the extension of the existing **running shoe tracker** into a **universal gear tracker** for multiple sports, including components, service intervals, and usage history. Focus is on **planning tasks, dependencies, priorities, and architecture**, not implementation.

---

## 1. Activity Categories Planning

- Current system only tracks running shoes.
- Plan to extend to multiple activity types:
  - run
  - bike
  - swim
  - other
- Consider mapping gear types to activities.
- Decide whether to modify `shoes` table or create generalized `gear` table for planning purposes.

---

## 2. Gear Hierarchy / Components

### Planning Considerations

- Some gear is a parent (bike) and some are child components (cassette, chain, tires).
- Components may move between parents over time — need **installation history**.
- Only one active installation per component at a time.
- Plan usage propagation: parent activity → all active components.
- Enforce metric type consistency between parent and child.
- Only 1 level of hierarchy allowed(bike → chain).
- Component can be attached to multiple parents
- Can we consider adding component in activity with bike2 which assigned to bike1? How better to handle this?
- Components can have independent `max_value`. Inherit from parent by default. Similar to what we have with shoes now where we have sum of all activities + 1 manual distance row record in activity_shoe_distance table per each gear
- components without a parent can be manually added in any activity and should behave same way as parent components. in other workds component is not a component until attached to any parent
- Child gear should have its own service intervals

---

## 3. Gear Retirement Planning

- Gear can be retired: inactive for future activities, but history remains.
- component can be removed from parent which should keep covered distance.
- Determine how retirement affects service intervals, active installations, and historical activities.

---

## 4. Service / Maintenance Intervals

### Planning Considerations

- Service schedules tied to gear:
  - Name
  - Interval (distance, hours, sessions)
  - Early warning threshold
  - Last performed value
- Gear usage updates service status.
- Service logs for history and analytics.
- Plan flexible service types per gear.

### Questions for Planning

- Should service intervals be additive or separate (distance vs. hours)?
- Should services propagate to components automatically?
- How to represent complex chains (e.g., chain cleaning vs. replacement)?

---

## 5. Metric Types Planning

- Decide supported metric types: distance, hours, sessions.
- Ensure child gear matches parent metric.
- Plan defaults per gear type (e.g., running shoes = distance, wetsuit = hours).
- Consider future expansion to hybrid metrics.
- plan adding km/miles in profile. how this will affect all distance data?

---

## 6. Max Value / Alerts Planning

- Current shoes track `max_distance`. Plan generalized `max_value` per gear.
- Determine alert thresholds, notification logic.
- Plan how `value_covered` interacts with service intervals and retirement.

---

## 7. Data Model Planning

### Existing Tables

- `shoes` → possibly extend with `activity_type`, `status`, `metric_type`, `max_value`.

### New Tables to Plan

- `gear_installations` → track parent-child relationships, installation history.
- `gear_services` → service intervals.
- `gear_service_logs` → executed services with timestamps and value.

### Relationships

- Gear ↔ Installations ↔ Parent gear
- Gear ↔ Services ↔ Logs
- Activities ↔ Gear ↔ Components

### Considerations

- Indexing for fast lookups (user, parent gear, active installations)
- Migration plan from existing `shoes` table
- Backwards compatibility with existing activity data

---

## 8. Activity Integration Planning

- Decide rules for activity → parent gear → components usage update.
- Plan validation: metric type consistency, prevent sum of component usage > parent activity.
- Plan how Strava / manual activity import interacts with components and service logs.

---

## 10. AI Agent Planning Tasks

1. Analyze current `shoes` table → decide which fields to extend.
2. Plan generalized `gear` model vs. extend `shoes`.
3. Plan component hierarchy and installation history.
4. Plan service interval system with logs.
5. Plan usage propagation from parent to child components.
6. Identify required API extensions (CRUD, service management, installation tracking, alerts).
7. Design alerting and warning rules (max value, service due).
8. Plan UI/UX updates to visualize gear, service, retirement, and installations.
9. Evaluate dependencies and ordering of tasks:
   - E.g., component system before service propagation.
   - Retire gear system must respect installation logic.
10. Plan future extensions:
    - Multi-level gear hierarchy
    - Predictive maintenance
    - Dual metric tracking (distance + hours)
    - Analytics on component lifespan

---

## 11. Planning Questions / Decisions Needed

- Which metric types to support initially? Distance, hours, sessions?
- How many levels of component hierarchy to allow?
- Should services propagate automatically to components?
- How to handle multi-parent components for historical tracking?
- Should existing `shoes` table be migrated or aliased as `gear`?

---

## 12. Deliverable for AI Agent

- Generate a **development plan** with ordered tasks, dependencies, and data model sketch.
- Identify **required database changes** and migration path.
- Define **rules and constraints** for hierarchy, service, retirement, and usage propagation.
- Suggest **UI/UX design considerations**.
- Highlight **future extensibility points**.
