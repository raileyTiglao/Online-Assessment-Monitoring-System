// src/components/ConfirmModal.tsx — generic confirm/cancel modal, replacing
// window.confirm()/window.alert() for destructive actions (currently just
// ExamsAndSessionsPage's delete-exam flow) with something that matches the
// app's own look instead of a native browser dialog.

import { useEffect } from "react";

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  // Escape-to-cancel — not while busy, so an in-flight delete can't be
  // dismissed out from under itself.
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onCancel();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      onClick={() => !busy && onCancel()}
      role="presentation"
    >
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="confirm-modal-title">{title}</h3>
        <div className="modal-card__message">{message}</div>
        <div className="modal-actions">
          <button type="button" className="button-secondary" disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={danger ? "button-danger" : ""}
            disabled={busy}
            onClick={onConfirm}
          >
            {busy ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
