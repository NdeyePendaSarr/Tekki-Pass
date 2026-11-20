"use client";

import { type FormEvent, useMemo, useState } from "react";
import {
  identityFromPhrase,
  newRecoveryPhrase,
  normalizePhrase,
  pickCheckPositions,
} from "@/lib/identity";
import { isValidPin, saveVault } from "@/lib/vault";
import { Icon } from "../Icon";
import { Stepper } from "../Stepper";

const STEPS = ["Préparer", "Écrire", "Vérifier", "Protéger"] as const;

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
        <Stepper steps={STEPS} current={0} />
        <h1>Créer mon profil</h1>
        <p className="lead">
          Tu vas recevoir <strong>12 mots secrets</strong>. Ils sont la clé de ton profil, de tes
          preuves et de ton portefeuille.
        </p>
        <div className="callout">
          <Icon name="key" />
          <p>
            Prépare une <strong>feuille et un stylo</strong>. Si tu perds ton téléphone, ces 12 mots
            sont le seul moyen de tout récupérer.
          </p>
        </div>
        <button className="button" onClick={() => setStep("words")}>
          Je suis prêt
        </button>
      </section>
    );
  }

  if (step === "words") {
    return (
      <section>
        <Stepper steps={STEPS} current={1} />
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
        <Stepper steps={STEPS} current={2} />
        <h1>Vérifions ta feuille</h1>
        <p className="muted">Recopie ces 3 mots depuis ta feuille.</p>
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
      <Stepper steps={STEPS} current={3} />
      <h1>Choisis un code à 6 chiffres</h1>
      <p>Il protège ton profil sur ce téléphone. Tu le taperas à chaque ouverture.</p>
      <label className="field">
        Code
        <input
          className="pin"
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
          className="pin"
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
