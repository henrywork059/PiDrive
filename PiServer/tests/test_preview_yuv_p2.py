import cv2
import numpy as np
from piserver.services.preview_yuv import YUV420Layout
import pytest

@pytest.mark.parametrize('w,h,stride', [(2,2,2),(6,6,8),(320,180,384),(320,182,384),(426,240,448),(640,480,640)])
def test_planar_padding(w,h,stride):
    rng=np.random.default_rng(17)
    y=rng.integers(16,236,(h,w),dtype=np.uint8)
    u=rng.integers(16,241,(h//2,w//2),dtype=np.uint8)
    v=rng.integers(16,241,(h//2,w//2),dtype=np.uint8)
    canonical=np.concatenate([y.ravel(),u.ravel(),v.ravel()]).reshape(h*3//2,w)
    expected=cv2.cvtColor(canonical,cv2.COLOR_YUV2BGR_I420)
    padded=[np.pad(p,((0,0),(0,s-p.shape[1])),constant_values=255) for p,s in [(y,stride),(u,stride//2),(v,stride//2)]]
    plane=np.concatenate([p.ravel() for p in padded]).reshape(h*3//2,stride)
    layout=YUV420Layout.from_config({'format':'YUV420','size':(w,h),'stride':stride},(w,h))
    actual=layout.decode_bgr(plane,np,cv2)
    np.testing.assert_array_equal(actual,expected)
    np.testing.assert_array_equal(cv2.imencode('.jpg',actual)[1],cv2.imencode('.jpg',expected)[1])
    plane.fill(0)
    np.testing.assert_array_equal(actual,expected)

@pytest.mark.parametrize('bad', [{'format':'YVU420'}, {'stride':319}, {'stride':321}, {'stride':None}, {'stride':8192}, {'size':(318,180)}, {'size':None}])
def test_bad_config(bad):
    with pytest.raises(ValueError): YUV420Layout.from_config({'format':'YUV420','size':(320,180),'stride':384,**bad},(320,180))

def test_bad_array():
    layout=YUV420Layout(320,180,384)
    for a in [np.zeros((270,320),np.uint8),np.zeros((270,384),np.uint16),np.zeros((270,768),np.uint8)[:,::2]]:
        with pytest.raises(ValueError): layout.decode_bgr(a,np,cv2)
