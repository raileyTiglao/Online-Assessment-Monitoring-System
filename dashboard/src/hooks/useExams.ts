// src/hooks/useExams.ts — live Firestore query over the "exams" collection
// (professor's own exams, or all exams for admin) plus exam creation with
// collision-retry: a client set() on an existing code doc is classified as
// an "update" by Firestore, which firestore.rules only allows the owning
// professor to do — a code collision from a different professor's create
// attempt fails with permission-denied, which we catch and retry with a
// freshly generated code.

import { useEffect, useState, useCallback } from "react";
import {
  collection, query, where, orderBy, onSnapshot,
  doc, setDoc, serverTimestamp,
  getDocs, writeBatch,
} from "firebase/firestore";
import { ref, deleteObject } from "firebase/storage";
import { db, storage } from "../firebase";
import { useAuth } from "../auth/AuthContext";
import type { SessionDoc } from "./useSessions";

export interface ExamDoc {
  code: string; // Firestore doc ID === code
  title: string;
  professorUid: string;
  professorEmail: string;
  createdAt: unknown; // Firestore Timestamp
  active: boolean;
}

const CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // no 0/O/1/I ambiguity

function generateExamCode(): string {
  let suffix = "";
  for (let i = 0; i < 5; i++) {
    suffix += CODE_CHARS[Math.floor(Math.random() * CODE_CHARS.length)];
  }
  return `EXAM-${suffix}`;
}

export function useExams() {
  const { user, role } = useAuth();
  const [exams, setExams] = useState<ExamDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user || !role) return;

    const base = collection(db, "exams");
    const q = role === "admin"
      ? query(base, orderBy("createdAt", "desc"))
      : query(base, where("professorUid", "==", user.uid), orderBy("createdAt", "desc"));

    setLoading(true);
    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        setExams(snapshot.docs.map((d) => ({ code: d.id, ...d.data() }) as ExamDoc));
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
    );
    return unsubscribe;
  }, [user, role]);

  const createExam = useCallback(
    async (title: string, maxAttempts = 5): Promise<string> => {
      if (!user) throw new Error("Not signed in.");

      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        const code = generateExamCode();
        try {
          await setDoc(doc(db, "exams", code), {
            code,
            title,
            professorUid: user.uid,
            professorEmail: user.email,
            createdAt: serverTimestamp(),
            active: true,
          });
          return code;
        } catch (err) {
          // permission-denied here means the code already exists (see file
          // header) — regenerate and retry. Any other error propagates.
          const isCollision = (err as { code?: string }).code === "permission-denied";
          if (!isCollision || attempt === maxAttempts - 1) throw err;
        }
      }
      throw new Error("Could not generate a unique exam code — please try again.");
    },
    [user],
  );

  // Deletes the exam doc, every session recorded under it, AND those
  // sessions' evidence screenshots in Storage. Firestore side (exam +
  // sessions) goes first as one batch, so the exam and its sessions
  // disappear together, not exam-deleted-but-sessions-still-there on a
  // failure partway through; Storage cleanup runs after, per-file and
  // best-effort (a screenshot already missing/deleted, or one blocked by
  // a storage.rules mismatch, is logged and skipped rather than aborting
  // the rest of the cleanup — Firestore deletion succeeding is the part
  // that actually matters for the dashboard). Firestore batches cap at
  // 500 ops; fine for this app's scale, but a very high-volume exam
  // could theoretically exceed it — not handled here.
  const deleteExam = useCallback(async (code: string): Promise<number> => {
    if (!user) throw new Error("Not signed in.");

    // Same constraint as useSessions.ts: a professor's query MUST filter
    // on professor_uid itself, or Firestore rejects the query outright
    // (permission-denied) rather than silently scoping it — the security
    // rule can't prove every matched doc belongs to this professor
    // without that filter being part of the query.
    const sessionsBase = collection(db, "sessions");
    const sessionsQuery = role === "admin"
      ? query(sessionsBase, where("exam_code", "==", code))
      : query(sessionsBase, where("exam_code", "==", code), where("professor_uid", "==", user.uid));
    const sessionDocs = await getDocs(sessionsQuery);

    const screenshotPaths = sessionDocs.docs.flatMap((d) => {
      const session = d.data() as SessionDoc;
      return session.events
        .map((e) => e.screenshot_path)
        .filter((p): p is string => Boolean(p));
    });

    const batch = writeBatch(db);
    sessionDocs.forEach((d) => batch.delete(d.ref));
    batch.delete(doc(db, "exams", code));
    await batch.commit();

    await Promise.all(
      screenshotPaths.map((path) =>
        deleteObject(ref(storage, path)).catch((err) =>
          console.warn(`[deleteExam] Couldn't delete evidence file ${path}:`, err),
        ),
      ),
    );

    return sessionDocs.size;
  }, [user, role]);

  return { exams, loading, error, createExam, deleteExam };
}
