import pandas as pd
import pytest
from piTrainer.services.train.dataset_service import _prepare_dataset_rows, _DATASET_COLUMNS
from piTrainer.services.data.augmentation_service import normalize_horizontal_flip_labels
from piTrainer.services.data.visibility_service import without_hidden_rows, HIDDEN_FLAG_KEYS

@pytest.mark.parametrize("cow", [False, True])
@pytest.mark.parametrize("duplicate_index", [False, True])
def test_projection_matches_legacy(cow, duplicate_index):
    df = pd.DataFrame({
        'abs_image': list('abcdefg'), 'frame_id': list('abcdefg'),
        'source_frame_id': ['', 'a','a','missing','a','a','a'],
        'steering': [.3,.3,.1,.5,.2,.9,.6], 'throttle': [.4,.3,.7,.8,.6,.2,.1],
        'aug_flip_lr': [False,True,True,True,True,True,True],
        'source_steering': [None,None,.8,None,None,.1,None],
        'source_throttle': [None,.6,.9,None,None,None,None],
        'flip_steering_inverted': [False,False,False,True,False,False,False],
        'training_label': [{},{},{},{},{'hidden': True},{},'{"hidden": "yes"}'],
        'hidden': [False,False,False,False,False,True,False],
        'aug_brightness_delta': [0,.1,.2,0,0,0,0],
        'metadata': [{'x':i} for i in range(7)],
    })
    if duplicate_index:
        df.index = [0,0,2,3,4,4,6]
    before = df.copy(deep=True)
    with pd.option_context('mode.copy_on_write', cow):
        expected = normalize_horizontal_flip_labels(without_hidden_rows(df))
        actual = _prepare_dataset_rows(df)
        cols = [x for x in expected.columns if x in _DATASET_COLUMNS]
        pd.testing.assert_frame_equal(expected[cols], actual[cols])
        assert 'metadata' not in actual
        pd.testing.assert_frame_equal(df,before)

@pytest.mark.parametrize("flag", HIDDEN_FLAG_KEYS)
def test_all_visibility_flags_preserved(flag):
    df = pd.DataFrame({'abs_image':['a','b'], 'steering':[0.,.5], 'throttle':[.2,.3],
                       flag:[False,True], 'metadata':[1,2]})
    assert _prepare_dataset_rows(df)['abs_image'].tolist() == ['a']

def test_duplicate_columns_use_legacy_path():
    df=pd.DataFrame([[0,1]],columns=['metadata','metadata'])
    pd.testing.assert_frame_equal(_prepare_dataset_rows(df),normalize_horizontal_flip_labels(without_hidden_rows(df)))
