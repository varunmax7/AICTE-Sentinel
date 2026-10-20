"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { useRouter } from "@/i18n/navigation";
import { ApiError, type UserRole, sendOtp, verifyOtp } from "@/lib/api";
import { cn } from "@/lib/utils";

import { Button } from "../ui/button";

const ROLES: UserRole[] = [
  "INSTITUTION",
  "SCRUTINY_OFFICER",
  "REGIONAL_OFFICER",
  "BUREAU_HEAD",
  "COMMITTEE_MEMBER",
  "EVC_EXPERT",
  "ADMIN",
];

const ROLE_HOME: Record<UserRole, string> = {
  INSTITUTION: "/institution/dashboard",
  SCRUTINY_OFFICER: "/officer/dashboard",
  REGIONAL_OFFICER: "/regional/dashboard",
  BUREAU_HEAD: "/bureau/dashboard",
  COMMITTEE_MEMBER: "/committee/dashboard",
  EVC_EXPERT: "/expert",
  ADMIN: "/admin/dashboard",
};

type Step = "identify" | "otp";

export function LoginForm() {
  const t = useTranslations("auth");
  const router = useRouter();

  const [role, setRole] = useState<UserRole>("INSTITUTION");
  const [identifier, setIdentifier] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<Step>("identify");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function errorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      const key = `errors.${err.code}` as Parameters<typeof t>[0];
      if (t.has(key)) return t(key);
    }
    return t("errors.GENERIC");
  }

  async function handleSendOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await sendOtp(identifier, role);
      setStep("otp");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const me = await verifyOtp(identifier, role, code);
      router.push(ROLE_HOME[me.role]);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-6 shadow-sm">
      <h1 className="text-xl font-semibold text-text">{t("title")}</h1>
      <p className="mt-1 text-sm text-muted">{t("subtitle")}</p>

      {step === "identify" ? (
        <form onSubmit={handleSendOtp} className="mt-6 space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted">{t("roleLabel")}</label>
            <div className="grid grid-cols-2 gap-1.5">
              {ROLES.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRole(r)}
                  className={cn(
                    "rounded-lg border px-2 py-1.5 text-left text-xs leading-tight transition-colors",
                    role === r
                      ? "border-primary bg-ai-soft text-primary"
                      : "border-border text-muted hover:bg-surface-2"
                  )}
                >
                  {t(`roles.${r}`)}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="identifier" className="mb-1.5 block text-xs font-medium text-muted">
              {t("identifierLabel")}
            </label>
            <input
              id="identifier"
              type="tel"
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder={t("identifierPlaceholder")}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <Button type="submit" className="w-full" disabled={loading}>
            {t("sendOtp")}
          </Button>
        </form>
      ) : (
        <form onSubmit={handleVerify} className="mt-6 space-y-4">
          <p className="text-sm text-muted">{t("otpSentTo", { identifier })}</p>
          <p className="rounded-lg bg-ai-soft px-3 py-2 text-xs text-ai">{t("demoNotice")}</p>

          <div>
            <label htmlFor="otp" className="mb-1.5 block text-xs font-medium text-muted">
              {t("otpLabel")}
            </label>
            <input
              id="otp"
              type="text"
              inputMode="numeric"
              required
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={t("otpPlaceholder")}
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-center text-lg tracking-widest text-text focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <Button type="submit" className="w-full" disabled={loading}>
            {t("verifyAndLogin")}
          </Button>
          <button
            type="button"
            onClick={() => {
              setStep("identify");
              setCode("");
              setError(null);
            }}
            className="w-full text-center text-xs text-muted hover:text-text"
          >
            {t("changeNumber")}
          </button>
        </form>
      )}
    </div>
  );
}
