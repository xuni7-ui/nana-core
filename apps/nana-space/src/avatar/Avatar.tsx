import { useEffect, useState } from "react";
/** Display-only driver. Only a sanitized Core projection may supply expressions or speech cues. */
export interface AvatarCue {
  origin: "CORE_PROJECTION" | "DEMO";
  expression?: string;
  speaking?: boolean;
  mouthOpen?: number;
}
export interface AvatarDriver {
  kind: "static" | "live2d";
  mount: (container: HTMLElement) => Promise<void>;
  apply: (cue: AvatarCue) => void;
  resize: () => void;
  dispose: () => void;
}
export const avatarCapabilities = {
  static: true,
  live2d: false,
  lipSync: false,
} as const;
export function Avatar({
  size = 40,
  expression = "neutral",
  className = "",
}: {
  size?: number;
  expression?: string;
  className?: string;
}) {
  void expression; // Static original artwork; never implies an inferred mood.
  return (
    <img
      className={`avatar ${className}`}
      src="/assets/nana-next.svg"
      alt="奈奈 · 原创静态形象"
      width={size}
      height={size}
    />
  );
}
export function AvatarStage({
  expression = "neutral",
  enabled = true,
}: {
  expression?: string;
  enabled?: boolean;
}) {
  const [url, setUrl] = useState<string>();
  const [error, setError] = useState("");
  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url);
    },
    [url],
  );
  return (
    <div className="avatar-studio">
      {enabled ? (
        <div className="avatar-orbit">
          {url ? (
            <img className="custom-avatar" src={url} alt="本地角色预览" />
          ) : (
            <Avatar size={140} expression={expression} />
          )}
          <span className="orbit-spark">✧</span>
        </div>
      ) : (
        <div className="avatar-orbit">
          <span className="orbit-spark">✦</span>
        </div>
      )}
      <h3>同一个奈奈，不同的窗口</h3>
      <p>当前为静态头像。形象是表达层，主体始终属于 Nana Core。</p>
      <label className="button secondary file-button">
        预览本地角色图片
        <input
          aria-label="选择本地角色图片"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) {
              if (
                f.size > 5 * 1024 * 1024 ||
                !["image/png", "image/jpeg", "image/webp"].includes(f.type)
              ) {
                setError("请选择 5 MB 以内的 PNG / JPEG / WebP 图片。");
              } else {
                setError("");
                setUrl(URL.createObjectURL(f));
              }
            }
            e.target.value = "";
          }}
        />
      </label>
      {error && <p role="alert">{error}</p>}
      <small>PNG / JPEG / WebP · ≤ 5 MB · 仅本次页面预览</small>
      <span className="badge muted">Live2D 驱动 · PLANNED</span>
    </div>
  );
}
