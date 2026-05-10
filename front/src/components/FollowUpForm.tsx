import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import type { HandlingChannel, InteractionRecord, InteractionResult } from "@/types/alerts";

type FollowUpFormProps = {
  onCancel: () => void;
  onSubmit: (record: InteractionRecord) => void;
};

function OutcomeToggle({
  value,
  onChange,
  yesLabel,
  noLabel,
  label,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
  yesLabel: string;
  noLabel: string;
  label: string;
}) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium text-foreground">{label}</legend>
      <div className="flex gap-2">
        {([true, false] as const).map((opt) => (
          <button
            key={String(opt)}
            type="button"
            onClick={() => onChange(opt)}
            className={[
              "flex-1 rounded-md border px-3 py-2 text-sm font-medium transition-colors",
              value === opt
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-background text-foreground hover:bg-secondary",
            ].join(" ")}
          >
            {opt ? yesLabel : noLabel}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export function FollowUpForm({ onCancel, onSubmit }: FollowUpFormProps) {
  const { t } = useTranslation();
  const [handledBy, setHandledBy] = useState<HandlingChannel>("phone");
  const [answered, setAnswered] = useState(true);
  const [visitSuccessful, setVisitSuccessful] = useState(true);
  const [emailResponseReceived, setEmailResponseReceived] = useState(true);
  const [result, setResult] = useState<InteractionResult>("positive");
  const [notes, setNotes] = useState("");
  const [keepOpen, setKeepOpen] = useState(false);

  const handlingOptions: Array<{ value: HandlingChannel; label: string }> = [
    { value: "phone", label: t("form.handling.phone") },
    { value: "visit", label: t("form.handling.visit") },
    { value: "email", label: t("form.handling.email") },
    { value: "other", label: t("form.handling.other") },
  ];

  const resultOptions: Array<{ value: InteractionResult; label: string }> = [
    { value: "positive", label: t("form.results.positive") },
    { value: "neutral", label: t("form.results.neutral") },
    { value: "negative", label: t("form.results.negative") },
  ];

  // Whether the contact was successful (i.e. show Result + Notes)
  const contactMade =
    handledBy === "phone" ? answered :
    handledBy === "visit" ? visitSuccessful :
    handledBy === "email" ? emailResponseReceived :
    true; // "other" always shows result

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const record: InteractionRecord = {
      id: `int-${Date.now()}`,
      handledBy,
      ...(handledBy === "phone" ? { answered } : {}),
      ...(handledBy === "visit" ? { visitSuccessful } : {}),
      ...(handledBy === "email" ? { emailResponseReceived } : {}),
      ...(contactMade ? { result, notes: notes.trim() } : {}),
      keepOpen,
      submittedAt: new Date().toISOString(),
    };
    onSubmit(record);
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      {/* Channel selector */}
      <label className="block space-y-2">
        <span className="text-sm font-medium text-foreground">{t("form.handled_label")}</span>
        <select
          className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/20"
          value={handledBy}
          onChange={(e) => setHandledBy(e.target.value as HandlingChannel)}
        >
          {handlingOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </label>

      {/* Channel-specific outcome toggle */}
      {handledBy === "phone" && (
        <OutcomeToggle
          label={t("form.answered.label")}
          value={answered}
          onChange={setAnswered}
          yesLabel={t("form.answered.yes")}
          noLabel={t("form.answered.no")}
        />
      )}
      {handledBy === "visit" && (
        <OutcomeToggle
          label={t("form.visit_ok.label")}
          value={visitSuccessful}
          onChange={setVisitSuccessful}
          yesLabel={t("form.visit_ok.yes")}
          noLabel={t("form.visit_ok.no")}
        />
      )}
      {handledBy === "email" && (
        <OutcomeToggle
          label={t("form.email_response.label")}
          value={emailResponseReceived}
          onChange={setEmailResponseReceived}
          yesLabel={t("form.email_response.yes")}
          noLabel={t("form.email_response.no")}
        />
      )}

      {/* Result + Notes — only when contact was made */}
      {contactMade && (
        <>
          <fieldset className="space-y-3">
            <legend className="text-sm font-medium text-foreground">{t("form.result_label")}</legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {resultOptions.map((opt) => (
                <label
                  key={opt.value}
                  className="flex cursor-pointer items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                >
                  <input
                    checked={result === opt.value}
                    className="size-4 accent-primary"
                    name="result"
                    type="radio"
                    value={opt.value}
                    onChange={() => setResult(opt.value)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </fieldset>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-foreground">{t("form.reminder_label")}</span>
            <textarea
              className="min-h-20 w-full resize-none rounded-md border bg-background px-3 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
              placeholder={t("form.reminder_placeholder")}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
        </>
      )}

      {/* Keep open toggle */}
      <OutcomeToggle
        label={t("form.keep_open.label")}
        value={keepOpen}
        onChange={setKeepOpen}
        yesLabel={t("form.keep_open.keep")}
        noLabel={t("form.keep_open.close")}
      />

      <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
        <Button variant="outline" type="button" onClick={onCancel}>
          {t("form.cancel")}
        </Button>
        <Button type="submit">{t("form.submit")}</Button>
      </div>
    </form>
  );
}
