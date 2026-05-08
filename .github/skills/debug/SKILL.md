# Debug

Use this workflow when diagnosing a failure.

1. Reproduce with the smallest Docker or local command.
2. Capture the exact command, exit code, and relevant log lines.
3. Check configuration before rewriting code.
4. Isolate frontend, backend, database, and Docker issues separately.
5. Apply the smallest fix that explains the symptom.
6. Re-run the original failing command.

Keep notes factual. Do not mask failures by broadening retries or swallowing exceptions.
