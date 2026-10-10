#!/usr/bin/env python3
"""Single schema DTOs and strict, non-normalizing runtime validation."""

import argparse
import hashlib
import json
from pathlib import Path


def ts(schema):
    if schema is True or schema == {}:
        return "unknown"
    if schema is False:
        return "never"
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[1]
    if "const" in schema:
        return json.dumps(schema["const"], ensure_ascii=False)
    if "enum" in schema:
        return " | ".join(json.dumps(v, ensure_ascii=False) for v in schema["enum"])
    for key in ("anyOf", "oneOf"):
        if key in schema:
            return " | ".join(ts(v) for v in schema[key])
    kind = schema.get("type")
    if isinstance(kind, list):
        return " | ".join(ts({**schema, "type": value}) for value in kind)
    if kind == "null":
        return "null"
    if kind in ("number", "integer"):
        return "number"
    if kind in ("boolean", "string"):
        return kind
    if kind == "array":
        return "Array<" + ts(schema["items"]) + ">"
    if kind == "object":
        if "properties" not in schema:
            extra = schema.get("additionalProperties", True)
            return "{ [key: string]: " + (ts(extra) if isinstance(extra, dict) else "unknown") + " }"
        required = schema.get("required", [])
        return "{ " + "; ".join(json.dumps(k) + ("" if k in required else "?") + ": " + ts(v) for k, v in schema["properties"].items()) + " }"
    if schema is True or schema == {}:
        return "unknown"
    if schema is False:
        return "never"
    raise ValueError("Unsupported type schema node " + repr(schema))


RUNTIME = r'''
type Schema = { [key: string]: any } | boolean;
const own = (value: object, key: string) => Object.prototype.hasOwnProperty.call(value, key);
function sameJson(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v,i) => sameJson(v,b[i]));
  if (a && b && typeof a === "object" && typeof b === "object" && !Array.isArray(a) && !Array.isArray(b)) {
    const keys=Object.keys(a); return keys.length===Object.keys(b).length && keys.every(k=>own(b,k)&&sameJson((a as Record<string,unknown>)[k],(b as Record<string,unknown>)[k]));
  }
  return false;
}
// Reject values JSON cannot faithfully carry, even inside inert arbitrary content.
function isJson(value: unknown, stack = new Set<object>()): boolean {
  if (value === null || typeof value === "string" || typeof value === "boolean") return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (!value || typeof value !== "object" || stack.has(value) || Object.getOwnPropertySymbols(value).length) return false;
  if (!Array.isArray(value) && Object.getPrototypeOf(value)!==Object.prototype && Object.getPrototypeOf(value)!==null) return false;
  stack.add(value);
  let valid: boolean;
  if (Array.isArray(value)) valid=Object.keys(value).length===value.length && Object.getOwnPropertyNames(value).length===value.length+1 && Array.from({length:value.length},(_,i)=>{const d=Object.getOwnPropertyDescriptor(value,String(i));return !!d&&own(d,"value")&&isJson(d.value,stack);}).every(Boolean);
  else valid=Object.keys(value).length===Object.getOwnPropertyNames(value).length && Object.keys(value).every(k=>{const d=Object.getOwnPropertyDescriptor(value,k);return !!d&&own(d,"value")&&isJson(d.value,stack);});
  stack.delete(value); return valid;
}
function validate(node: Schema, value: unknown): boolean {
  if (node===true) return true;
  if (node===false) return false;
  if (node.$ref) {
    const name=node.$ref.replace(/^#\/\$defs\//,"");
    if (!own(definitions,name) || !validate(definitions[name],value)) return false;
  }
  if (own(node,"const") && !sameJson(node.const,value)) return false;
  if (node.enum && !node.enum.some((v:unknown)=>sameJson(v,value))) return false;
  if (node.anyOf && !node.anyOf.some((child:Schema)=>validate(child,value))) return false;
  if (node.oneOf && node.oneOf.filter((child:Schema)=>validate(child,value)).length!==1) return false;
  if (node.allOf && !node.allOf.every((child:Schema)=>validate(child,value))) return false;
  if (node.not && validate(node.not,value)) return false;
  if (Array.isArray(node.type)) {
    if (!node.type.some((type:string)=>validate({...node,type},value))) return false;
  } else if (node.type) {
    switch(node.type) {
      case "null": if(value!==null)return false;break;
      case "boolean": if(typeof value!=="boolean")return false;break;
      case "number": if(typeof value!=="number"||!Number.isFinite(value))return false;break;
      case "integer": if(typeof value!=="number"||!Number.isSafeInteger(value))return false;break;
      case "string": if(typeof value!=="string")return false;break;
      case "array": if(!Array.isArray(value))return false;break;
      case "object": if(!value||typeof value!=="object"||Array.isArray(value))return false;break;
      default: return false;
    }
  }
  if (typeof value==="number") {
    if(node.minimum!==undefined&&value<node.minimum)return false;
    if(node.maximum!==undefined&&value>node.maximum)return false;
    if(node.exclusiveMinimum!==undefined&&value<=node.exclusiveMinimum)return false;
    if(node.exclusiveMaximum!==undefined&&value>=node.exclusiveMaximum)return false;
    if(node.multipleOf!==undefined&&!Number.isInteger(value/node.multipleOf))return false;
  }
  if (typeof value==="string") {
    const length=Array.from(value).length;
    if(node.minLength!==undefined&&length<node.minLength)return false;
    if(node.maxLength!==undefined&&length>node.maxLength)return false;
    if(node.pattern!==undefined&&!new RegExp(node.pattern,"u").test(value))return false;
  }
  if (Array.isArray(value)) {
    if(node.minItems!==undefined&&value.length<node.minItems)return false;
    if(node.maxItems!==undefined&&value.length>node.maxItems)return false;
    if(node.items!==undefined&&!value.every(v=>validate(node.items,v)))return false;
    if(node.uniqueItems&&value.some((v,i)=>value.slice(0,i).some(p=>sameJson(v,p))))return false;
  }
  if(value&&typeof value==="object"&&!Array.isArray(value)) {
    const keys=Object.keys(value),properties=node.properties??{};
    if(node.minProperties!==undefined&&keys.length<node.minProperties)return false;
    if(node.maxProperties!==undefined&&keys.length>node.maxProperties)return false;
    if(node.required&&!node.required.every((k:string)=>own(value,k)))return false;
    for (const key of keys) {
      const item=(value as Record<string,unknown>)[key];
      if(own(properties,key)) {if(!validate(properties[key],item))return false;}
      else if(node.additionalProperties===false)return false;
      else if(typeof node.additionalProperties==="object"&&!validate(node.additionalProperties,item))return false;
    }
  }
  return true;
}
export function assertAiAssetDto<T>(name: keyof AiAssetDtoByName, value: unknown): T {
  let valid=false;
  try { valid=own(definitions,name)&&isJson(value)&&validate(definitions[name],value); } catch { valid=false; }
  if(!valid) throw new Error(`Invalid AI asset contract: ${name}`);
  return value as T;
}
'''


def verify_keywords(node):
    if isinstance(node, bool):
        return
    supported = {"$ref", "$comment", "title", "description", "default", "examples", "type", "const", "enum", "anyOf", "oneOf", "allOf", "not", "properties", "required", "additionalProperties", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength", "pattern", "items", "minItems", "maxItems", "uniqueItems", "minProperties", "maxProperties"}
    unknown = set(node) - supported
    if unknown:
        raise ValueError("Unsupported schema keywords: " + repr(sorted(unknown)))
    for key in ("anyOf", "oneOf", "allOf"):
        for child in node.get(key, []):
            verify_keywords(child)
    for child in node.get("properties", {}).values():
        verify_keywords(child)
    for key in ("not", "items", "additionalProperties"):
        if isinstance(node.get(key), (dict, bool)):
            verify_keywords(node[key])
    if "$ref" in node and not node["$ref"].startswith("#/$defs/"):
        raise ValueError("Only local $defs references are supported")


def generate(root):
    source = root / "packages/contracts/v2/ai-asset.schema.json"
    raw = source.read_bytes()
    schema = json.loads(raw)
    definitions = schema["$defs"]
    for node in definitions.values():
        verify_keywords(node)
    content = "// GENERATED from packages/contracts/v2/ai-asset.schema.json. Do not hand edit.\n// Schema SHA256: " + hashlib.sha256(raw).hexdigest() + "\n"
    content += "\n".join("export type " + name + " = " + ts(node) + ";" for name, node in definitions.items()) + "\n"
    content += "export type AiAssetDtoByName = { " + "; ".join(name + ": " + name for name in definitions) + " };\n"
    content += "const definitions: Record<string,Schema> = " + json.dumps(definitions, ensure_ascii=False, separators=(",", ":")) + ";\n"
    return content + RUNTIME


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = generate(args.root)
    target = args.root / "frontend/src/api/generated/ai-asset-contract.ts"
    if args.check:
        if not target.is_file() or target.read_text(encoding="utf-8") != content:
            raise SystemExit("generated AI asset contract drift")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
