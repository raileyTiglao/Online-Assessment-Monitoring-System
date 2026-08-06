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
  doc, setDoc, serverTimestamp, updateDoc,
} from "firebase/firestore";
import { db } from "../firebase";
import { useAuth } from "../auth/AuthContext";

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

  const setExamActive = useCallback(async (code: string, active: boolean) => {
    await updateDoc(doc(db, "exams", code), { active });
  }, []);

  return { exams, loading, error, createExam, setExamActive };
}
