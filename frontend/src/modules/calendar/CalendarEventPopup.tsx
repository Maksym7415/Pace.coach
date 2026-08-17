import { useRef, useState, type ChangeEvent } from "react";
import { Bike, Dumbbell, Footprints, Upload, Waves } from "lucide-react";
import { Link } from "react-router-dom";
import { importFitFile, type Activity } from "../activities/api";
import {
  formatDistance,
  formatDurationCompact,
} from "../activities/format";
import { toSportFilterId, type SportFilterId } from "../activities/sportFilter";
import { toDateKey } from "../shared/dates";
import type { Workout } from "../training/api";
import {
  displayStatusForActivity,
  displayStatusForWorkout,
  STATUS_BADGE_LABEL,
  type CalendarDisplayStatus,
} from "./eventStatus";

export type CalendarPopupItem =
  | { kind: "activity"; activity: Activity }
  | { kind: "workout"; workout: Workout };

const SPORT_ICONS: Record<SportFilterId, typeof Footprints> = {
  run: Footprints,
  bike: Bike,
  swim: Waves,
  other: Dumbbell,
};

const SPORT_LABELS: Record<SportFilterId, string> = {
  run: "Run",
  bike: "Bike",
  swim: "Swim",
  other: "Other",
};

function sportMeta(sportCode: string | null): { Icon: typeof Footprints; label: string } {
  const id = toSportFilterId(sportCode);
  return { Icon: SPORT_ICONS[id], label: SPORT_LABELS[id] };
}

function formatMinutes(min: number | null | undefined): string | null {
  if (min == null) return null;
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (h <= 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

type PopupView = {
  title: string;
  date: string;
  sportCode: string | null;
  duration: string | null;
  distance: string | null;
  status: CalendarDisplayStatus;
  activityId: number | null;
  workout: Workout | null;
  executionScore: number | null;
};

function toView(item: CalendarPopupItem, today: string): PopupView {
  if (item.kind === "activity") {
    const a = item.activity;
    return {
      title: a.name,
      date: toDateKey(a.date),
      sportCode: a.sport_code,
      duration: formatDurationCompact(a.total_hours),
      distance: a.total_distance_km != null ? formatDistance(a.total_distance_km) : null,
      status: displayStatusForActivity(),
      activityId: a.id,
      workout: null,
      executionScore: null,
    };
  }
  const w = item.workout;
  return {
    title: w.title,
    date: toDateKey(w.scheduled_date),
    sportCode: w.sport_code,
    duration: formatMinutes(w.duration_min),
    distance: w.distance_m != null ? formatDistance(w.distance_m / 1000) : null,
    status: displayStatusForWorkout(w, today),
    activityId: w.activity_id,
    workout: w,
    executionScore: w.execution_score,
  };
}

export function CalendarEventPopup({
  item,
  athleteId,
  today,
  onClose,
  onOpenWorkout,
  onUploaded,
}: {
  item: CalendarPopupItem | null;
  athleteId: number;
  today: string;
  onClose: () => void;
  onOpenWorkout: (workout: Workout) => void;
  onUploaded?: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  if (!item) return null;

  const view = toView(item, today);
  const { Icon, label: sportLabel } = sportMeta(view.sportCode);
  const showScore = view.executionScore != null;
  const canOpenActivity = view.activityId != null;
  const canOpenWorkout = view.workout != null;

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".fit")) {
      setUploadMessage("Please select a .fit file");
      return;
    }
    setUploading(true);
    setUploadMessage(null);
    try {
      const result = await importFitFile(athleteId, file);
      if (result.success) {
        setUploadMessage("Activity uploaded — processing in background.");
        onUploaded?.();
      } else {
        setUploadMessage(result.error ?? "Failed to upload activity");
      }
    } catch {
      setUploadMessage("Failed to upload activity");
    } finally {
      setUploading(false);
    }
  }

  function handlePrimaryCta() {
    if (view.status === "planned" && view.workout) {
      onOpenWorkout(view.workout);
      onClose();
      return;
    }
    if (view.status === "missed" && view.workout) {
      onOpenWorkout(view.workout);
      onClose();
      return;
    }
    if (canOpenActivity) {
      onClose();
      return;
    }
    if (view.workout) {
      onOpenWorkout(view.workout);
      onClose();
    }
  }

  const primaryIsLink = view.status === "completed" && canOpenActivity;
  const primaryLabel =
    view.status === "planned"
      ? "Open planned workout"
      : view.status === "missed"
        ? "Open planned workout"
        : canOpenActivity
          ? "Open full activity"
          : "Open planned workout";

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal card stack calendar-event-popup"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="calendar-event-popup-title"
      >
        <div className="row-between">
          <div className="flex items-center gap-2 min-w-0">
            <Icon className="calendar-event-popup-sport-icon" aria-hidden />
            <h3 id="calendar-event-popup-title" className="calendar-event-popup-title">
              {view.title}
            </h3>
          </div>
          <button type="button" className="secondary" onClick={onClose}>
            Close
          </button>
        </div>

        <p className="muted calendar-event-popup-sub">
          {view.date} · {sportLabel}
        </p>

        <div className="calendar-event-popup-rows">
          {view.duration && (
            <div className="calendar-event-popup-row">
              <span className="muted">Duration</span>
              <span className="font-medium">{view.duration}</span>
            </div>
          )}
          {view.distance && (
            <div className="calendar-event-popup-row">
              <span className="muted">Distance</span>
              <span className="font-medium">{view.distance}</span>
            </div>
          )}
          <div className="calendar-event-popup-row">
            <span className="muted">Status</span>
            <span className={`calendar-event-popup-badge status-${view.status}`}>
              {STATUS_BADGE_LABEL[view.status]}
            </span>
          </div>
          {showScore && (
            <div className="calendar-event-popup-row">
              <span className="muted">Execution score</span>
              <span className="font-medium">{view.executionScore}%</span>
            </div>
          )}
        </div>

        {view.status === "missed" && (
          <div className="calendar-event-popup-missed">
            <p className="muted">This workout has no matching activity yet.</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".fit"
              hidden
              onChange={handleFileChange}
            />
            <button
              type="button"
              className="calendar-event-popup-upload"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="calendar-event-popup-upload-icon" aria-hidden />
              {uploading ? "Uploading…" : "Upload activity"}
            </button>
            {uploadMessage && <p className="muted calendar-event-popup-upload-msg">{uploadMessage}</p>}
          </div>
        )}

        <div className="calendar-event-popup-cta">
          {primaryIsLink && view.activityId != null ? (
            <Link
              to={`/activity/${view.activityId}`}
              className="button-link calendar-event-popup-primary-link"
              onClick={onClose}
            >
              <button type="button" className="calendar-event-popup-primary">
                {primaryLabel}
              </button>
            </Link>
          ) : canOpenWorkout || view.workout ? (
            <button type="button" className="calendar-event-popup-primary" onClick={handlePrimaryCta}>
              {primaryLabel}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
