import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import type { FollowUpRecord, HandlingChannel, InteractionResult } from "@/types/alerts";

type FollowUpFormProps = {
  onCancel: () => void;
  onSubmit: (record: FollowUpRecord) => void;
};

export function FollowUpForm({ onCancel, onSubmit }: Omit<FollowUpFormProps, "clientName">) {
  const { t } = useTranslation();
  const [handledBy, setHandledBy] = useState<HandlingChannel>("phone");
  const [result, setResult] = useState<InteractionResult>("positive");
  const [reminder, setReminder] = useState("");

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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    onSubmit({
      handledBy,
      result,
      reminder: reminder.trim(),
      submittedAt: new Date().toISOString(),
    });
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <label className="block space-y-2">
        <span className="text-sm font-medium text-foreground">{t("form.handled_label")}</span>
        <select
          className="h-10 w-full rounded-md border bg-background px-3 text-sm outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/20"
          value={handledBy}
          onChange={(event) => setHandledBy(event.target.value as HandlingChannel)}
        >
          {handlingOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <fieldset className="space-y-3">
        <legend className="text-sm font-medium text-foreground">{t("form.result_label")}</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {resultOptions.map((option) => (
            <label
              key={option.value}
              className="flex cursor-pointer items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/5"
            >
              <input
                checked={result === option.value}
                className="size-4 accent-primary"
                name="result"
                type="radio"
                value={option.value}
                onChange={() => setResult(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-foreground">{t("form.reminder_label")}</span>
        <textarea
          className="min-h-24 w-full resize-none rounded-md border bg-background px-3 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
          placeholder={t("form.reminder_placeholder")}
          value={reminder}
          onChange={(event) => setReminder(event.target.value)}
        />
      </label>

      <div className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
        <Button variant="outline" type="button" onClick={onCancel}>
          {t("form.cancel")}
        </Button>
        <Button type="submit">{t("form.submit")}</Button>
      </div>
    </form>
  );
}
