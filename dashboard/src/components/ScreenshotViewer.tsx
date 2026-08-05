// src/components/ScreenshotViewer.tsx — resolves a Storage object path
// (events[].screenshot_path) to a real, access-controlled download URL.
// screenshot_path is null for every MODERATE event by design — EvidenceCapture
// (monitoring/evidence_capture.py) only ever captures on HIGH risk — so a
// missing screenshot here is an expected empty state, not a bug.

import { useEffect, useState } from "react";
import { ref, getDownloadURL } from "firebase/storage";
import { storage } from "../firebase";

export function ScreenshotViewer({ screenshotPath }: { screenshotPath: string | null }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setUrl(null);
    setError(false);
    if (!screenshotPath) return;

    let cancelled = false;
    getDownloadURL(ref(storage, screenshotPath))
      .then((resolved) => { if (!cancelled) setUrl(resolved); })
      .catch(() => { if (!cancelled) setError(true); });

    return () => { cancelled = true; };
  }, [screenshotPath]);

  if (!screenshotPath) {
    return <div className="screenshot-placeholder">No screenshot (MODERATE risk)</div>;
  }
  if (error) {
    return <div className="screenshot-placeholder screenshot-placeholder--error">
      Screenshot unavailable
    </div>;
  }
  if (!url) {
    return <div className="screenshot-placeholder">Loading…</div>;
  }
  return <img className="screenshot-image" src={url} alt="Evidence screenshot" />;
}
