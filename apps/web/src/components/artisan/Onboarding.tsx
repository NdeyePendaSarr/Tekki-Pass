"use client";

import { type FormEvent, useMemo, useState } from "react";
import {
  identityFromPhrase,
  newRecoveryPhrase,
  normalizePhrase,
  pickCheckPositions,
} from "@/lib/identity";
import { isValidPin, saveVault } from "@/lib/vault";

type Step = "intro" | "words" | "check" | "pin";

/**
 * Profile creation: generate the recovery phrase, make the artisan write it down,
 * check 3 words (brief: "une vérification avant de continuer"), then protect it with a PIN.
 */
export function Onboarding({ onDone }: { onDone: (phrase: string) => void }) {
  const [step, setStep] = useState<Step>("intro");
  const [phrase] = useState(newRecoveryPhrase);
  const words = useMemo(() => phrase.split(" "), [phrase]);
  const [positions] = useState(() => pickCheckPositions(12));
  const [answers, setAnswers] = useState<string[]>(["", "", ""]);
  const [pin, setPin] = useState("");
  const [pinAgain, setPinAgain] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function submitCheck(event: FormEvent) {
    event.preventDefault();
    const ok = positions.every(
      (position, i) => normalizePhrase(answers[i] ?? "") === words[position],
    );
    if (!ok) {
      setError("Un mot ne correspond pas. Regarde ta feuille et réessaie.");
      return;
    }
    setError(null);
    setStep("pin");
  }

  async function submitPin(event: FormEvent) {
    event.preventDefault();
    if (!isValidPin(pin)) return setError("Le code doit avoir 6 chiffres.");
    if (pin !== pinAgain) return setError("Les deux codes sont différents.");
    setSaving(true);
    await saveVault(phrase, pin, identityFromPhrase(phrase).pubkey);
    onDone(phrase);
  }

  if (step === "intro") {
    return (
      <section>
        <h1>Créer mon profil</h1>
        <p>
          Tu vas recevoir <strong>12 mots secrets</strong>. Ils sont la clé de ton profil et de tes
          preuves. Prépare une feuille et un stylo.
        </p>
        <button className="button" onClick={() => setStep("words")}>
          Je suis prêt
        </button>
      </section>
    );
  }

  if (step === "words") {
    return (
      <section>
        <h1>Écris ces 12 mots</h1>
        <p>Dans l&apos;ordre, sur papier. Ne les envoie à personne, même pas à Tekki-Pass.</p>
        <ol className="words">
          {words.map((word, i) => (
            <li key={i}>{word}</li>
          ))}
        </ol>
        <button className="button" onClick={() => setStep("check")}>
          J&apos;ai écrit les 12 mots
        </button>
      </section>
    );
  }

  if (step === "check") {
    return (
      <form onSubmit={submitCheck}>
        <h1>Vérifions ta feuille</h1>
        {positions.map((position, i) => (
          <label key={position} className="field">
            Mot n°{position + 1}
            <input
              autoComplete="off"
              autoCapitalize="none"
              value={answers[i]}
              onChange={(e) =>
                setAnswers((current) => current.map((a, j) => (j === i ? e.target.value : a)))
              }
              required
            />
          </label>
        ))}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="button" type="submit">
          Vérifier
        </button>
        <button type="button" className="link" onClick={() => setStep("words")}>
          Revoir les mots
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={submitPin}>
      <h1>Choisis un code à 6 chiffres</h1>
      <p>Il protège ton profil sur ce téléphone.</p>
      <label className="field">
        Code
        <input
          inputMode="numeric"
          type="password"
          maxLength={6}
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          required
        />
      </label>
      <label className="field">
        Répète le code
        <input
          inputMode="numeric"
          type="password"
          maxLength={6}
          value={pinAgain}
          onChange={(e) => setPinAgain(e.target.value)}
          required
        />
      </label>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button className="button" type="submit" disabled={saving}>
        {saving ? "Enregistrement…" : "Terminer"}
      </button>
    </form>
  );
}
