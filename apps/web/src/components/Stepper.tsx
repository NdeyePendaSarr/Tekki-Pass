/** Where the user is in a short flow: "Étape 2 sur 4", shown as a progress bar with labels. */
export function Stepper({ steps, current }: { steps: readonly string[]; current: number }) {
  return (
    <ol className="stepper" aria-label={`Étape ${current + 1} sur ${steps.length}`}>
      {steps.map((step, i) => (
        <li
          key={step}
          className={i < current ? "done" : i === current ? "current" : undefined}
          aria-current={i === current ? "step" : undefined}
        >
          {step}
        </li>
      ))}
    </ol>
  );
}
