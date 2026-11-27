"""P2 bounded JSONL row processing and exact legacy session priority."""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import pandas as pd
import pytest
from piTrainer.services.data import record_loader_service as loader


def test_streaming_matches_legacy_rows_with_source_order_and_hidden_record_suppression():
    with tempfile.TemporaryDirectory(prefix='p2-records-') as tmp:
        root = Path(tmp)
        for session in ('a', 'b'):
            (root / session / 'frames').mkdir(parents=True)
            (root / session / 'frames' / 'frame.jpg').write_bytes(b'jpeg')
            (root / session / 'manifest.json').write_text(
                json.dumps({'overlay_settings': {'brightness': 1.1}, 'label': session}), encoding='utf-8')
        labels_a = [
            {'frame':'frames/frame.jpg','frame_id':'1','ts':'a1','mode':'manual',
             'steering':'0.2','throttle':'0.4'},
            {'frame':'frames/missing.jpg','frame_id':'2','ts':'a2'},
            {'frame':'frames/frame.jpg','frame_id':'3','ts':'a3','hidden':True},
        ]
        labels_b = [
            {'frame':'frames/missing.jpg','frame_id':'x','ts':'b1'},
        ]
        records_a = [{'frame':'frames/frame.jpg','frame_id':'ignored','ts':'a0'}]
        records_b = [
            {'frame':'frames/frame.jpg','frame_id':'x','ts':'b1', 'steering':-0.5},
            {'frame':'frames/frame.jpg','frame_id':'record','ts':'b2','throttle':0.7},
            {'frame':'frames/missing.jpg','frame_id':'missing','ts':'b3'},
        ]
        for name, labels, records in [('a',labels_a,records_a),('b',labels_b,records_b)]:
            base = root / name
            (base / 'labels.jsonl').write_text('\n'.join(json.dumps(x) for x in labels)+'\n',
                                              encoding='utf-8')
            (base / 'records.jsonl').write_text('\n'.join(json.dumps(x) for x in records)+'\n',
                                               encoding='utf-8')
        sessions=['a','b','a']
        def legacy_batches(records_root, names, batch_size=512):
            rows=[]
            for session in names:
                path=root / session
                labels=loader._load_labels_rows(session,path)
                if labels:
                    rows.extend(labels)
                else:
                    hidden=loader._hidden_record_identities(path/'labels.jsonl')
                    rows.extend(loader._load_records_rows(session,path,hidden))
            if rows:
                yield rows

        with patch.object(loader,'resolve_session_dir',side_effect=lambda base,name:root/name):
            with patch.object(loader,'iter_record_batches',legacy_batches):
                expected=loader.load_records_dataframe(root,sessions)
            actual=loader.load_records_dataframe(root,sessions)
            pd.testing.assert_frame_equal(actual,expected)
            self_frames=[x['frame_id'] for x in actual.to_dict('records')]
            assert self_frames == ['1','x','record','missing','1']
            for count in (1,2,3,512):
                parts=list(loader.iter_record_batches(root,sessions,batch_size=count))
                assert all(1<=len(batch)<=count for batch in parts)
                assert [row['frame_id'] for batch in parts for row in batch] == self_frames


@pytest.mark.parametrize('batch_size', [0,-1,4097,1.3,True,None])
def test_batch_bounds_rejected(batch_size):
    with pytest.raises(ValueError):
        list(loader.iter_record_batches(Path('unused'), [], batch_size=batch_size))


def test_canonical_session_context_preserves_paths_and_live_image_existence(tmp_path):
    session = tmp_path / "recordings" / "day" / "drive"
    (session / "frames").mkdir(parents=True)
    first = session / "frames" / "one.jpg"
    first.write_bytes(b"fixture")
    alias = session / "frames" / "alias.jpg"
    try:
        alias.symlink_to(first)
    except OSError:
        alias.write_bytes(b"fixture")
    records = [
        {"frame": "frames/one.jpg", "frame_id": 1, "steering": "0.4"},
        {"image": "frames/alias.jpg", "frame_id": 2},
        {"relative_file": "recordings/day/drive/frames/one.jpg", "frame_id": 3},
        {"frame": "frames/missing.jpg", "frame_id": 4},
        {"training_label": {"frame": "frames/one.jpg", "frame_id": 5}},
    ]
    defaults = {"overlay_settings": {"contrast": 1.1}}
    for record in records:
        old = loader.build_row("drive", session, record, manifest_defaults=defaults)
        new = loader.build_row("drive", session.resolve(), record,
                               manifest_defaults=defaults, _session_resolved=True)
        assert old == new

    (session / "labels.jsonl").write_text(
        "\n".join(json.dumps(x) for x in [records[0], records[0]])+"\n", encoding="utf-8")
    batches = loader.iter_record_batches(tmp_path, ["recordings/day/drive"], batch_size=1)
    assert next(batches)[0]["abs_image"] == str(first.resolve())
    first.unlink()
    assert list(batches) == []


def test_materialized_range_index_and_row_order(tmp_path):
    session = tmp_path / "drive"
    (session / "frames").mkdir(parents=True)
    (session / "frames" / "one.jpg").write_bytes(b"fixture")
    (session / "labels.jsonl").write_text(
        "\n".join(json.dumps({"frame":"frames/one.jpg","frame_id":i,
                             "steering":None if i==1 else 0.5,"throttle":2})
                  for i in range(3))+"\n",encoding="utf-8")
    df = loader.load_records_dataframe(tmp_path, ["drive", "drive"])
    assert isinstance(df.index, pd.RangeIndex)
    assert list(df.index) == list(range(6))
    assert df["frame_id"].tolist() == [0,1,2,0,1,2]
    assert df["steering"].tolist() == [0.5,0.0,0.5,0.5,0.0,0.5]
    assert df["throttle"].tolist() == [1.0]*6


@pytest.mark.parametrize("batch_size", [1,7,512])
def test_column_materialization_preserves_global_inference(batch_size):
    import random
    rng = random.Random(17)
    values = [None, True, False, 0, 1, 2**63, 2**64, .5, float("nan"),
              "a", "", {}, [], {"k": 1}, [1]]
    for _ in range(100):
        rows = [dict(id=i, **{k:rng.choice(values) for k in ("a","b","c","d")
                             if rng.random()<.8})
                for i in range(rng.randint(1,90))]
        expected = pd.DataFrame(rows)
        actual = loader._materialize_record_columns(
            rows[i:i+batch_size] for i in range(0,len(rows),batch_size))
        pd.testing.assert_frame_equal(expected, actual)
    pd.testing.assert_frame_equal(loader._materialize_record_columns([[{},{}],[{}]]),
                                  pd.DataFrame([{}, {}, {}]))


def test_actual_jsonl_column_loading_against_legacy_materialization(tmp_path):
    session = tmp_path / "drive"
    (session/"frames").mkdir(parents=True)
    (session/"frames"/"one.jpg").write_bytes(b"fixture")
    rows = [{"frame":"frames/one.jpg","frame_id":i,
             "steering":None if i%7==0 else str((i%100-50)/50),
             "throttle":.4,"overlay_settings":{"brightness":1.1},
             **({"cam_w":None} if i<512 else {"cam_w":426}),
             **({"format":"RGB888"} if i%13 else {}),
             **({"source_frame_bytes":2**63} if i==513 else {})}
            for i in range(1100)]
    (session/"labels.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows)+"\n",encoding="utf-8")
    with patch.object(loader, "_materialize_record_columns",
                      side_effect=lambda batches: pd.DataFrame([row for batch in batches for row in batch])):
        expected=loader.load_records_dataframe(tmp_path,["drive","drive"])
    actual=loader.load_records_dataframe(tmp_path,["drive","drive"])
    pd.testing.assert_frame_equal(actual,expected)
    assert actual.index.equals(pd.RangeIndex(2200))
