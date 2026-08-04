// src/hooks/useSessions.ts — live Firestore query over the "sessions"
// collection, scoped by role. Shape matches monitoring/session_report.py's
// _build_report_dict() + the session_uid/exam fields added on top by
// connection/firebase_db.py::FirestoreSessionRepository.save_report().

import { useEffect, useState } from "react";
import { collection, query, where, orderBy, onSnapshot } from "firebase/firestore";
import { db } from "../firebase";
import { useAuth } from "../auth/AuthContext";

export interface FlaggedEvent {
  timestamp: string;
  risk_level: "MODERATE" | "HIGH";
  yaw: number;
  pitch: number;
  roll: number;
  device_detected: boolean;
  behavioral_indicator: string;
  trigger: string;
  // A Storage object path (e.g. "evidence/<uid>/<session>/<file>.jpg"),
  // resolved to a real URL by ScreenshotViewer via getDownloadURL() — not
  // itself a URL. Always null for MODERATE events (EvidenceCapture only
  // captures on HIGH).
  screenshot_path: string | null;
}

export interface CalibrationBaseline {
  yaw: number;
  pitch: number;
  roll: number;
  sample_count: number;
}

export interface SessionDoc {
  id: string; // Firestore doc ID === session_uid
  session_start: string;
  session_end: string;
  calibration_baseline: CalibrationBaseline | null;
  total_flagged_events: number;
  high_risk_count: number;
  moderate_risk_count: number;
  events: FlaggedEvent[];
  exam_code: string | null;
  professor_uid: string | null;
  exam_title: string | null;
  examinee_label: string | null;
}

export function useSessions() {
  const { user, role } = useAuth();
  const [sessions, setSessions] = useState<SessionDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !role) return;

    const base = collection(db, "sessions");
    // A professor's query MUST filter on professor_uid — Firestore rules
    // reject an unfiltered read from a professor account outright (see
    // firestore.rules), rather than silently returning only their own
    // docs, so this filter is load-bearing, not an optimization.
    const q = role === "admin"
      ? query(base, orderBy("session_start", "desc"))
      : query(base, where("professor_uid", "==", user.uid), orderBy("session_start", "desc"));

    setLoading(true);
    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        setSessions(snapshot.docs.map((d) => ({ id: d.id, ...d.data() }) as SessionDoc));
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
    );
    return unsubscribe;
  }, [user, role]);

  return { sessions, loading, error };
}
