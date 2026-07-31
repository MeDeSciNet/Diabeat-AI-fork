/**
 * Which subject this caregiver is following.
 *
 * A prototype stand-in for the identity binding a real deployment would do at
 * login. Stored locally, and pseudonymous by construction (PRD 10.2) - the
 * frontend never holds a name, an identifier, or a date of birth.
 */
const KEY = 'somno.subject';
const DEFAULT = (import.meta as any).env?.VITE_SUBJECT_CODE ?? 'SUBJ-001';

export function getSubjectCode(): string {
  return localStorage.getItem(KEY) ?? DEFAULT;
}

export function setSubjectCode(code: string): void {
  localStorage.setItem(KEY, code);
}

const BED_KEY = 'somno.bed';
const BED_DEFAULT = (import.meta as any).env?.VITE_BED_ID ?? 'BED-01';

export function getBedId(): string {
  return localStorage.getItem(BED_KEY) ?? BED_DEFAULT;
}

export function setBedId(bedId: string): void {
  localStorage.setItem(BED_KEY, bedId);
}

export const ACTOR_ID = (import.meta as any).env?.VITE_ACTOR_ID ?? 'caregiver-1';
