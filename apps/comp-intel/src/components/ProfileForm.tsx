import { useMemo } from "react";
import { useApp, useUpdateProfile } from "../state";
import { EXPERIENCE_ORDER, PAY_TYPE_LABEL } from "../lib/constants";
import { Field, inputClass, selectClass, Chip } from "./ui";
import { SalaryInput } from "./SalaryInput";

export function ProfileForm({ compact = false }: { compact?: boolean }) {
  const { state } = useApp();
  const set = useUpdateProfile();
  const catalog = state.data?.catalog;
  if (!catalog) return null;

  const p = state.profile;
  const indiaOnly = catalog.countries.length === 1 && catalog.countries[0]?.code === "IN";

  const roleNames = useMemo(() => {
    if (p.roleFamily && catalog.roleNamesByFamily?.[p.roleFamily]?.length) {
      return catalog.roleNamesByFamily[p.roleFamily]!;
    }
    return catalog.roleNames.slice(0, 120);
  }, [catalog.roleNames, catalog.roleNamesByFamily, p.roleFamily]);

  return (
    <div className="space-y-5">
      <SalaryInput />

      {indiaOnly ? (
        <p className="text-[11px] leading-relaxed text-mute">
          Switch hub and P25 / P50 / P75 target in the header — salary stays fixed in INR.
        </p>
      ) : null}

      <Field label="Incumbent label">
        <input
          className={inputClass}
          value={p.label}
          onChange={(e) => set({ label: e.target.value })}
          placeholder="e.g. Priya · DS Mid · Bengaluru"
        />
      </Field>

      <div className={`grid gap-3 ${compact ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2"}`}>
        <Field label="Country">
          <select
            className={selectClass}
            value={p.countryCode}
            onChange={(e) => set({ countryCode: e.target.value, city: "", metro: "" })}
          >
            {catalog.countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.code === "IN" ? "India Market Baseline" : c.name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Role family">
          <select
            className={selectClass}
            value={p.roleFamily}
            onChange={(e) => set({ roleFamily: e.target.value, roleName: "" })}
          >
            <option value="">All role family</option>
            {catalog.roleFamilies.map((r) => (
              <option key={r.name} value={r.name}>
                {r.name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Experience">
          <select
            className={selectClass}
            value={p.experienceLevel}
            onChange={(e) => set({ experienceLevel: e.target.value })}
          >
            <option value="">Any Experience</option>
            {[...catalog.experienceLevels]
              .sort(
                (a, b) =>
                  EXPERIENCE_ORDER.indexOf(a.name) - EXPERIENCE_ORDER.indexOf(b.name),
              )
              .map((e) => (
                <option key={e.name} value={e.name}>
                  {e.name}
                </option>
              ))}
          </select>
        </Field>

        <Field label="Role title (optional)">
          <select
            className={selectClass}
            value={p.roleName}
            onChange={(e) => set({ roleName: e.target.value })}
          >
            <option value="">Any title in family</option>
            {roleNames.map((r) => (
              <option key={r.name} value={r.name}>
                {r.name}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Pay type">
          <div className="flex flex-wrap gap-1.5">
            {catalog.payTypes.map((pt) => (
              <Chip
                key={pt.name}
                active={p.payType === pt.name}
                onClick={() => set({ payType: pt.name })}
              >
                {PAY_TYPE_LABEL[pt.name] ?? pt.name}
              </Chip>
            ))}
          </div>
        </Field>
      </div>
    </div>
  );
}
