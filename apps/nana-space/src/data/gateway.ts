import type { InspectorSnapshot } from "./contracts";
import { AdapterError, assertActive } from "./errors";
import { parseInspectorSnapshot } from "./inspector";
/** PLANNED browser transport. No HTTP endpoint is claimed to exist in Core. */
export interface GatewayConfiguration {
  contract: "nana-space-gateway/v1";
  path: string;
  expectedIdentity: string;
  credentials: "same-origin";
  readOnly: true;
}
export interface GatewayProjection {
  contract: "nana-space-gateway/v1";
  subject_id: string;
  projection: "INSPECTOR";
  execution_authority: false;
  data: InspectorSnapshot;
}
function error(code: string): never {
  throw new AdapterError(
    code,
    "规划中的只读 Gateway 未连接，或响应不符合版本与身份边界。",
  );
}
function object(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    return error("GATEWAY_INVALID");
  return value as Record<string, unknown>;
}
export function validateGatewayConfiguration(
  input: unknown,
  origin: string,
): GatewayConfiguration {
  const value = object(input);
  if (
    Object.keys(value).some(
      (key) =>
        ![
          "contract",
          "path",
          "expectedIdentity",
          "credentials",
          "readOnly",
        ].includes(key),
    )
  )
    return error("GATEWAY_CONFIG_UNKNOWN_FIELD");
  if (value.contract !== "nana-space-gateway/v1")
    return error("GATEWAY_VERSION_UNSUPPORTED");
  if (value.credentials !== "same-origin" || value.readOnly !== true)
    return error("GATEWAY_PERMISSION_DENIED");
  if (
    typeof value.expectedIdentity !== "string" ||
    !/^[A-Za-z0-9._:-]{1,128}$/.test(value.expectedIdentity)
  )
    return error("SUBJECT_IDENTITY_REQUIRED");
  if (
    typeof value.path !== "string" ||
    !value.path.startsWith("/") ||
    value.path.startsWith("//") ||
    value.path.includes("\\") ||
    value.path.length > 256
  )
    return error("GATEWAY_SAME_ORIGIN_REQUIRED");
  let url: URL;
  try {
    url = new URL(value.path, origin);
  } catch {
    return error("GATEWAY_URL_INVALID");
  }
  if (
    url.origin !== origin ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    !/^\/api\/nana-space\/v1(?:\/[a-z-]+)?$/.test(url.pathname)
  )
    return error("GATEWAY_SAME_ORIGIN_REQUIRED");
  return {
    contract: "nana-space-gateway/v1",
    path: url.pathname,
    expectedIdentity: value.expectedIdentity,
    credentials: "same-origin",
    readOnly: true,
  };
}
export function validateGatewayProjection(
  input: unknown,
  expectedIdentity: string,
): GatewayProjection {
  const value = object(input);
  if (value.contract !== "nana-space-gateway/v1")
    return error("GATEWAY_VERSION_UNSUPPORTED");
  if (value.subject_id !== expectedIdentity)
    return error("SUBJECT_IDENTITY_MISMATCH");
  if (value.projection !== "INSPECTOR")
    return error("GATEWAY_PROJECTION_UNSUPPORTED");
  if (value.execution_authority !== false)
    return error("GATEWAY_PERMISSION_DENIED");
  if (
    Object.keys(value).some(
      (key) =>
        ![
          "contract",
          "subject_id",
          "projection",
          "execution_authority",
          "data",
        ].includes(key),
    )
  )
    return error("GATEWAY_RESPONSE_UNKNOWN_FIELD");
  return {
    contract: "nana-space-gateway/v1",
    subject_id: expectedIdentity,
    projection: "INSPECTOR",
    execution_authority: false,
    data: parseInspectorSnapshot(value.data, expectedIdentity),
  };
}
export class PlannedGatewayAdapter {
  readonly kind = "planned-core-gateway";
  readonly maturity = "PLANNED";
  readonly enabled = false;
  readonly executionAuthority = false;
  async load(
    _configuration?: GatewayConfiguration,
    signal?: AbortSignal,
  ): Promise<InspectorSnapshot> {
    assertActive(signal);
    // No fetch: deployment, authentication, recipient policy are not implemented.
    throw new AdapterError(
      "GATEWAY_NOT_IMPLEMENTED",
      "Core 已有 Python 投影。浏览器 Gateway 与会话授权仍待正式实施，当前没有建立网络连接。",
    );
  }
}
export const plannedGateway = new PlannedGatewayAdapter();
