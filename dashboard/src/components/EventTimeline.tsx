// src/components/EventTimeline.tsx — chronological list of flagged events
// for one session, each with its risk level, the behavioral reason
// (HeadPoseNormalizer's normalized_pose.reason), the RiskClassifier
// trigger description, and the evidence screenshot (if any).

import { RiskBadge } from "./RiskBadge";
import { ScreenshotViewer } from "./ScreenshotViewer";
import type { FlaggedEvent } from "../hooks/useSessions";

export function EventTimeline({ events }: { events: FlaggedEvent[] }) {
  if (events.length === 0) {
    return <p className="empty-state">No flagged events in this session.</p>;
  }

  return (
    <ol className="event-timeline">
      {events.map((event, i) => (
        <li key={i} className="event-timeline__item">
          <div className="event-timeline__header">
            <RiskBadge level={event.risk_level} />
            <time>{new Date(event.timestamp).toLocaleString()}</time>
          </div>
          <p className="event-timeline__trigger">{event.trigger || event.behavioral_indicator}</p>
          <dl className="event-timeline__pose">
            <dt>Yaw</dt><dd>{event.yaw.toFixed(1)}°</dd>
            <dt>Pitch</dt><dd>{event.pitch.toFixed(1)}°</dd>
            <dt>Roll</dt><dd>{event.roll.toFixed(1)}°</dd>
            <dt>Device detected</dt><dd>{event.device_detected ? "Yes" : "No"}</dd>
          </dl>
          <ScreenshotViewer screenshotPath={event.screenshot_path} />
        </li>
      ))}
    </ol>
  );
}
