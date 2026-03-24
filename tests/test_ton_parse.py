"""
Unit tests for TON transaction parsing.
All tests are offline — no network calls.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import base64
import pytest
from pytoniq_core import begin_cell, Address as PAddress

from OrbisPaySDK.interface.ton import TON

NANOTON = 1_000_000_000

# Reusable raw-format addresses for cell building
ADDR_A = "0:ed16913070500471177998b561d8de82d31fbf84910ced6eb5fc92e7485ef8a7"
ADDR_B = "0:6f5bc6798ae064309620ddf004339269bcd2ee2a8dc6191b7e14ad2594f09041"


# ========================= Helpers =========================

def _make_native_tx(value_nano=1_000_000_000, comment_text=None, fee=1_500_000):
    """Build a minimal native TON transfer raw tx dict."""
    if comment_text:
        msg_data = {
            "@type": "msg.dataText",
            "text": base64.b64encode(comment_text.encode()).decode(),
        }
    else:
        msg_data = {"@type": "msg.dataText", "text": ""}

    return {
        "transaction_id": {"lt": "47000000001", "hash": "native_hash_123"},
        "utime": 1700000000,
        "fee": str(fee),
        "storage_fee": str(fee // 3),
        "other_fee": str(fee - fee // 3),
        "in_msg": {
            "source": "EQDtFpEwcFAEcRe5mLVh2N6C0x-_hJEM7W61_JLnSF74p4q2",
            "destination": "EQBvW8Z5huBkMJYdnfAEM5JqTNLuKo3GGRt-FK0llPCQQWKg",
            "value": str(value_nano),
            "fwd_fee": "666672",
            "ihr_fee": "0",
            "created_lt": "47000000000",
            "body_hash": "aabbccdd",
            "msg_data": msg_data,
        },
        "out_msgs": [],
    }


def _make_external_tx(out_value_nano=500_000_000):
    """Build a minimal external message tx (no source)."""
    return {
        "transaction_id": {"lt": "47000000002", "hash": "ext_hash_456"},
        "utime": 1700000100,
        "fee": "100000",
        "storage_fee": "0",
        "other_fee": "100000",
        "in_msg": {
            "source": "",
            "destination": "EQBvW8Z5huBkMJYdnfAEM5JqTNLuKo3GGRt-FK0llPCQQWKg",
            "value": "0",
            "fwd_fee": "0",
            "ihr_fee": "0",
            "msg_data": {"@type": "msg.dataRaw", "body": "", "init_state": ""},
        },
        "out_msgs": [
            {
                "source": "EQBvW8Z5huBkMJYdnfAEM5JqTNLuKo3GGRt-FK0llPCQQWKg",
                "destination": "EQDtFpEwcFAEcRe5mLVh2N6C0x-_hJEM7W61_JLnSF74p4q2",
                "value": str(out_value_nano),
                "fwd_fee": "333336",
                "ihr_fee": "0",
                "msg_data": {"@type": "msg.dataText", "text": ""},
            }
        ],
    }


def _make_jetton_transfer_boc(amount=5_000_000_000, query_id=12345):
    """Build a base64-encoded BOC for a jetton transfer op."""
    cell = (
        begin_cell()
        .store_uint(0x0F8A7EA5, 32)
        .store_uint(query_id, 64)
        .store_coins(amount)
        .store_address(PAddress(ADDR_A))
        .store_address(PAddress(ADDR_B))
        .store_bit(0)
        .store_coins(0)
        .store_bit(0)
        .end_cell()
    )
    return base64.b64encode(cell.to_boc()).decode()


def _make_jetton_notification_boc(amount=12_000_000_000, query_id=99):
    """Build a base64-encoded BOC for a jetton transfer notification."""
    cell = (
        begin_cell()
        .store_uint(0x7362D09C, 32)
        .store_uint(query_id, 64)
        .store_coins(amount)
        .store_address(PAddress(ADDR_A))
        .store_bit(0)
        .end_cell()
    )
    return base64.b64encode(cell.to_boc()).decode()


def _make_jetton_burn_boc(amount=1_000_000, query_id=77):
    """Build a base64-encoded BOC for a jetton burn."""
    cell = (
        begin_cell()
        .store_uint(0x595F07BC, 32)
        .store_uint(query_id, 64)
        .store_coins(amount)
        .end_cell()
    )
    return base64.b64encode(cell.to_boc()).decode()


def _make_jetton_tx(body_boc, value_nano=50_000_000, fee=2_000_000):
    """Wrap a BOC body into a raw tx dict."""
    return {
        "transaction_id": {"lt": "47000000003", "hash": "jetton_hash_789"},
        "utime": 1700000200,
        "fee": str(fee),
        "storage_fee": str(fee // 4),
        "other_fee": str(fee - fee // 4),
        "in_msg": {
            "source": "EQDtFpEwcFAEcRe5mLVh2N6C0x-_hJEM7W61_JLnSF74p4q2",
            "destination": "EQBvW8Z5huBkMJYdnfAEM5JqTNLuKo3GGRt-FK0llPCQQWKg",
            "value": str(value_nano),
            "fwd_fee": "666672",
            "ihr_fee": "0",
            "msg_data": {"@type": "msg.dataRaw", "body": body_boc, "init_state": ""},
        },
        "out_msgs": [],
    }


# ========================= Tests =========================

class TestParseNativeTransfer:

    def test_basic_fields(self):
        parsed = TON.parse_transaction(_make_native_tx())
        assert parsed["tx_hash"] == "native_hash_123"
        assert parsed["lt"] == "47000000001"
        assert parsed["timestamp"] == 1700000000
        assert parsed["datetime_utc"] is not None

    def test_category_native_transfer(self):
        parsed = TON.parse_transaction(_make_native_tx())
        assert parsed["tx_category"] == "native_transfer"

    def test_value(self):
        parsed = TON.parse_transaction(_make_native_tx(value_nano=2_500_000_000))
        assert parsed["in_msg"]["value"] == 2_500_000_000
        assert parsed["in_msg"]["value_ton"] == 2.5

    def test_fees(self):
        parsed = TON.parse_transaction(_make_native_tx(fee=3_000_000))
        assert parsed["fee"] == 3_000_000
        assert parsed["fee_ton"] == 3_000_000 / NANOTON
        assert parsed["storage_fee"] == 1_000_000
        assert parsed["other_fee"] == 2_000_000

    def test_comment_decoded(self):
        parsed = TON.parse_transaction(_make_native_tx(comment_text="Hello TON!"))
        assert parsed["comment"] == "Hello TON!"

    def test_no_comment(self):
        parsed = TON.parse_transaction(_make_native_tx())
        assert parsed["comment"] is None

    def test_no_out_msgs(self):
        parsed = TON.parse_transaction(_make_native_tx())
        assert parsed["out_msgs_count"] == 0
        assert parsed["out_msgs"] == []
        assert parsed["total_out_value"] == 0

    def test_in_msg_addresses(self):
        parsed = TON.parse_transaction(_make_native_tx())
        assert "EQDtFpEw" in parsed["in_msg"]["source"]
        assert "EQBvW8Z5" in parsed["in_msg"]["destination"]

    def test_opcode_none_for_text(self):
        parsed = TON.parse_transaction(_make_native_tx(comment_text="test"))
        assert parsed["opcode"] is None


class TestParseExternalMessage:

    def test_category_external(self):
        parsed = TON.parse_transaction(_make_external_tx())
        assert parsed["tx_category"] == "external"

    def test_out_msgs(self):
        parsed = TON.parse_transaction(_make_external_tx(out_value_nano=750_000_000))
        assert parsed["out_msgs_count"] == 1
        assert parsed["total_out_value"] == 750_000_000
        assert parsed["total_out_value_ton"] == 0.75

    def test_no_source_in_msg(self):
        parsed = TON.parse_transaction(_make_external_tx())
        assert parsed["in_msg"]["source"] == ""


class TestParseJettonTransfer:

    def test_category_jetton_transfer(self):
        boc = _make_jetton_transfer_boc()
        parsed = TON.parse_transaction(_make_jetton_tx(boc))
        assert parsed["tx_category"] == "jetton_transfer"

    def test_opcode(self):
        boc = _make_jetton_transfer_boc()
        parsed = TON.parse_transaction(_make_jetton_tx(boc))
        assert parsed["opcode"] == hex(0x0F8A7EA5)

    def test_jetton_fields(self):
        boc = _make_jetton_transfer_boc(amount=9_000_000_000, query_id=555)
        parsed = TON.parse_transaction(_make_jetton_tx(boc))
        j = parsed["jetton"]
        assert j["op_name"] == "jetton_transfer"
        assert j["jetton_amount"] == 9_000_000_000
        assert j["query_id"] == 555
        assert j["destination"] is not None
        assert j["response_destination"] is not None


class TestParseJettonNotification:

    def test_category_notification(self):
        boc = _make_jetton_notification_boc()
        parsed = TON.parse_transaction(_make_jetton_tx(boc))
        assert parsed["tx_category"] == "jetton_transfer_notification"

    def test_notification_fields(self):
        boc = _make_jetton_notification_boc(amount=25_000_000, query_id=42)
        parsed = TON.parse_transaction(_make_jetton_tx(boc))
        j = parsed["jetton"]
        assert j["op_name"] == "jetton_transfer_notification"
        assert j["jetton_amount"] == 25_000_000
        assert j["query_id"] == 42
        assert j["sender"] is not None


class TestParseJettonBurn:

    def test_category_burn(self):
        boc = _make_jetton_burn_boc()
        parsed = TON.parse_transaction(_make_jetton_tx(boc))
        assert parsed["tx_category"] == "jetton_burn"

    def test_burn_fields(self):
        boc = _make_jetton_burn_boc(amount=100_000, query_id=7)
        parsed = TON.parse_transaction(_make_jetton_tx(boc))
        j = parsed["jetton"]
        assert j["op_name"] == "jetton_burn"
        assert j["jetton_amount"] == 100_000
        assert j["query_id"] == 7


class TestParseEdgeCases:

    def test_empty_tx(self):
        parsed = TON.parse_transaction({})
        assert parsed["tx_hash"] == ""
        assert parsed["timestamp"] == 0
        assert parsed["datetime_utc"] is None
        assert parsed["fee"] == 0
        assert parsed["tx_category"] == "external"  # no source

    def test_none_in_msg(self):
        parsed = TON.parse_transaction({"in_msg": None, "out_msgs": None})
        assert parsed["in_msg"] == {}
        assert parsed["out_msgs"] == []

    def test_unknown_opcode_is_contract_call(self):
        """A raw body with an unknown non-zero op should be 'contract_call'."""
        cell = begin_cell().store_uint(0xDEADBEEF, 32).store_uint(0, 64).end_cell()
        boc = base64.b64encode(cell.to_boc()).decode()
        tx = _make_jetton_tx(boc)
        parsed = TON.parse_transaction(tx)
        assert parsed["tx_category"] == "contract_call"
        assert parsed["opcode"] == hex(0xDEADBEEF)
        assert "jetton" not in parsed

    def test_raw_body_with_text_comment(self):
        """A raw body with op=0 followed by text is a comment."""
        cell = (
            begin_cell()
            .store_uint(0, 32)
            .store_snake_string("raw comment test")
            .end_cell()
        )
        boc = base64.b64encode(cell.to_boc()).decode()
        tx = {
            "transaction_id": {"lt": "1", "hash": "comment_raw"},
            "utime": 1700000000,
            "fee": "0",
            "storage_fee": "0",
            "other_fee": "0",
            "in_msg": {
                "source": "EQDtFpEwcFAEcRe5mLVh2N6C0x-_hJEM7W61_JLnSF74p4q2",
                "destination": "EQBvW8Z5huBkMJYdnfAEM5JqTNLuKo3GGRt-FK0llPCQQWKg",
                "value": "1000000000",
                "fwd_fee": "0",
                "ihr_fee": "0",
                "msg_data": {"@type": "msg.dataRaw", "body": boc, "init_state": ""},
            },
            "out_msgs": [],
        }
        parsed = TON.parse_transaction(tx)
        assert parsed["comment"] == "raw comment test"
        assert parsed["tx_category"] == "native_transfer"

    def test_multiple_out_msgs(self):
        tx = _make_external_tx()
        tx["out_msgs"].append({
            "source": "EQBvW8Z5huBkMJYdnfAEM5JqTNLuKo3GGRt-FK0llPCQQWKg",
            "destination": "EQDtFpEwcFAEcRe5mLVh2N6C0x-_hJEM7W61_JLnSF74p4q2",
            "value": "250000000",
            "fwd_fee": "100000",
            "ihr_fee": "0",
            "msg_data": {"@type": "msg.dataText", "text": ""},
        })
        parsed = TON.parse_transaction(tx)
        assert parsed["out_msgs_count"] == 2
        assert parsed["total_out_value"] == 750_000_000
        assert parsed["total_out_value_ton"] == 0.75
