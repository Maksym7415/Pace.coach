import { useState } from "react";
import { TodaySummary } from "./TodaySummary";
import { CalendarTab } from "./tabs/CalendarTab";
import { ActivitiesTab } from "./tabs/ActivitiesTab";
import { SettingsTab } from "./tabs/SettingsTab";

type DashboardTab = "calendar" | "activities" | "settings";

const TABS: { id: DashboardTab; label: string }[] = [
  { id: "calendar", label: "Calendar" },
  { id: "activities", label: "Activities" },
  { id: "settings", label: "Settings" },
];

export function AthleteDashboard() {
  const [activeTab, setActiveTab] = useState<DashboardTab>("calendar");

  return (
    <div className="stack athlete-dashboard">
      <TodaySummary />

      <div className="tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? "tab active" : "tab"}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="tab-panel">
        {activeTab === "calendar" && <CalendarTab />}
        {activeTab === "activities" && <ActivitiesTab />}
        {activeTab === "settings" && <SettingsTab />}
      </div>
    </div>
  );
}
