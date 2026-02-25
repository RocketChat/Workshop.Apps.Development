#!/usr/bin/env python3
"""
Workshop room weekly management for Rocket.Chat.

Capabilities:
- Select top N unique usernames from an input file.
- Skip usernames already invited in earlier weeks.
- Move last week's invited users to an archive room (or kick if no archive room).
- Optionally clear room messages.
- Persist invite history and index by username.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_WELCOME_MESSAGE = """Hey everyone! 👋

Welcome to the RC Apps AI Workshop onboarding channel. Glad to have you here.

To get started:
1) Join the workspace (if you haven't already):
https://safe.dev.rocket.chat/register/FSWsAEpirrrUtck7Du

2) Check the challenge assignment here:
https://safe.dev.rocket.chat/group/Challenge_Wave_1

Please try to complete the challenge as soon as possible, since we'll be prioritizing participants who finish early for the workshop (dates TBA).

If you run into any issues joining the workspace or accessing the challenge, just drop a message here.
Looking forward to seeing what you build 🚀"""


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_week_label() -> str:
    year, week_number, _ = datetime.now().isocalendar()
    return f"{year}-W{week_number:02d}"


def normalize_username(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    username = value.strip()
    if username.startswith("@"):
        username = username[1:]
    username = username.strip().lower()
    if not username or " " in username:
        return None
    if not USERNAME_RE.match(username):
        return None
    return username


def unique_preserve_order(values: Sequence[str]) -> List[str]:
    output: List[str] = []
    seen = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def extract_usernames_from_json(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            out.extend(extract_usernames_from_json(item))
        return out
    if isinstance(value, dict):
        out = []
        if "username" in value:
            out.extend(extract_usernames_from_json(value["username"]))
        if "usernames" in value:
            out.extend(extract_usernames_from_json(value["usernames"]))
        if "entries" in value:
            out.extend(extract_usernames_from_json(value["entries"]))
        return out
    return []


def load_usernames_from_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Usernames file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".txt", ".list"}:
        lines = path.read_text(encoding="utf-8").splitlines()
        usernames = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
        return usernames

    if suffix == ".csv":
        usernames: List[str] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
        if not rows:
            return usernames

        first_row = [col.strip().lower() for col in rows[0]]
        has_header = bool(first_row) and first_row[0] in {"username", "usernames", "user"}
        data_rows = rows[1:] if has_header else rows

        for row in data_rows:
            if not row:
                continue
            usernames.append(row[0].strip())
        return usernames

    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return extract_usernames_from_json(data)

    raise ValueError(f"Unsupported usernames file format: {path.suffix}. Use .txt, .csv, or .json")


def parse_csv_list(value: str | None) -> List[str]:
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path} ({exc})") from exc


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def ensure_state(state: Any) -> Dict[str, Any]:
    if not isinstance(state, dict):
        state = {}
    if not isinstance(state.get("batches"), list):
        state["batches"] = []
    if not isinstance(state.get("invited_index"), dict):
        state["invited_index"] = {}
    state.setdefault("version", 1)
    return state


def error_to_text(error_data: Any) -> str:
    if isinstance(error_data, dict):
        if isinstance(error_data.get("error"), str):
            return error_data["error"]
        if isinstance(error_data.get("message"), str):
            return error_data["message"]
        if isinstance(error_data.get("errorType"), str):
            return error_data["errorType"]
        return json.dumps(error_data)
    return str(error_data)


def is_already_member_error(error_data: Any) -> bool:
    text = error_to_text(error_data).lower()
    return "already" in text and any(keyword in text for keyword in ("room", "channel", "group", "joined"))


class RocketChatClient:
    def __init__(self, base_url: str, auth_token: str, user_id: str, timeout_seconds: int = 30):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.user_id = user_id
        self.timeout_seconds = timeout_seconds

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "X-Auth-Token": self.auth_token,
            "X-User-Id": self.user_id,
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, Any] | None = None,
        payload: Dict[str, Any] | None = None,
    ) -> Tuple[bool, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.RequestException as exc:
            return False, {"error": str(exc)}

        try:
            body = response.json()
        except ValueError:
            body = {"error": response.text or f"HTTP {response.status_code}"}

        if response.status_code >= 400:
            return False, body
        return True, body

    @staticmethod
    def endpoint_prefix(room_kind: str) -> str:
        if room_kind == "channel":
            return "channels"
        return "groups"

    def detect_room_kind(self, room_id: str) -> str:
        ok, data = self.request("GET", "/api/v1/rooms.info", params={"roomId": room_id})
        if ok:
            room = data.get("room", {})
            room_type = room.get("t")
            if room_type == "c":
                return "channel"
            if room_type == "p":
                return "group"

        # Fallback for servers where rooms.info may be restricted.
        ok_group, _ = self.request("GET", "/api/v1/groups.info", params={"roomId": room_id})
        if ok_group:
            return "group"
        ok_channel, _ = self.request("GET", "/api/v1/channels.info", params={"roomId": room_id})
        if ok_channel:
            return "channel"
        raise RuntimeError(f"Failed to detect room type for roomId={room_id}.")

    def get_user_id_by_username(self, username: str) -> str | None:
        ok, data = self.request("GET", "/api/v1/users.info", params={"username": username})
        if not ok:
            return None
        user = data.get("user", {})
        user_id = user.get("_id")
        if isinstance(user_id, str) and user_id:
            return user_id
        return None

    def list_room_members(self, room_id: str, room_kind: str) -> List[Dict[str, Any]]:
        members: List[Dict[str, Any]] = []
        offset = 0
        page_size = 100
        prefix = self.endpoint_prefix(room_kind)

        while True:
            ok, data = self.request(
                "GET",
                f"/api/v1/{prefix}.members",
                params={"roomId": room_id, "offset": offset, "count": page_size},
            )
            if not ok:
                raise RuntimeError(f"Failed to fetch members: {error_to_text(data)}")

            batch = data.get("members", [])
            if not isinstance(batch, list):
                break

            members.extend(batch)
            if len(batch) < page_size:
                break

            offset += len(batch)
            total = data.get("total")
            if isinstance(total, int) and offset >= total:
                break

        return members

    def invite_user(
        self,
        room_id: str,
        room_kind: str,
        *,
        user_id: str | None = None,
        username: str | None = None,
    ) -> Tuple[bool, Any]:
        prefix = self.endpoint_prefix(room_kind)

        # Prefer userId for better compatibility across Rocket.Chat versions.
        if user_id:
            ok, data = self.request(
                "POST",
                f"/api/v1/{prefix}.invite",
                payload={"roomId": room_id, "userId": user_id},
            )
            if ok or is_already_member_error(data):
                return True, data

        if username:
            # Fallback for servers that still support username payload.
            ok, data = self.request(
                "POST",
                f"/api/v1/{prefix}.invite",
                payload={"roomId": room_id, "username": username},
            )
            if ok or is_already_member_error(data):
                return True, data
            return False, data

        return False, {"error": "No user_id or username provided for invite."}

    def invite_username(self, room_id: str, room_kind: str, username: str) -> Tuple[bool, Any]:
        user_id = self.get_user_id_by_username(username)
        return self.invite_user(room_id, room_kind, user_id=user_id, username=username)

    def kick_user(self, room_id: str, room_kind: str, target_user_id: str) -> Tuple[bool, Any]:
        prefix = self.endpoint_prefix(room_kind)
        return self.request(
            "POST",
            f"/api/v1/{prefix}.kick",
            payload={"roomId": room_id, "userId": target_user_id},
        )

    def list_room_message_ids(self, room_id: str, room_kind: str, max_messages: int) -> List[str]:
        offset = 0
        page_size = 100
        message_ids: List[str] = []
        prefix = self.endpoint_prefix(room_kind)

        while len(message_ids) < max_messages:
            count = min(page_size, max_messages - len(message_ids))
            ok, data = self.request(
                "GET",
                f"/api/v1/{prefix}.history",
                params={"roomId": room_id, "offset": offset, "count": count},
            )
            if not ok:
                raise RuntimeError(f"Failed to fetch history: {error_to_text(data)}")

            batch = data.get("messages", [])
            if not isinstance(batch, list) or not batch:
                break

            for message in batch:
                msg_id = message.get("_id")
                if isinstance(msg_id, str):
                    message_ids.append(msg_id)
                    if len(message_ids) >= max_messages:
                        break

            if len(batch) < count:
                break

            offset += len(batch)
            total = data.get("total")
            if isinstance(total, int) and offset >= total:
                break

        return message_ids

    def delete_message(self, room_id: str, msg_id: str) -> Tuple[bool, Any]:
        return self.request(
            "POST",
            "/api/v1/chat.delete",
            payload={"roomId": room_id, "msgId": msg_id, "asUser": False},
        )

    def post_message(self, room_id: str, text: str) -> Tuple[bool, Any]:
        return self.request(
            "POST",
            "/api/v1/chat.postMessage",
            payload={"roomId": room_id, "text": text},
        )


def select_usernames(
    source_usernames: Sequence[str],
    invited_index: Dict[str, Any],
    limit: int,
) -> Dict[str, List[str]]:
    selected: List[str] = []
    skipped_already_invited: List[str] = []
    skipped_duplicate_input: List[str] = []
    skipped_invalid: List[str] = []
    seen_input = set()

    for raw_username in source_usernames:
        normalized = normalize_username(raw_username)
        if not normalized:
            skipped_invalid.append(str(raw_username))
            continue
        if normalized in seen_input:
            skipped_duplicate_input.append(normalized)
            continue
        seen_input.add(normalized)
        if normalized in invited_index:
            skipped_already_invited.append(normalized)
            continue

        selected.append(normalized)
        if len(selected) >= limit:
            break

    return {
        "selected": selected,
        "skipped_already_invited": unique_preserve_order(skipped_already_invited),
        "skipped_duplicate_input": unique_preserve_order(skipped_duplicate_input),
        "skipped_invalid": unique_preserve_order(skipped_invalid),
    }


def find_previous_batch_for_room(state: Dict[str, Any], room_id: str, week_label: str | None = None) -> Dict[str, Any] | None:
    for batch in reversed(state.get("batches", [])):
        if batch.get("room_id") != room_id:
            continue
        if week_label and batch.get("week_label") != week_label:
            continue
        invited_success = batch.get("invited_success", [])
        if isinstance(invited_success, list):
            return batch
    return None


def kick_usernames(
    client: RocketChatClient,
    room_id: str,
    room_kind: str,
    usernames: Sequence[str],
    protected_usernames: Sequence[str],
    *,
    dry_run: bool,
    pause_seconds: float,
) -> Dict[str, Any]:
    protected_set = {normalize_username(u) for u in protected_usernames if normalize_username(u)}
    members = client.list_room_members(room_id, room_kind)
    members_by_username: Dict[str, Dict[str, Any]] = {}
    for member in members:
        normalized = normalize_username(member.get("username"))
        if normalized:
            members_by_username[normalized] = member

    kicked: List[str] = []
    failed: List[Dict[str, str]] = []
    not_found: List[str] = []
    skipped_protected: List[str] = []

    for username in usernames:
        normalized = normalize_username(username)
        if not normalized:
            continue
        if normalized in protected_set:
            skipped_protected.append(normalized)
            continue
        member = members_by_username.get(normalized)
        if not member:
            not_found.append(normalized)
            continue
        if dry_run:
            kicked.append(normalized)
            continue

        ok, response = client.kick_user(room_id, room_kind, member.get("_id", ""))
        if ok:
            kicked.append(normalized)
        else:
            failed.append({"username": normalized, "error": error_to_text(response)})
        if pause_seconds > 0:
            time.sleep(pause_seconds)

    return {
        "kicked": unique_preserve_order(kicked),
        "failed": failed,
        "not_found": unique_preserve_order(not_found),
        "skipped_protected": unique_preserve_order(skipped_protected),
    }


def move_usernames_to_room(
    client: RocketChatClient,
    source_room_id: str,
    source_room_kind: str,
    destination_room_id: str,
    destination_room_kind: str,
    usernames: Sequence[str],
    protected_usernames: Sequence[str],
    *,
    dry_run: bool,
    pause_seconds: float,
) -> Dict[str, Any]:
    protected_set = {normalize_username(u) for u in protected_usernames if normalize_username(u)}
    members = client.list_room_members(source_room_id, source_room_kind)
    members_by_username: Dict[str, Dict[str, Any]] = {}
    for member in members:
        normalized = normalize_username(member.get("username"))
        if normalized:
            members_by_username[normalized] = member

    moved: List[str] = []
    failed: List[Dict[str, str]] = []
    not_found: List[str] = []
    skipped_protected: List[str] = []

    for username in usernames:
        normalized = normalize_username(username)
        if not normalized:
            continue
        if normalized in protected_set:
            skipped_protected.append(normalized)
            continue

        member = members_by_username.get(normalized)
        if not member:
            not_found.append(normalized)
            continue
        member_id = member.get("_id", "")
        if not member_id:
            failed.append({"username": normalized, "error": "Missing member ID in source room."})
            continue

        if dry_run:
            moved.append(normalized)
            continue

        invited, invite_response = client.invite_user(
            destination_room_id,
            destination_room_kind,
            user_id=member_id,
            username=normalized,
        )
        if not invited:
            failed.append({"username": normalized, "error": f"Archive invite failed: {error_to_text(invite_response)}"})
            continue

        kicked, kick_response = client.kick_user(source_room_id, source_room_kind, member_id)
        if kicked:
            moved.append(normalized)
        else:
            failed.append(
                {"username": normalized, "error": f"Source room removal failed: {error_to_text(kick_response)}"}
            )

        if pause_seconds > 0:
            time.sleep(pause_seconds)

    return {
        "moved": unique_preserve_order(moved),
        "move_failed": failed,
        "move_not_found": unique_preserve_order(not_found),
        "move_skipped_protected": unique_preserve_order(skipped_protected),
    }


def clear_messages(
    client: RocketChatClient,
    room_id: str,
    room_kind: str,
    max_messages: int,
    *,
    dry_run: bool,
    pause_seconds: float,
) -> Dict[str, Any]:
    message_ids = client.list_room_message_ids(room_id, room_kind, max_messages=max_messages)
    if dry_run:
        return {"candidate_count": len(message_ids), "deleted_count": len(message_ids), "failed": []}

    deleted_count = 0
    failed: List[Dict[str, str]] = []
    for msg_id in message_ids:
        ok, response = client.delete_message(room_id, msg_id)
        if ok:
            deleted_count += 1
        else:
            failed.append({"msg_id": msg_id, "error": error_to_text(response)})
        if pause_seconds > 0:
            time.sleep(pause_seconds)
    return {"candidate_count": len(message_ids), "deleted_count": deleted_count, "failed": failed}


def update_state_with_batch(state: Dict[str, Any], batch: Dict[str, Any]) -> None:
    state["batches"].append(batch)
    invited_index = state["invited_index"]

    invited_success = batch.get("invited_success", [])
    week_label = batch.get("week_label", "")
    invited_at = batch.get("invited_at", now_iso_utc())

    for username in invited_success:
        entry = invited_index.get(username)
        if not isinstance(entry, dict):
            entry = {
                "first_invited_at": invited_at,
                "last_invited_at": invited_at,
                "invite_count": 0,
                "weeks": [],
            }
        entry["last_invited_at"] = invited_at
        entry["invite_count"] = int(entry.get("invite_count", 0)) + 1

        weeks = entry.get("weeks")
        if not isinstance(weeks, list):
            weeks = []
        if week_label and week_label not in weeks:
            weeks.append(week_label)
        entry["weeks"] = weeks
        invited_index[username] = entry


def require_credentials() -> Tuple[str, str]:
    auth_token = os.getenv("RC_TOKEN") or os.getenv("RC_AUTH_TOKEN") or os.getenv("RC_AUTH_TOKEN_1")
    user_id = os.getenv("RC_UID") or os.getenv("RC_USER_ID") or os.getenv("RC_USER_ID_1")

    if not auth_token or not user_id:
        raise RuntimeError(
            "Missing credentials. Set RC_TOKEN/RC_UID or RC_AUTH_TOKEN/RC_USER_ID in your environment."
        )
    return auth_token, user_id


def print_selection_summary(selection: Dict[str, List[str]], limit: int) -> None:
    selected = selection["selected"]
    skipped_already_invited = selection["skipped_already_invited"]
    skipped_duplicate_input = selection["skipped_duplicate_input"]
    skipped_invalid = selection["skipped_invalid"]

    print(f"Selected {len(selected)} username(s) for invite (limit {limit}).")
    if selected:
        print("Invite list:", ", ".join(selected))
    if skipped_already_invited:
        print(f"Skipped already invited ({len(skipped_already_invited)}): {', '.join(skipped_already_invited)}")
    if skipped_duplicate_input:
        print(f"Skipped duplicate input ({len(skipped_duplicate_input)}): {', '.join(skipped_duplicate_input)}")
    if skipped_invalid:
        print(f"Skipped invalid usernames ({len(skipped_invalid)}): {', '.join(skipped_invalid)}")


def load_config(config_path: Path, strict: bool) -> Dict[str, Any]:
    if not config_path.exists():
        if strict:
            raise FileNotFoundError(f"Config file not found: {config_path}")
        return {}
    return load_json(config_path, default={})


def resolve_state_path(config_path: Path, explicit_state_file: str | None, config_state_file: str | None) -> Path:
    state_file = explicit_state_file or config_state_file or "workshop_state.json"
    path = Path(state_file)
    if path.is_absolute():
        return path
    return (config_path.parent / path).resolve()


def resolve_settings(args: argparse.Namespace, config: Dict[str, Any], config_path: Path) -> Dict[str, Any]:
    room_id = args.room_id or config.get("room_id") or os.getenv("RC_RID")
    archive_room_id = args.archive_room_id or config.get("archive_room_id") or os.getenv("RC_ARCHIVE_RID")
    base_url = args.base_url or config.get("base_url") or os.getenv("RC_URL") or "https://open.rocket.chat"
    state_path = resolve_state_path(config_path, args.state_file, config.get("state_file"))
    arg_limit = getattr(args, "limit", None)
    weekly_invite_count = arg_limit if arg_limit is not None else int(config.get("weekly_invite_count", 15))
    pause_seconds = (
        args.pause_seconds if args.pause_seconds is not None else float(config.get("request_pause_seconds", 0.2))
    )

    protected = (
        parse_csv_list(args.protected_usernames)
        if args.protected_usernames is not None
        else config.get("protected_usernames", [])
    )
    protected_usernames = []
    for username in protected:
        normalized = normalize_username(username)
        if normalized:
            protected_usernames.append(normalized)

    return {
        "room_id": room_id,
        "archive_room_id": archive_room_id,
        "base_url": base_url.rstrip("/"),
        "state_path": state_path,
        "weekly_invite_count": weekly_invite_count,
        "pause_seconds": max(0.0, pause_seconds),
        "protected_usernames": unique_preserve_order(protected_usernames),
        "welcome_message": config.get("welcome_message", DEFAULT_WELCOME_MESSAGE),
        "send_welcome_message": bool(config.get("send_welcome_message", True)),
    }


def command_preview(args: argparse.Namespace, settings: Dict[str, Any], state: Dict[str, Any]) -> int:
    source_path = Path(args.source).expanduser()
    source_usernames = load_usernames_from_file(source_path)
    selection = select_usernames(source_usernames, state["invited_index"], settings["weekly_invite_count"])
    print_selection_summary(selection, settings["weekly_invite_count"])
    return 0


def command_cleanup(args: argparse.Namespace, settings: Dict[str, Any], state: Dict[str, Any]) -> int:
    room_id = settings["room_id"]
    if not room_id:
        raise RuntimeError("Missing room id. Set RC_RID, --room-id, or room_id in workshop_config.json.")
    archive_room_id = settings["archive_room_id"]
    if archive_room_id and archive_room_id == room_id:
        raise RuntimeError("archive_room_id cannot be the same as room_id.")

    auth_token, user_id = require_credentials()
    client = RocketChatClient(settings["base_url"], auth_token, user_id)
    room_kind = client.detect_room_kind(room_id)
    print(f"Detected room type: {room_kind}")
    archive_room_kind = None
    if archive_room_id:
        archive_room_kind = client.detect_room_kind(archive_room_id)
        print(f"Detected archive room type: {archive_room_kind}")

    target_batch = find_previous_batch_for_room(state, room_id, week_label=args.week)
    if not target_batch:
        print("No previous invite batch found for this room. Nothing to move/kick.")
        usernames_to_kick = []
    else:
        usernames_to_kick = target_batch.get("invited_success", [])

    if usernames_to_kick:
        if archive_room_id and archive_room_kind:
            print(f"Moving up to {len(usernames_to_kick)} user(s) from workshop room to archive room...")
            move_result = move_usernames_to_room(
                client,
                room_id,
                room_kind,
                archive_room_id,
                archive_room_kind,
                usernames_to_kick,
                settings["protected_usernames"],
                dry_run=args.dry_run,
                pause_seconds=settings["pause_seconds"],
            )
            print(
                f"Moved: {len(move_result['moved'])}, "
                f"failed: {len(move_result['move_failed'])}, "
                f"not found: {len(move_result['move_not_found'])}, "
                f"protected: {len(move_result['move_skipped_protected'])}"
            )
        else:
            print(f"Kicking up to {len(usernames_to_kick)} user(s) from previous batch...")
            kick_result = kick_usernames(
                client,
                room_id,
                room_kind,
                usernames_to_kick,
                settings["protected_usernames"],
                dry_run=args.dry_run,
                pause_seconds=settings["pause_seconds"],
            )
            print(
                f"Kicked: {len(kick_result['kicked'])}, "
                f"failed: {len(kick_result['failed'])}, "
                f"not found: {len(kick_result['not_found'])}, "
                f"protected: {len(kick_result['skipped_protected'])}"
            )
    else:
        print("No users to kick.")

    if args.clear_messages:
        print(f"Clearing up to {args.max_messages} message(s) from room history...")
        clear_result = clear_messages(
            client,
            room_id,
            room_kind,
            args.max_messages,
            dry_run=args.dry_run,
            pause_seconds=settings["pause_seconds"],
        )
        print(
            f"Messages considered: {clear_result['candidate_count']}, "
            f"deleted: {clear_result['deleted_count']}, "
            f"failed: {len(clear_result['failed'])}"
        )

    return 0


def command_rotate(args: argparse.Namespace, settings: Dict[str, Any], state: Dict[str, Any]) -> int:
    room_id = settings["room_id"]
    if not room_id:
        raise RuntimeError("Missing room id. Set RC_RID, --room-id, or room_id in workshop_config.json.")
    archive_room_id = settings["archive_room_id"]
    if archive_room_id and archive_room_id == room_id:
        raise RuntimeError("archive_room_id cannot be the same as room_id.")

    source_path = Path(args.source).expanduser()
    source_usernames = load_usernames_from_file(source_path)
    selection = select_usernames(source_usernames, state["invited_index"], settings["weekly_invite_count"])

    print_selection_summary(selection, settings["weekly_invite_count"])

    week_label = args.week or default_week_label()
    auth_token, user_id = require_credentials()
    client = RocketChatClient(settings["base_url"], auth_token, user_id)
    room_kind = client.detect_room_kind(room_id)
    print(f"Detected room type: {room_kind}")
    archive_room_kind = None
    if archive_room_id:
        archive_room_kind = client.detect_room_kind(archive_room_id)
        print(f"Detected archive room type: {archive_room_kind}")

    cleanup_result = {
        "archive_room_id": archive_room_id,
        "kicked": [],
        "failed": [],
        "not_found": [],
        "skipped_protected": [],
        "moved": [],
        "move_failed": [],
        "move_not_found": [],
        "move_skipped_protected": [],
        "messages_considered": 0,
        "messages_deleted": 0,
        "message_delete_failures": [],
    }

    if not args.skip_kick:
        previous_batch = find_previous_batch_for_room(state, room_id)
        if previous_batch:
            previous_usernames = previous_batch.get("invited_success", [])
            if previous_usernames:
                if archive_room_id and archive_room_kind:
                    print(f"Moving previous batch users ({len(previous_usernames)}) to archive room...")
                    move_result = move_usernames_to_room(
                        client,
                        room_id,
                        room_kind,
                        archive_room_id,
                        archive_room_kind,
                        previous_usernames,
                        settings["protected_usernames"],
                        dry_run=args.dry_run,
                        pause_seconds=settings["pause_seconds"],
                    )
                    cleanup_result.update(move_result)
                    print(
                        f"Moved: {len(move_result['moved'])}, "
                        f"failed: {len(move_result['move_failed'])}, "
                        f"not found: {len(move_result['move_not_found'])}, "
                        f"protected: {len(move_result['move_skipped_protected'])}"
                    )
                else:
                    print(f"Kicking previous batch users ({len(previous_usernames)})...")
                    kick_result = kick_usernames(
                        client,
                        room_id,
                        room_kind,
                        previous_usernames,
                        settings["protected_usernames"],
                        dry_run=args.dry_run,
                        pause_seconds=settings["pause_seconds"],
                    )
                    cleanup_result.update(kick_result)
                    print(
                        f"Kicked: {len(kick_result['kicked'])}, "
                        f"failed: {len(kick_result['failed'])}, "
                        f"not found: {len(kick_result['not_found'])}, "
                        f"protected: {len(kick_result['skipped_protected'])}"
                    )
            else:
                print("Previous batch found but it has no invited_success users.")
        else:
            print("No previous batch found for this room; skipping kick step.")

    if args.clear_messages:
        print(f"Clearing up to {args.max_messages} message(s) from room history...")
        clear_result = clear_messages(
            client,
            room_id,
            room_kind,
            args.max_messages,
            dry_run=args.dry_run,
            pause_seconds=settings["pause_seconds"],
        )
        cleanup_result["messages_considered"] = clear_result["candidate_count"]
        cleanup_result["messages_deleted"] = clear_result["deleted_count"]
        cleanup_result["message_delete_failures"] = clear_result["failed"]
        print(
            f"Messages considered: {clear_result['candidate_count']}, "
            f"deleted: {clear_result['deleted_count']}, "
            f"failed: {len(clear_result['failed'])}"
        )

    selected = selection["selected"]
    if not selected:
        print("No new users selected after filtering. No invites sent.")
        return 0

    invited_success: List[str] = []
    invited_failed: List[Dict[str, str]] = []

    print(f"Inviting {len(selected)} user(s)...")
    for username in selected:
        if args.dry_run:
            invited_success.append(username)
            continue

        ok, response = client.invite_username(room_id, room_kind, username)
        if ok:
            invited_success.append(username)
        else:
            invited_failed.append({"username": username, "error": error_to_text(response)})
        if settings["pause_seconds"] > 0:
            time.sleep(settings["pause_seconds"])

    print(f"Invites complete. Success: {len(invited_success)}, failed: {len(invited_failed)}")
    if invited_failed:
        print("Invite failures:")
        for failure in invited_failed:
            print(f"- {failure['username']}: {failure['error']}")

    welcome_message_sent = False
    welcome_message_error = None
    should_send_welcome = settings["send_welcome_message"] and bool(settings["welcome_message"])
    if should_send_welcome and invited_success:
        if args.dry_run:
            print("Dry run: would post default welcome message.")
            welcome_message_sent = True
        else:
            ok, response = client.post_message(room_id, settings["welcome_message"])
            if ok:
                print("Posted default welcome message.")
                welcome_message_sent = True
            else:
                welcome_message_error = error_to_text(response)
                print(f"Failed to post welcome message: {welcome_message_error}")

    batch_record = {
        "week_label": week_label,
        "invited_at": now_iso_utc(),
        "room_id": room_id,
        "source_file": str(source_path),
        "selected_candidates": selected,
        "invited_success": invited_success,
        "invited_failed": invited_failed,
        "welcome_message_sent": welcome_message_sent,
        "welcome_message_error": welcome_message_error,
        "cleanup": cleanup_result,
        "dry_run": bool(args.dry_run),
    }

    if args.dry_run:
        print("Dry run enabled; state file was not updated.")
        return 0

    update_state_with_batch(state, batch_record)
    save_json(settings["state_path"], state)
    print(f"State updated: {settings['state_path']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage weekly workshop room invites in Rocket.Chat.")
    parser.add_argument("--config", help="Path to workshop config JSON. Defaults to scripts/workshop_config.json.")
    parser.add_argument("--room-id", help="Override room ID.")
    parser.add_argument(
        "--archive-room-id",
        help="Optional archive room ID. If set, previous batch users are moved there instead of only kicked.",
    )
    parser.add_argument("--base-url", help="Override Rocket.Chat base URL.")
    parser.add_argument("--state-file", help="Override state JSON file path.")
    parser.add_argument(
        "--protected-usernames",
        help="Comma-separated usernames that should never be kicked by cleanup/rotate.",
    )
    parser.add_argument("--pause-seconds", type=float, help="Pause between API calls.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    preview_parser = subparsers.add_parser("preview", help="Preview top unique users that would be invited.")
    preview_parser.add_argument("--source", required=True, help="Input usernames file (.txt, .csv, .json).")
    preview_parser.add_argument("--limit", type=int, help="Number of users to select.")

    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Move previous batch to archive room (or kick), and optionally clear messages.",
    )
    cleanup_parser.add_argument("--week", help="Optional week label to clean up (e.g. 2026-W08).")
    cleanup_parser.add_argument("--clear-messages", action="store_true", help="Also delete room messages.")
    cleanup_parser.add_argument("--max-messages", type=int, default=500, help="Maximum messages to delete.")
    cleanup_parser.add_argument("--dry-run", action="store_true", help="Show actions without mutating server state.")

    rotate_parser = subparsers.add_parser(
        "rotate",
        help="Weekly rotation: move/kick last batch, optionally clear messages, and invite new unique users.",
    )
    rotate_parser.add_argument("--source", required=True, help="Input usernames file (.txt, .csv, .json).")
    rotate_parser.add_argument("--limit", type=int, help="Number of users to invite this run.")
    rotate_parser.add_argument("--week", help="Week label to store in history (default current ISO week).")
    rotate_parser.add_argument(
        "--skip-kick",
        action="store_true",
        help="Do not kick previous batch users before inviting new users.",
    )
    rotate_parser.add_argument("--clear-messages", action="store_true", help="Delete room messages before invite.")
    rotate_parser.add_argument("--max-messages", type=int, default=500, help="Maximum messages to delete.")
    rotate_parser.add_argument("--dry-run", action="store_true", help="Show actions without mutating server state.")

    return parser


def main() -> int:
    if load_dotenv:
        load_dotenv()

    parser = build_parser()
    args = parser.parse_args()

    default_config_path = Path(__file__).with_name("workshop_config.json")
    config_path = Path(args.config).expanduser() if args.config else default_config_path
    config = load_config(config_path, strict=bool(args.config))

    settings = resolve_settings(args, config, config_path)
    state = ensure_state(load_json(settings["state_path"], default={}))

    if settings["weekly_invite_count"] <= 0:
        raise RuntimeError("Invite limit must be greater than zero.")

    if args.command == "preview":
        return command_preview(args, settings, state)
    if args.command == "cleanup":
        return command_cleanup(args, settings, state)
    if args.command == "rotate":
        return command_rotate(args, settings, state)

    raise RuntimeError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
