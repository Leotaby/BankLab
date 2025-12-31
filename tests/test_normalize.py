"""Tests for XBRL normalization module."""

import pandas as pd
import pytest

from banklab.clean.xbrl_normalize import (
    BANK_LINE_ITEM_MAPPINGS,
    LineItemMapping,
    XBRLNormalizer,
)


class TestLineItemMappings:
    """Tests for line item mapping definitions."""

    def test_all_mappings_have_required_fields(self):
        """Verify all mappings have required attributes."""
        for name, mapping in BANK_LINE_ITEM_MAPPINGS.items():
            assert isinstance(mapping, LineItemMapping)
            assert mapping.name == name
            assert len(mapping.tags) > 0
            assert mapping.category in [
                "income_statement",
                "balance_sheet",
                "cash_flow",
                "shares",
                "regulatory",
            ]
            assert mapping.unit_filter in ["USD", "shares", "pure"]
            assert mapping.expected_sign in ["positive", "negative", "any"]

    def test_core_line_items_exist(self):
        """Verify core financial statement items are defined."""
        core_items = [
            "total_revenue",
            "net_income",
            "total_assets",
            "total_liabilities",
            "total_equity",
            "net_interest_income",
        ]
        for item in core_items:
            assert item in BANK_LINE_ITEM_MAPPINGS

    def test_tags_follow_naming_convention(self):
        """Verify XBRL tags follow expected format."""
        for _name, mapping in BANK_LINE_ITEM_MAPPINGS.items():
            for tag in mapping.tags:
                assert ":" in tag, f"Tag {tag} should have namespace prefix"
                namespace, tag_name = tag.split(":", 1)
                assert namespace in ["us-gaap", "dei", "srt"]


class TestXBRLNormalizer:
    """Tests for XBRLNormalizer class."""

    @pytest.fixture
    def sample_raw_facts(self):
        """Create sample raw facts for testing."""
        return pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2024-03-31"),
                    "cik": "0000019617",
                    "ticker": "JPM",
                    "tag": "us-gaap:Assets",
                    "value": 4_000_000_000_000,
                    "unit": "USD",
                    "fp": "Q1",
                    "fy": 2024,
                    "form": "10-Q",
                },
                {
                    "date": pd.Timestamp("2024-03-31"),
                    "cik": "0000019617",
                    "ticker": "JPM",
                    "tag": "us-gaap:Liabilities",
                    "value": 3_700_000_000_000,
                    "unit": "USD",
                    "fp": "Q1",
                    "fy": 2024,
                    "form": "10-Q",
                },
                {
                    "date": pd.Timestamp("2024-03-31"),
                    "cik": "0000019617",
                    "ticker": "JPM",
                    "tag": "us-gaap:StockholdersEquity",
                    "value": 300_000_000_000,
                    "unit": "USD",
                    "fp": "Q1",
                    "fy": 2024,
                    "form": "10-Q",
                },
                {
                    "date": pd.Timestamp("2024-03-31"),
                    "cik": "0000019617",
                    "ticker": "JPM",
                    "tag": "us-gaap:NetIncomeLoss",
                    "value": 13_000_000_000,
                    "unit": "USD",
                    "fp": "Q1",
                    "fy": 2024,
                    "form": "10-Q",
                },
            ]
        )

    def test_normalizer_initialization(self):
        """Test normalizer can be initialized."""
        normalizer = XBRLNormalizer()
        assert normalizer.mappings == BANK_LINE_ITEM_MAPPINGS
        assert normalizer.min_year == 2015

    def test_normalize_returns_dataframe(self, sample_raw_facts):
        """Test normalize returns a DataFrame with expected columns."""
        normalizer = XBRLNormalizer(min_year=2020)
        result = normalizer.normalize(sample_raw_facts)

        assert isinstance(result, pd.DataFrame)
        expected_cols = [
            "ticker",
            "fiscal_year",
            "fiscal_period",
            "date",
            "line_item",
            "display_name",
            "category",
            "value",
            "source_tag",
        ]
        for col in expected_cols:
            assert col in result.columns

    def test_normalize_extracts_values(self, sample_raw_facts):
        """Test that normalization extracts correct values."""
        normalizer = XBRLNormalizer(min_year=2020)
        result = normalizer.normalize(sample_raw_facts)

        # Check total_assets was extracted
        assets_row = result[result["line_item"] == "total_assets"]
        assert len(assets_row) == 1
        assert assets_row["value"].iloc[0] == 4_000_000_000_000

    def test_normalize_filters_by_year(self, sample_raw_facts):
        """Test that min_year filter works."""
        normalizer = XBRLNormalizer(min_year=2025)
        result = normalizer.normalize(sample_raw_facts)

        # Should be empty since all data is from 2024
        assert len(result) == 0

    def test_to_wide_format(self, sample_raw_facts):
        """Test conversion to wide format."""
        normalizer = XBRLNormalizer(min_year=2020)
        long_df = normalizer.normalize(sample_raw_facts)
        wide_df = normalizer.to_wide_format(long_df)

        # Wide format should have line items as columns
        assert "total_assets" in wide_df.columns
        assert "net_income" in wide_df.columns

    def test_get_data_dictionary(self):
        """Test data dictionary generation."""
        normalizer = XBRLNormalizer()
        data_dict = normalizer.get_data_dictionary()

        assert isinstance(data_dict, pd.DataFrame)
        assert "line_item" in data_dict.columns
        assert "description" in data_dict.columns
        assert len(data_dict) == len(BANK_LINE_ITEM_MAPPINGS)


class TestDeduplication:
    """Tests for handling duplicate facts."""

    def test_prefers_10k_over_8k(self):
        """Test that 10-K/10-Q filings are preferred over 8-K."""
        raw_facts = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2024-03-31"),
                    "cik": "0000019617",
                    "ticker": "JPM",
                    "tag": "us-gaap:Assets",
                    "value": 100,
                    "unit": "USD",
                    "fp": "Q1",
                    "fy": 2024,
                    "form": "8-K",
                },
                {
                    "date": pd.Timestamp("2024-03-31"),
                    "cik": "0000019617",
                    "ticker": "JPM",
                    "tag": "us-gaap:Assets",
                    "value": 200,
                    "unit": "USD",
                    "fp": "Q1",
                    "fy": 2024,
                    "form": "10-Q",
                },
            ]
        )

        normalizer = XBRLNormalizer(min_year=2020)
        result = normalizer.normalize(raw_facts)

        assets = result[result["line_item"] == "total_assets"]
        assert len(assets) == 1
        assert assets["value"].iloc[0] == 200  # 10-Q value preferred

    def test_filters_by_unit(self):
        """Test that unit filtering works."""
        raw_facts = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2024-03-31"),
                    "cik": "0000019617",
                    "ticker": "JPM",
                    "tag": "us-gaap:Assets",
                    "value": 100,
                    "unit": "USD",
                    "fp": "Q1",
                    "fy": 2024,
                    "form": "10-Q",
                },
                {
                    "date": pd.Timestamp("2024-03-31"),
                    "cik": "0000019617",
                    "ticker": "JPM",
                    "tag": "us-gaap:Assets",
                    "value": 999,
                    "unit": "shares",  # Wrong unit for Assets
                    "fp": "Q1",
                    "fy": 2024,
                    "form": "10-Q",
                },
            ]
        )

        normalizer = XBRLNormalizer(min_year=2020)
        result = normalizer.normalize(raw_facts)

        assets = result[result["line_item"] == "total_assets"]
        assert len(assets) == 1
        assert assets["value"].iloc[0] == 100  # USD value only
