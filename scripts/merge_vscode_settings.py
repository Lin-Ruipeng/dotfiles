"""Apply a JSON settings fragment while preserving JSONC comments and other keys."""
import argparse
import json
from pathlib import Path
import re

STRINGS_OR_COMMENTS = re.compile(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/')
STRINGS_OR_TRAILING_COMMAS = re.compile(r'"(?:\\.|[^"\\])*"|,(?=\s*[\]}])')
DECODER = json.JSONDecoder()


def parse_jsonc(text):
    def mask_comment(match):
        token = match.group()
        return token if token.startswith('"') else re.sub(r"[^\r\n]", " ", token)

    uncommented = STRINGS_OR_COMMENTS.sub(mask_comment, text)
    sanitized = STRINGS_OR_TRAILING_COMMAS.sub(
        lambda match: match.group() if match.group().startswith('"') else " ",
        uncommented,
    )
    value = json.loads(sanitized)
    if not isinstance(value, dict):
        raise ValueError("VS Code settings must be a JSON object")
    return sanitized, uncommented, value


def merge_settings(text, overlay):
    sanitized, uncommented, current = parse_jsonc(text)
    edits = []

    def skip_space(offset):
        while offset < len(sanitized) and sanitized[offset].isspace():
            offset += 1
        return offset

    def members(offset):
        offset = skip_space(offset)
        if sanitized[offset] != "{":
            raise ValueError("Expected a settings object")
        offset = skip_space(offset + 1)
        found = {}
        last_end = None
        while sanitized[offset] != "}":
            key_offset = offset
            key, offset = DECODER.raw_decode(sanitized, offset)
            offset = skip_space(offset)
            if sanitized[offset] != ":":
                raise ValueError("Expected ':' after a setting name")
            start = skip_space(offset + 1)
            value, end = DECODER.raw_decode(sanitized, start)
            found[key] = (start, end, value, key_offset)
            last_end = end
            offset = skip_space(end)
            if sanitized[offset] == ",":
                offset = skip_space(offset + 1)
        return found, offset, last_end

    def update_object(offset, patch):
        found, close, last_end = members(offset)
        missing = {}
        for key, value in patch.items():
            if key not in found:
                missing[key] = value
                continue
            start, end, previous, _ = found[key]
            if isinstance(value, dict) and isinstance(previous, dict):
                update_object(start, value)
            elif previous != value:
                edits.append((start, end, json.dumps(value, ensure_ascii=False)))

        if not missing:
            return
        close_line = text[text.rfind("\n", 0, close) + 1:close]
        close_indent = close_line if close_line.isspace() else ""
        if found:
            first_key = next(iter(found.values()))[3]
            key_line = text[text.rfind("\n", 0, first_key) + 1:first_key]
            indent = key_line if not key_line.strip() else close_indent + "    "
        else:
            indent = close_indent + "    "
        trailing_comma = last_end is not None and "," in uncommented[last_end:close]
        if last_end is not None and not trailing_comma:
            edits.append((last_end, last_end, ","))
        properties = []
        for key, value in missing.items():
            rendered = json.dumps(value, ensure_ascii=False, indent=4).replace("\n", "\n" + indent)
            properties.append(indent + json.dumps(key, ensure_ascii=False) + ": " + rendered)
        addition = "\n" + ",\n".join(properties)
        if trailing_comma:
            addition += ","
        addition += "\n" + close_indent
        edits.append((close, close, addition))

    update_object(skip_space(0), overlay)
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fragment", type=Path)
    parser.add_argument("settings", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        overlay = json.loads(args.fragment.read_text(encoding="utf-8"))
        if not isinstance(overlay, dict):
            raise ValueError("The settings fragment must be a JSON object")
        original = args.settings.read_text(encoding="utf-8") if args.settings.is_file() else "{}\n"
        merged = merge_settings(original, overlay)
        if args.check:
            print("unchanged" if merged == original else "changed")
        else:
            args.output.write_text(merged, encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot merge VS Code settings: {error}\n")


if __name__ == "__main__":
    main()
