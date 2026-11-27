"""Ordered PIL tensor parity and bounded TFLite chunk loading."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from PIL import Image
from piTrainer.services.validation.validation_inputs import (
    PreparedImageSource, _prepare_input_source, _prepare_inputs)
from piTrainer.services.validation.tflite_runner import _run_tflite_predictions


def fixture(tmp_path):
    rng=np.random.default_rng(17)
    paths=[]
    for index in range(7):
        path=tmp_path/f"{index}.png"
        im=Image.fromarray(rng.integers(0,256,(31,43,3),dtype=np.uint8))
        if index==1: im=im.convert("L")
        if index==2: im=im.convert("RGBA")
        im.save(path)
        paths.append(str(path))
    paths.insert(2,str(tmp_path/"missing.png"))
    df=pd.DataFrame({"abs_image":paths,"frame_id":list("abcdefgh"),
        "steering":[.1,.1,.2,.3,.4,.5,.6,.7],"throttle":[.2,.3,.4,.5,.6,.7,.8,.9],
        "aug_flip_lr":[False,True,False,True,False,True,False,True],
        "source_steering":[None,.1,None,.3,None,.5,None,.7],
        "source_throttle":[None,.2,None,.5,None,.7,None,.9]},
        index=[1,2,3,5,8,9,10,11])
    return df


def test_eager_and_chunked_exact_legacy_pil_pixels(tmp_path):
    df=fixture(tmp_path)
    rows,source,steering,throttle=_prepare_input_source(df,12,16,5)
    assert list(rows.source_row_number)==[2,3,6,9,10]
    expected=[]
    for path,flip in zip(source.paths,source.flips):
        with Image.open(path) as im:
            im=im.convert("RGB")
            if flip: im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            expected.append(np.asarray(im.resize((16,12)),dtype=np.float32)/255.0)
    expected=np.stack(expected,axis=0)
    assert source.shape==(5,12,16,3)
    np.testing.assert_array_equal(np.concatenate([source[:2],source[2:4],source[4:]],axis=0),expected)
    rows2,x,s,t=_prepare_inputs(df,12,16,5)
    pd.testing.assert_frame_equal(rows,rows2)
    np.testing.assert_array_equal(x,expected)
    np.testing.assert_array_equal(s,steering)
    np.testing.assert_array_equal(t,throttle)
    np.testing.assert_allclose(s,[.1,-.1,-.3,.4,-.5])
    np.testing.assert_allclose(t,[.2,.2,.5,.6,.7])
    with pytest.raises(ValueError): source[::2]


class FakeInterpreter:
    def __init__(self, fixed, quantized):
        self.fixed=fixed
        self.shape=(fixed or 1,12,16,3)
        self.quantized=quantized
        self.batches=[]
    def allocate_tensors(self): pass
    def get_input_details(self):
        return [{"index":0,"name":"image","shape":self.shape,
                 "shape_signature":(self.fixed or -1,12,16,3),
                 "dtype":np.uint8 if self.quantized else np.float32,
                 "quantization":(1/255,0) if self.quantized else (0.,0)}]
    def get_output_details(self):
        return [{"index":1,"name":"steering_throttle","shape":(self.shape[0],2),
                 "dtype":np.float32}]
    def resize_tensor_input(self,index,shape,strict=False):
        self.shape=tuple(shape)
    def set_tensor(self,index,value):
        self.batches.append(value.copy())
    def invoke(self): pass
    def get_tensor(self,index):
        x=self.batches[-1].astype(np.float32)
        return x[:,:,:,0:2].mean(axis=(1,2))


@pytest.mark.parametrize("fixed",[0,1,3])
@pytest.mark.parametrize("quantized",[False,True])
def test_streaming_preserves_interpreter_batches_and_padding(tmp_path,fixed,quantized):
    _,source,s,t=_prepare_input_source(fixture(tmp_path),12,16,0)
    dense=source[:]
    first=FakeInterpreter(fixed,quantized)
    second=FakeInterpreter(fixed,quantized)
    a=_run_tflite_predictions(first,dense,s,t,2)
    b=_run_tflite_predictions(second,source,s,t,2)
    assert len(first.batches)==len(second.batches)
    for x,y in zip(first.batches,second.batches):
        np.testing.assert_array_equal(x,y)
        assert len(y)<= (fixed or 2)
    for x,y in zip(a[:2],b[:2]): np.testing.assert_array_equal(x,y)
    assert a[2:]==b[2:]


def test_chunk_source_does_not_decode_unrequested_paths(tmp_path):
    path=tmp_path/"valid.png";Image.new("RGB",(4,4)).save(path)
    src=PreparedImageSource([str(path),str(tmp_path/"missing.png")],[False,False],2,2)
    assert src[:1].shape==(1,2,2,3)
    with pytest.raises(FileNotFoundError): src[1:2]
