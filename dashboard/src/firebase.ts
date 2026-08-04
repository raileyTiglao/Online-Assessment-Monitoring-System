// src/firebase.ts — Firebase SDK init. Connects to the Local Emulator Suite
// in dev (npm run dev) instead of the real project, so day-to-day work
// never touches production data. See firebase.json at the repo root for
// emulator ports.

import { initializeApp } from "firebase/app";
import { getAuth, connectAuthEmulator } from "firebase/auth";
import { getFirestore, connectFirestoreEmulator } from "firebase/firestore";
import { getStorage, connectStorageEmulator } from "firebase/storage";

// Replace YOUR_* below with your real Firebase project's web app config
// (Firebase Console -> Project settings -> General -> Your apps -> Web
// app) for a real deployment. Safe to commit — these are public client
// identifiers, not secrets; access control is enforced by firestore.rules
// / storage.rules, not by hiding this config.
//
// In dev (npm run dev), the emulators are used instead (see below), and
// the emulators only recognize the project ID they were started with —
// `firebase emulators:start --project demo-oams` (see connection/
// seed_emulator.py) — so projectId must stay "demo-oams" here in DEV
// regardless of the real project ID, or the app won't see seeded data.
const firebaseConfig = {
  apiKey: import.meta.env.DEV ? "demo-api-key" : "AIzaSyDYTooK3dgLG6vci28qgPLoPTw0oAFYJVY",
  authDomain: "baandod-testing.firebaseapp.com",
  projectId: import.meta.env.DEV ? "demo-oams" : "baandod-testing",
  storageBucket: import.meta.env.DEV ? "demo-oams.appspot.com" : "baandod-testing.firebasestorage.app",
  messagingSenderId: "149647348434",
  appId: "1:149647348434:web:3c21b37c0e320b6fea130b",
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);

if (import.meta.env.DEV) {
  connectAuthEmulator(auth, "http://127.0.0.1:9099", { disableWarnings: true });
  connectFirestoreEmulator(db, "127.0.0.1", 8080);
  connectStorageEmulator(storage, "127.0.0.1", 9199);
}
