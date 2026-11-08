"""Generate the canonical JSON Schema/OpenAPI and TypeScript declarations."""

import json
from pathlib import Path
from pydantic.json_schema import models_json_schema
from nana_core.life.live_api import contracts as c
from nana_core.life.live_api.provider_settings import ProviderConfigurationRequest, CredentialBindingRequest
from nana_core.life.live_api.platform_settings import PlatformConfigurationRequest
from nana_core.life.live_api.platform_credentials import PlatformCredentialRequest
from nana_core.life.live_api.memory_notes import MemoryNoteRequest

ROOT = Path(__file__).resolve().parents[2]
MODELS = [
    c.Binding,
    c.Envelope,
    c.Login,
    c.DeviceLogin,
    c.PairRequest,
    c.PairOffer,
    c.MessageRequest,
    c.LanguageFeedbackRequest,
    MemoryNoteRequest,
    c.CommandRequest,
    c.HostRequest,
    c.HostConfirmation,
    c.Receipt,
    ProviderConfigurationRequest,
    CredentialBindingRequest,
    PlatformConfigurationRequest,
    PlatformCredentialRequest,
]


def typescript(node):
    """JSON-schema projection for this finite DTO grammar, fail on new forms."""
    if node == {}:
        return "null | boolean | number | string | Array<JsonValue> | { [key: string]: JsonValue }"
    if "$ref" in node:
        return node["$ref"].rsplit("/", 1)[-1]
    if "const" in node:
        return json.dumps(node["const"])
    if "enum" in node:
        return " | ".join(json.dumps(x) for x in node["enum"])
    if "anyOf" in node:
        return "(" + " | ".join(typescript(x) for x in node["anyOf"]) + ")"
    kind = node.get("type")
    if kind == "null":
        return "null"
    if kind in {"integer", "number"}:
        return "number"
    if kind in {"string", "boolean"}:
        return kind
    if kind == "array":
        if "prefixItems" in node:
            return "[" + ", ".join(typescript(x) for x in node["prefixItems"]) + "]"
        return "Array<" + typescript(node["items"]) + ">"
    if kind == "object":
        if "properties" not in node:
            additional = node.get("additionalProperties", {})
            return "Record<string, " + (typescript(additional) if additional else "unknown") + ">"
        required = node.get("required", [])
        return (
            "{\n"
            + "\n".join(
                "  " + json.dumps(k) + ("" if k in required else "?") + ": " + typescript(v) + ";"
                for k, v in node["properties"].items()
            )
            + "\n}"
        )
    raise ValueError("UNSUPPORTED_SCHEMA_FORM")


def generate():
    _, schema = models_json_schema([(m, "validation") for m in MODELS], title=c.CONTRACT)
    out = ROOT / "contracts/nana-space-live-v2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "api-v2.schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    paths = {}
    for path, methods in {
        "/session": ["post", "delete"],
        "/bootstrap": ["get"],
        "/views/{domain}": ["get"],
        "/events": ["get"],
        "/messages": ["post"],
        "/memories/notes": ["post"],
        "/conversation/feedback": ["post"],
        "/receipts/{id}": ["get"],
        "/commands": ["post"],
        "/host/confirmations": ["post"],
        "/host/operations": ["get", "post"],
        "/device/pairing": ["post"],
        "/device/login": ["post"],
        "/session/native": ["post"],
        "/devices/offers": ["post"],
        "/devices": ["get"],
        "/devices/{id}": ["delete"],
        "/notifications": ["get"],
        "/providers/status": ["get"],
        "/providers/commands": ["post"],
        "/providers/credential": ["post"],
        "/backup/status": ["get"],
        "/conversation/history": ["get"],
        "/life/shares": ["get"],
        "/platform/bilibili": ["get"],
        "/platform/status": ["get"],
        "/platform/commands": ["post"],
        "/platform/credential": ["post"],
        "/privacy/withdrawal": ["post"],
    }.items():
        paths["/api/nana-space/v2" + path] = {
            m: {
                "responses": {
                    "200": {"description": "Typed sanitized envelope"},
                    "400": {"description": "Fail closed typed error"},
                }
            }
            for m in methods
        }
    request_models = {
        "/session": "Login",
        "/device/pairing": "PairRequest",
        "/device/login": "DeviceLogin",
        "/devices/offers": "PairOffer",
        "/messages": "MessageRequest",
        "/conversation/feedback": "LanguageFeedbackRequest",
        "/commands": "CommandRequest",
        "/providers/commands": "ProviderConfigurationRequest",
        "/providers/credential": "CredentialBindingRequest",
        "/platform/commands": "PlatformConfigurationRequest",
        "/platform/credential": "PlatformCredentialRequest",
        "/privacy/withdrawal": "CommandRequest",
        "/host/confirmations": "HostConfirmation",
        "/host/operations": "HostRequest",
    }
    for path, operations in paths.items():
        short = path.removeprefix("/api/nana-space/v2")
        for method, operation in operations.items():
            operation["security"] = [{"webCookie": []}, {"nativeBearer": []}]
            if short in {"/providers/credential", "/platform/credential"}:
                operation["security"] = [{"nativeBearer": []}]
                operation["description"] = "HOST_ADMIN + host opt-in. Native secure input only; no secret in JS, persistence or receipt."
            response = {"$ref": "#/components/schemas/Envelope"}
            if short in {"/device/pairing", "/device/login"}:
                response = {
                    "type": "object",
                    "required": ["contract", "subject_id", "lineage_binding", "realm", "device_id", "refresh_token"],
                    "properties": {
                        k: {"type": "string"}
                        for k in ["contract", "subject_id", "lineage_binding", "realm", "device_id", "refresh_token"]
                    },
                    "description": "Native-only credential exchange; never forwarded to WebView JS",
                }
            if short == "/session/native":
                response = {
                    "type": "object",
                    "properties": {
                        "contract": {"type": "string"},
                        "access_token": {"type": "string"},
                        "expires_in": {"type": "integer"},
                    },
                    "required": ["contract", "access_token", "expires_in"],
                    "description": "Native-only memory access session",
                }
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["device_id", "subject_id", "refresh_token"],
                                "properties": {
                                    k: {"type": "string"} for k in ["device_id", "subject_id", "refresh_token"]
                                },
                            }
                        }
                    },
                }
            if method == "post" and short in request_models:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/" + request_models[short]}}
                    },
                }
            if method == "post" and short in {"/session", "/device/pairing", "/device/login", "/session/native"}:
                operation["security"] = []
            operation["responses"]["200"]["content"] = {"application/json": {"schema": response}}
            if "{" in short:
                name = short.split("{")[1].split("}")[0]
                operation["parameters"] = [{"name": name, "in": "path", "required": True, "schema": {"type": "string"}}]
            if short == "/events":
                operation["parameters"] = [{"name": "cursor", "in": "query", "schema": {"type": "string"}}]
    doc = {
        "openapi": "3.1.0",
        "info": {"title": c.CONTRACT, "version": "2.0.0"},
        "paths": paths,
        "components": {
            "schemas": schema["$defs"],
            "securitySchemes": {
                "webCookie": {"type": "apiKey", "in": "cookie", "name": "__Host-nana_v2"},
                "nativeBearer": {"type": "http", "scheme": "bearer"},
            },
        },
    }
    (out / "openapi.json").write_text(json.dumps(doc, indent=2).replace("#/$defs/", "#/components/schemas/") + "\n")
    declarations = "// Generated by tools.nana_first_life_android_v2.schema; do not edit.\n"
    declarations += "\n".join(
        "export type " + name + " = " + typescript(value) + ";\n" for name, value in schema["$defs"].items()
    )
    target = ROOT / "apps/nana-space/src/data/v2.generated.ts"
    target.write_text(declarations)
    return schema


if __name__ == "__main__":
    generate()
