"""Pure category<->group fold-up logic. See specs/01-domain-model.md §2.2."""

from src.analysis.groups import fold_to_group, group_map_from_json, group_map_to_json, unmapped_categories


def test_fold_to_group_income_is_never_grouped():
    assert fold_to_group("salary", "income", {"salary": "Pay"}) is None


def test_fold_to_group_mapped_expense_category():
    assert fold_to_group("groceries", "expense", {"groceries": "Food"}) == "Food"


def test_fold_to_group_unmapped_expense_category_folds_to_rest():
    assert fold_to_group("mystery", "expense", {"groceries": "Food"}) == "Rest"


def test_unmapped_categories_returns_only_categories_missing_from_map():
    categories = {"groceries", "rent", "mystery"}
    mapping = {"groceries": "Food", "rent": "Housing"}

    assert unmapped_categories(categories, mapping) == {"mystery"}


def test_group_map_to_json_groups_categories_under_their_group_sorted():
    mapping = {"dining": "Food", "groceries": "Food", "rent": "Housing"}

    assert group_map_to_json(mapping) == {"Food": ["dining", "groceries"], "Housing": ["rent"]}


def test_group_map_from_json_flattens_to_category_to_group_dict():
    raw = {"Food": ["dining", "groceries"], "Housing": ["rent"]}

    assert group_map_from_json(raw) == {"dining": "Food", "groceries": "Food", "rent": "Housing"}


def test_group_map_round_trips_through_json_shape():
    mapping = {"dining": "Food", "groceries": "Food", "rent": "Housing"}

    assert group_map_from_json(group_map_to_json(mapping)) == mapping
