#!/usr/bin/env python3
"""
Task 3.5 - Automated Data Capture (ADC) Barcode Verification Tool
================================================================
Parses raw scanned barcode strings, extracts the part serial number, the
operation routing code and the batch data, and validates the scan against a
sample part database so that a component can only be released to the operation
that its routing actually permits.

Two payload formats are supported:

  CODE 39   fixed-field, self-checking, framed by the '*' start/stop sentinel
            and terminated by a modulo-43 check character:

                *<PART:8><OP:3><LOT:6><SERIAL:6><CHECK:1>*
                e.g.  *BLKA1234040250715000123K*

  QR / 2-D  free-order pipe-delimited key=value payload:

                PN=BLK-A1234|OP=040|LOT=250715|SN=000123

Validation performed
--------------------
  1. sentinel and field-format check
  2. Code 39 modulo-43 check character
  3. part number exists in the database
  4. the operation code belongs to that part's routing
  5. the operation is the CORRECT NEXT operation for that serial number
  6. the lot code is a real date, not in the future, within shelf life
  7. the serial has not already been scanned at this operation (duplicate)

Run:  python3 task3_5_barcode_verification.py
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ----------------------------------------------------------------------------
# 1. CODE 39 CHARACTER SET AND CHECK CHARACTER
# ----------------------------------------------------------------------------

CODE39_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%"
assert len(CODE39_CHARSET) == 43, "the Code 39 character set must hold exactly 43 symbols"

_VALUE = {c: i for i, c in enumerate(CODE39_CHARSET)}


def code39_check_char(data: str) -> str:
    """
    Modulo-43 check character: sum the value of every data character, take the
    remainder modulo 43 and translate it back to a Code 39 symbol.
    """
    total = 0
    for ch in data:
        if ch not in _VALUE:
            raise ValueError(f"character {ch!r} is not in the Code 39 character set")
        total += _VALUE[ch]
    return CODE39_CHARSET[total % 43]


# ----------------------------------------------------------------------------
# 2. PART MASTER DATABASE
# ----------------------------------------------------------------------------

@dataclass
class PartMaster:
    """Routing master record for one part number."""
    part_number: str
    description: str
    routing: List[str]                 # operation codes in the order they must run
    shelf_life_days: int = 365

    def next_operation(self, completed: List[str]) -> Optional[str]:
        """The operation that is legitimately due next for this part."""
        for op in self.routing:
            if op not in completed:
                return op
        return None


# A small sample database, as required by the task statement.
PART_DB: Dict[str, PartMaster] = {
    "BLK-A1234": PartMaster("BLK-A1234", "Engine cylinder block, 4-cyl",
                            ["010", "020", "030", "040", "050", "060"]),
    "SHF-T5500": PartMaster("SHF-T5500", "Transmission stepped shaft",
                            ["010", "020", "040", "070"]),
    "PIN-L0099": PartMaster("PIN-L0099", "Aluminium locating pin",
                            ["010", "030", "070"], shelf_life_days=180),
}

OPERATION_NAMES = {
    "010": "Raw material receipt / goods-in inspection",
    "020": "CNC rough turning",
    "030": "CNC milling",
    "040": "CNC finish turning / threading",
    "050": "Deburr and wash",
    "060": "In-line dimensional inspection",
    "070": "Final inspection and despatch",
}


# ----------------------------------------------------------------------------
# 3. PARSED SCAN RECORD
# ----------------------------------------------------------------------------

@dataclass
class ScanRecord:
    """A decoded barcode."""
    raw: str
    symbology: str
    part_number: str = ""
    operation: str = ""
    lot: str = ""
    serial: str = ""
    check_char: str = ""
    parse_errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.parse_errors

    @property
    def unique_id(self) -> str:
        return f"{self.part_number}/{self.lot}/{self.serial}"


# ----------------------------------------------------------------------------
# 4. PARSERS
# ----------------------------------------------------------------------------

#  *<PART:8><OP:3><LOT:6><SERIAL:6><CHECK:1>*
_C39_BODY = re.compile(r"^\*([0-9A-Z\-. $/+%]{23})([0-9A-Z\-. $/+%])\*$")


def parse_code39(raw: str) -> ScanRecord:
    """Decode a fixed-field Code 39 payload and verify its check character."""
    rec = ScanRecord(raw=raw, symbology="CODE39")
    s = raw.strip().upper()

    m = _C39_BODY.match(s)
    if not m:
        if not (s.startswith("*") and s.endswith("*")):
            rec.parse_errors.append("missing '*' start/stop sentinel")
        else:
            rec.parse_errors.append(
                f"wrong payload length: expected 24 data+check characters, got {len(s) - 2}")
        return rec

    body, check = m.group(1), m.group(2)
    rec.check_char = check

    expected = code39_check_char(body)
    if check != expected:
        rec.parse_errors.append(
            f"modulo-43 check character is {check!r}, expected {expected!r}")

    # fixed-width fields - the part number is stored without its hyphens
    packed_pn = body[0:8].strip()
    rec.operation = body[8:11]
    rec.lot = body[11:17]
    rec.serial = body[17:23]

    # restore the hyphenated master part number (BLKA1234 -> BLK-A1234)
    rec.part_number = _unpack_part_number(packed_pn)

    if not rec.operation.isdigit():
        rec.parse_errors.append(f"operation field {rec.operation!r} is not numeric")
    if not rec.serial.isdigit():
        rec.parse_errors.append(f"serial field {rec.serial!r} is not numeric")
    return rec


def _unpack_part_number(packed: str) -> str:
    """Match a de-hyphenated scan against the hyphenated master part numbers."""
    for pn in PART_DB:
        if pn.replace("-", "") == packed:
            return pn
    return packed            # unknown - reported later by the validator


_QR_FIELD = re.compile(r"^([A-Z]{2,3})=(.+)$")


def parse_qr(raw: str) -> ScanRecord:
    """Decode a pipe-delimited key=value QR payload."""
    rec = ScanRecord(raw=raw, symbology="QR")
    mapping: Dict[str, str] = {}

    for token in raw.strip().split("|"):
        token = token.strip()
        if not token:
            continue
        m = _QR_FIELD.match(token.upper())
        if not m:
            rec.parse_errors.append(f"malformed field {token!r} (expected KEY=VALUE)")
            continue
        mapping[m.group(1)] = m.group(2)

    for key, attr in (("PN", "part_number"), ("OP", "operation"),
                      ("LOT", "lot"), ("SN", "serial")):
        if key not in mapping:
            rec.parse_errors.append(f"mandatory field {key} is missing")
        else:
            setattr(rec, attr, mapping[key])
    return rec


def parse_scan(raw: str) -> ScanRecord:
    """Detect the symbology automatically and dispatch to the right parser."""
    s = raw.strip()
    if s.startswith("*"):
        return parse_code39(s)
    if "=" in s:
        return parse_qr(s)
    rec = ScanRecord(raw=raw, symbology="UNKNOWN")
    rec.parse_errors.append("payload matches neither the Code 39 nor the QR format")
    return rec


# ----------------------------------------------------------------------------
# 5. ROUTING VALIDATION
# ----------------------------------------------------------------------------

class RoutingValidator:
    """Checks a decoded scan against the part master and the scan history."""

    def __init__(self, db: Dict[str, PartMaster], today: _dt.date) -> None:
        self.db = db
        self.today = today
        # history[unique_id] = list of operation codes already completed
        self.history: Dict[str, List[str]] = {}

    # ---- individual checks -------------------------------------------------
    def _check_lot(self, rec: ScanRecord, master: PartMaster) -> List[str]:
        errs: List[str] = []
        if not re.fullmatch(r"\d{6}", rec.lot):
            return [f"lot code {rec.lot!r} is not a 6-digit YYMMDD date"]
        try:
            lot_date = _dt.datetime.strptime(rec.lot, "%y%m%d").date()
        except ValueError:
            return [f"lot code {rec.lot!r} is not a valid calendar date"]
        if lot_date > self.today:
            errs.append(f"lot date {lot_date} lies in the future")
        age = (self.today - lot_date).days
        if age > master.shelf_life_days:
            errs.append(f"lot is {age} days old, shelf life is {master.shelf_life_days} days")
        return errs

    # ---- the public entry point -------------------------------------------
    def validate(self, rec: ScanRecord) -> Tuple[bool, List[str], List[str]]:
        """Return (accepted, errors, notes)."""
        errors = list(rec.parse_errors)
        notes: List[str] = []

        if errors:
            return False, errors, notes

        master = self.db.get(rec.part_number)
        if master is None:
            errors.append(f"part number {rec.part_number!r} is not in the part master")
            return False, errors, notes
        notes.append(f"part recognised: {master.description}")

        errors.extend(self._check_lot(rec, master))

        if rec.operation not in master.routing:
            errors.append(f"operation {rec.operation} is not in the routing for "
                          f"{rec.part_number} (routing: {'-'.join(master.routing)})")
        else:
            notes.append(f"operation {rec.operation} = "
                         f"{OPERATION_NAMES.get(rec.operation, 'unnamed')}")
            done = self.history.get(rec.unique_id, [])
            if rec.operation in done:
                errors.append(f"duplicate scan: operation {rec.operation} has already "
                              f"been recorded for serial {rec.serial}")
            else:
                expected = master.next_operation(done)
                if expected != rec.operation:
                    errors.append(f"routing violation: operation {rec.operation} presented "
                                  f"but operation {expected} is the next one due "
                                  f"(completed so far: {'-'.join(done) or 'none'})")
                else:
                    notes.append(f"routing position correct "
                                 f"({len(done)+1} of {len(master.routing)})")

        accepted = not errors
        if accepted:
            self.history.setdefault(rec.unique_id, []).append(rec.operation)
        return accepted, errors, notes


# ----------------------------------------------------------------------------
# 6. REPORTING
# ----------------------------------------------------------------------------

def process(raw: str, validator: RoutingValidator, label: str = "") -> bool:
    rec = parse_scan(raw)
    accepted, errors, notes = validator.validate(rec)

    print("-" * 78)
    if label:
        print(f"  {label}")
    print(f"  RAW SCAN   : {raw}")
    print(f"  SYMBOLOGY  : {rec.symbology}")
    if rec.part_number or rec.operation or rec.serial:
        print(f"  DECODED    : part={rec.part_number or '?'}  op={rec.operation or '?'}  "
              f"lot={rec.lot or '?'}  serial={rec.serial or '?'}"
              + (f"  check={rec.check_char}" if rec.check_char else ""))
    for n in notes:
        print(f"      note   : {n}")
    for e in errors:
        print(f"      ERROR  : {e}")
    print(f"  RESULT     : {'ACCEPT - part may proceed' if accepted else 'REJECT - part diverted to the query bay'}")
    return accepted


def build_code39(part: str, op: str, lot: str, serial: str,
                 corrupt_check: bool = False) -> str:
    """Helper that encodes a valid (or deliberately corrupted) Code 39 payload."""
    body = f"{part.replace('-', ''):<8}{op:>03}{lot}{serial:>06}"
    if len(body) != 23:
        raise ValueError(f"body must be 23 characters, got {len(body)}: {body!r}")
    chk = code39_check_char(body)
    if corrupt_check:
        chk = CODE39_CHARSET[(CODE39_CHARSET.index(chk) + 1) % 43]
    return f"*{body}{chk}*"


# ----------------------------------------------------------------------------
# 7. TEST CASES
# ----------------------------------------------------------------------------

def main() -> None:
    print("\n" + "#" * 78)
    print("# TASK 3.5 - ADC BARCODE VERIFICATION TOOL : TEST VERIFICATION RUN")
    print("#" * 78)

    # A fixed 'today' keeps the test output reproducible.
    TODAY = _dt.date(2026, 3, 1)
    v = RoutingValidator(PART_DB, TODAY)
    print(f"\n  Validation date fixed at {TODAY} for reproducibility")
    print(f"  Part master holds: {', '.join(PART_DB)}\n")

    # --- check-character self test ------------------------------------------
    print("=" * 78)
    print("CHECK-CHARACTER SELF TEST (modulo 43)")
    print("=" * 78)
    for data in ("BLKA1234", "SHFT5500010", "123456"):
        print(f"  data {data:<14} -> check character {code39_check_char(data)!r}")
    assert code39_check_char("") == "0", "empty data must give check character '0'"
    print("   >>> check-character routine behaves as specified\n")

    results = []

    # ===== TEST CASE 1 - a clean Code 39 scan at the correct operation ======
    print("=" * 78)
    print("TEST CASE 1 - valid Code 39 scan, correct first operation")
    print("=" * 78)
    s1 = build_code39("BLK-A1234", "010", "260115", "000123")
    r = process(s1, v, "goods-in scan of an engine block")
    assert r is True, "a clean, in-sequence scan must be accepted"
    results.append(("valid Code 39, op 010", r, True))

    # the next operation in the routing must now be accepted too
    s1b = build_code39("BLK-A1234", "020", "260115", "000123")
    r = process(s1b, v, "same serial presented at the next operation")
    assert r is True, "the next routing operation must be accepted"
    results.append(("valid Code 39, op 020 (next)", r, True))

    # ===== TEST CASE 2 - QR payload, routing violation ======================
    print("\n" + "=" * 78)
    print("TEST CASE 2 - QR payload with a routing violation and a duplicate")
    print("=" * 78)
    r = process("PN=BLK-A1234|OP=060|LOT=260115|SN=000123", v,
                "operation 060 presented while 030 is due")
    assert r is False, "an out-of-sequence operation must be rejected"
    results.append(("QR, out-of-sequence op", r, False))

    r = process("PN=BLK-A1234|OP=020|LOT=260115|SN=000123", v,
                "operation 020 presented a second time")
    assert r is False, "a duplicate scan must be rejected"
    results.append(("QR, duplicate scan", r, False))

    r = process("PN=SHF-T5500|OP=010|LOT=260210|SN=004501", v,
                "a different part, first operation")
    assert r is True, "a valid scan of another part must be accepted"
    results.append(("QR, valid other part", r, True))

    # ===== TEST CASE 3 - corrupted and unknown scans ========================
    print("\n" + "=" * 78)
    print("TEST CASE 3 - corrupted check character, unknown part, bad lot, junk")
    print("=" * 78)
    r = process(build_code39("BLK-A1234", "030", "260115", "000123", corrupt_check=True), v,
                "one bit flipped in the check character")
    assert r is False, "a bad modulo-43 check character must be rejected"
    results.append(("Code 39, bad check char", r, False))

    r = process("PN=XXX-99999|OP=010|LOT=260115|SN=000001", v, "part not in the master")
    assert r is False, "an unknown part number must be rejected"
    results.append(("QR, unknown part", r, False))

    r = process("PN=PIN-L0099|OP=010|LOT=270101|SN=000045", v, "lot dated in the future")
    assert r is False, "a future lot date must be rejected"
    results.append(("QR, future lot date", r, False))

    r = process("PN=PIN-L0099|OP=010|LOT=240101|SN=000046", v,
                "lot older than the 180-day shelf life")
    assert r is False, "an expired lot must be rejected"
    results.append(("QR, expired lot", r, False))

    r = process("HELLO WORLD 12345", v, "unreadable payload")
    assert r is False, "unparseable data must be rejected"
    results.append(("junk payload", r, False))

    r = process("*SHORT*", v, "truncated Code 39 payload")
    assert r is False, "a truncated payload must be rejected"
    results.append(("Code 39, truncated", r, False))

    # ===== summary ==========================================================
    print("\n" + "=" * 78)
    print("SUMMARY OF ALL SCANS")
    print("=" * 78)
    print(f"{'Scan':<34}{'Result':>10}{'Expected':>12}{'Verdict':>12}")
    allok = True
    for name, got, want in results:
        ok = got == want
        allok &= ok
        print(f"{name:<34}{'ACCEPT' if got else 'REJECT':>10}"
              f"{'ACCEPT' if want else 'REJECT':>12}{'OK' if ok else 'MISMATCH':>12}")
    print("-" * 78)
    print(f"  Scans processed : {len(results)}")
    print(f"  Accepted        : {sum(1 for _, g, _ in results if g)}")
    print(f"  Rejected        : {sum(1 for _, g, _ in results if not g)}")
    assert allok, "at least one scan did not give the expected verdict"
    print("\n  Routing history recorded by the validator:")
    for uid, ops in v.history.items():
        print(f"    {uid:<28} operations completed: {'-'.join(ops)}")
    print("=" * 78)
    print("ALL TEST CASES COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()
