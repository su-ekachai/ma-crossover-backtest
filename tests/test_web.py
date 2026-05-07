"""Tests for Flask web application."""

import pytest

from web.app import app, parse_result_folder


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestParseResultFolder:
    def test_valid_folder_name(self):
        result = parse_result_folder("20260417_BTCUSDT_MAEMA99_1h")
        assert result is not None
        assert result["date"] == "20260417"
        assert result["asset"] == "BTCUSDT"
        assert result["ma_type"] == "EMA"
        assert result["ma_period"] == 99
        assert result["timeframe"] == "1h"

    def test_sma_folder(self):
        result = parse_result_folder("20260417_ETHUSDT_MASMA200_4h")
        assert result is not None
        assert result["ma_type"] == "SMA"
        assert result["ma_period"] == 200

    def test_rejects_path_traversal(self):
        assert parse_result_folder("../etc/passwd") is None
        assert parse_result_folder("../../secret") is None
        assert parse_result_folder("20260417/../../../etc") is None

    def test_rejects_invalid_format(self):
        assert parse_result_folder("invalid_folder") is None
        assert parse_result_folder("") is None
        assert parse_result_folder("abc_xyz_MAabc_1h") is None


class TestRoutes:
    def test_index_route(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_invalid_result_404(self, client):
        response = client.get("/result/nonexistent_folder")
        assert response.status_code == 404

    def test_compare_no_selection(self, client):
        response = client.get("/compare")
        assert response.status_code == 200
