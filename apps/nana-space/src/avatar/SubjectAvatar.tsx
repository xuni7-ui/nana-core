import { CircleUserRound } from "lucide-react";
import { Avatar } from "./Avatar";

/** Display-only fallback; it does not define the subject's identity. */
export function SubjectAvatar({size, enabled}: {size: number; enabled: boolean}) {
  return enabled ? <Avatar size={size}/> :
    <CircleUserRound className="avatar" width={size} height={size} role="img" aria-label="默认主体图标"/>;
}
