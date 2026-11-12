/** Transient provider catalog pages. These do not attest model capabilities. */
export interface ModelCatalogPage {
  models: string[];
  truncated: boolean;
  nextAfterId?: string;
}
export interface ModelCatalog extends ModelCatalogPage {
  revision: number;
  requestedAfterIds: string[];
}
export const catalogDisplayLimit = 1024;
const modelId = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,95}$/;

export function readModelCatalog(value: unknown): ModelCatalogPage {
  const raw = value as Record<string, unknown> | null;
  if (!raw || !Array.isArray(raw.models) || raw.models.length > 256 ||
      !raw.models.every(id => typeof id === "string" && modelId.test(id)))
    throw new Error("服务商模型列表格式无效，请手动填写模型名称。");
  const next = raw.next_after_id;
  if (next != null && (typeof next !== "string" || !modelId.test(next) || raw.truncated !== true))
    throw new Error("服务商分页信息无效，请重新读取列表。");
  return {
    models: [...new Set(raw.models as string[])],
    // Older servers without completion metadata cannot attest a full catalog.
    truncated: raw.truncated !== false,
    ...(typeof next === "string" ? { nextAfterId: next } : {}),
  };
}

export function mergeModelCatalog(
  previous: ModelCatalog | undefined,
  page: ModelCatalogPage,
  revision: number,
  afterId?: string,
): ModelCatalog {
  if (afterId !== undefined && (!previous || previous.revision !== revision || previous.nextAfterId !== afterId))
    throw new Error("服务商配置已变化，请重新读取列表。");
  const requestedAfterIds = afterId ? [...previous!.requestedAfterIds, afterId] : [];
  if (page.nextAfterId && requestedAfterIds.includes(page.nextAfterId))
    throw new Error("服务商返回了重复页面，已保留读取结果；可以手动填写模型名称。");
  const models = [...new Set([...(afterId ? previous!.models : []), ...page.models])].sort();
  return {
    models: models.slice(0, catalogDisplayLimit),
    truncated: page.truncated || models.length > catalogDisplayLimit,
    nextAfterId: models.length < catalogDisplayLimit && requestedAfterIds.length < 15 ? page.nextAfterId : undefined,
    revision,
    requestedAfterIds,
  };
}
