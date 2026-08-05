from src.domain.models import BankProfile, CategoryRule
from src.storage import config_store

# --- round trips through the JSON files (the hand-editable config contract, specs/02-storage.md) ---


def test_bank_profile_round_trips_through_json(tmp_path):
    profile = BankProfile(
        name="Bank A",
        defaultCurrency="EUR",
        currencyColumn=None,
        encoding="utf-8-sig",
        delimiter=";",
        hasHeader=True,
        skipRows=0,
        dateColumn="EntryDate",
        dateFormat="%Y-%m-%d",
        amountMapping={"amountColumn": "Amount EUR"},
        amountConvention="signed_expense_negative",
        numberFormat="eu",
        descriptionColumns=["Description", "Recipient/Payer"],
    )

    config_store.save_bank_profiles(tmp_path, {"Bank A": profile})
    loaded = config_store.load_bank_profiles(tmp_path)

    assert loaded == {"Bank A": profile}


def test_missing_config_files_load_as_empty(tmp_path):
    assert config_store.load_bank_profiles(tmp_path) == {}
    assert config_store.load_rules(tmp_path) == []
    assert config_store.load_category_groups(tmp_path) == {}
    assert config_store.load_saved_views(tmp_path) == []
    assert config_store.load_settings(tmp_path) == {}


def test_category_rule_with_no_category_round_trips(tmp_path):
    """A type=skip rule has no category (specs/01-domain-model.md)."""
    rule = CategoryRule(pattern="internal transfer", type="skip", category=None)

    config_store.save_rules(tmp_path, [rule])
    loaded = config_store.load_rules(tmp_path)

    assert loaded == [rule]


def test_category_groups_round_trip_as_category_to_group_map(tmp_path):
    mapping = {"groceries": "Food", "rent": "Housing"}

    config_store.save_category_groups(tmp_path, mapping)
    loaded = config_store.load_category_groups(tmp_path)

    assert loaded == mapping


def test_bank_profiles_ignore_underscore_prefixed_comment_keys(tmp_path):
    """Hand-edited JSON may annotate an entry with e.g. "_comment" (specs/03-import-and-profiles.md)."""
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "bank-profiles.json").write_text(
        """
        [
          {
            "_comment": "my bank's export format",
            "name": "Bank A",
            "defaultCurrency": "EUR",
            "encoding": "utf-8-sig",
            "delimiter": ";",
            "hasHeader": true,
            "skipRows": 0,
            "dateColumn": "EntryDate",
            "dateFormat": "%Y-%m-%d",
            "amountMapping": {"amountColumn": "Amount EUR"},
            "amountConvention": "signed_expense_negative",
            "numberFormat": "eu",
            "descriptionColumns": ["Description"]
          }
        ]
        """
    )

    loaded = config_store.load_bank_profiles(tmp_path)

    assert loaded["Bank A"].name == "Bank A"


def test_rules_ignore_underscore_prefixed_comment_keys(tmp_path):
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "rules.json").write_text(
        """
        [
          {"_comment": "salary rule", "pattern": "salary", "type": "income", "category": "salary"}
        ]
        """
    )

    loaded = config_store.load_rules(tmp_path)

    assert loaded == [CategoryRule(pattern="salary", type="income", category="salary")]
