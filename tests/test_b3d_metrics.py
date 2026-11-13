import pytest
from engine.b3d.metrics import comparison_label_value
from engine.render import NO_STICKERS

def test_comparison_labels_are_exact_scenario_values():
    for fraction in (0, 0.1, 0.5, 0.9, 1):
        assert comparison_label_value(8, fraction) == 8
        assert comparison_label_value(1, fraction) == 1

def test_invalid_comparison_values_fail_closed():
    for target in (-1, float('inf'), float('nan')):
        with pytest.raises(ValueError, match='finite nonnegative'):
            comparison_label_value(target, 0.3)
    with pytest.raises(ValueError, match='progress'):
        comparison_label_value(8, float('nan'))

def test_atlas_3d_data_is_not_covered_by_random_emojis():
    assert 'atlas' in NO_STICKERS
    assert 'lowbat' in NO_STICKERS
    assert '10sec' not in NO_STICKERS
