import { useEffect, useState } from "react";
export interface Preferences {
  theme: "dark" | "light" | "system";
  motion: boolean;
  streamReplies: boolean;
  avatar: boolean;
  fontScale: number;
  quiet: boolean;
  language: "zh-CN";
}
const defaults: Preferences = {
  theme: "system",
  motion: true,
  streamReplies: true,
  avatar: true,
  fontScale: 1,
  quiet: true,
  language: "zh-CN",
};
export function usePreferences() {
  const [preferences, setPreferences] = useState<Preferences>(() => {
    try {
      const x = JSON.parse(
        localStorage.getItem("nana-space.preferences.v1") || "{}",
      );
      return {
        ...defaults,
        theme: ["dark", "light", "system"].includes(x.theme)
          ? x.theme
          : defaults.theme,
        streamReplies: typeof x.streamReplies === "boolean" ? x.streamReplies : true,
        motion: typeof x.motion === "boolean" ? x.motion : defaults.motion,
        avatar: typeof x.avatar === "boolean" ? x.avatar : true,
        fontScale: [0.9, 1, 1.1, 1.2].includes(x.fontScale) ? x.fontScale : 1,
        quiet: typeof x.quiet === "boolean" ? x.quiet : true,
      };
    } catch {
      return defaults;
    }
  });
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      document.documentElement.dataset.theme =
        preferences.theme === "system"
          ? media.matches
            ? "dark"
            : "light"
          : preferences.theme;
      document.documentElement.dataset.motion = preferences.motion
        ? "full"
        : "reduced";
      document.documentElement.style.fontSize = `${16 * preferences.fontScale}px`;
      document.documentElement.style.setProperty(
        "--v3-font-scale",
        String(preferences.fontScale),
      );
    };
    apply();
    media.addEventListener("change", apply);
    try {
      localStorage.setItem(
        "nana-space.preferences.v1",
        JSON.stringify(preferences),
      );
    } catch {}
    return () => media.removeEventListener("change", apply);
  }, [preferences]);
  return [preferences, setPreferences] as const;
}
