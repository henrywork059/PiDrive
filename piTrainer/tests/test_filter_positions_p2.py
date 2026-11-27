"""Deterministic position-based filtering parity; no Qt or hardware required."""
import itertools
import numpy as np
import pandas as pd
from piTrainer.services.data.filter_service import filter_preview_dataframe, _legacy_filter


def test_filter_position_parity():
    df = pd.DataFrame({
        'session': ['a','b',None,'foo']*3,
        'frame_id': ['f1','F2','f3','bar']*3,
        'mode': ['Manual','AI',None,'manual']*3,
        'ts': ['x','y','z',None]*3,
        'throttle': [.2,.5,np.nan,.8]*3,
        'steering': pd.array([0,-.5,pd.NA,1]*3,dtype='Float64'),
        'meta': [{'v':i} for i in range(12)],
    }, index=[1,1,3,2]*3)
    variants = [df, df.iloc[:0], df.drop(columns=['mode','steering']),
                df.assign(throttle=['bad','1','0.5',None]*3),
                df.assign(session=df.session.astype('string')),
                df.assign(mode=df['mode'].astype('category')),
                df.iloc[::-1], df.set_index(['session','frame_id'])]
    for cow in [False, True]:
        with pd.option_context('mode.copy_on_write',cow):
            for frame in variants:
                for args in itertools.product(['','manual','foo bar','missing'],
                        ['','manual','bad'], [None,(0,.8),(.9,.1)], [None,(-.5,.5)]):
                    try:
                        expected = _legacy_filter(frame,*args)
                    except Exception as exc:
                        import pytest
                        with pytest.raises(type(exc)):
                            filter_preview_dataframe(frame,*args)
                        continue
                    actual = filter_preview_dataframe(frame,*args)
                    pd.testing.assert_frame_equal(expected,actual)
                    if len(actual) and 'throttle' in actual:
                        before = frame.copy()
                        actual.iloc[0,actual.columns.get_loc('throttle')] = 9
                        pd.testing.assert_frame_equal(before,frame)


def test_duplicate_column_fallback():
    df = pd.DataFrame([[1,2],[3,4]],columns=['x','x'])
    pd.testing.assert_frame_equal(filter_preview_dataframe(df),_legacy_filter(df))
