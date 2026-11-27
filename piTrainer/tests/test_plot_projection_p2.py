"""Plot projection preserves all rendered series and summaries; source is isolated."""
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure
from piTrainer.services.data.plot_service import (
    plot_input_snapshot, plot_sessions_for_combo, filter_plot_dataframe,
    build_plot_summary, render_plot)


def legacy_filter(df, name):
    if df.empty:
        return df.copy()
    if name and name != 'All loaded sessions' and 'session' in df.columns:
        return df[df['session'].astype(str)==name].copy().reset_index(drop=True)
    return df.reset_index(drop=True).copy()


def artist_signature(ax):
    return {
        "lines":[(line.get_xdata().tolist(),line.get_ydata().tolist()) for line in ax.lines],
        "bars":[(p.get_x(),p.get_y(),p.get_width(),p.get_height()) for p in ax.patches],
        "collections":[np.asarray(c.get_offsets()).tolist() for c in ax.collections],
        "texts":[t.get_text() for t in ax.texts],
        "labels":(ax.get_xlabel(),ax.get_ylabel(),ax.get_title()),
        "ticks":([t.get_text() for t in ax.get_xticklabels()],
                 [t.get_text() for t in ax.get_yticklabels()])
    }


@pytest.mark.parametrize("cow",[False,True])
@pytest.mark.parametrize("name",["All loaded sessions","s1","missing","None"])
def test_plot_snapshot_parity(cow,name):
    frame=pd.DataFrame({"session":["s1","s2","s1",None,"s2"],
        "steering":[.1,-.2,None,.5,.8],"throttle":[.2,.4,.6,.8,0],
        "mode":["manual","ai",None,"ai","manual"],
        "metadata":[{"a":i} for i in range(5)]},index=[3,1,1,8,4])
    with pd.option_context("mode.copy_on_write",cow):
        before=frame.copy()
        wide=frame.reset_index(drop=True).copy()
        narrow=plot_input_snapshot(frame)
        assert list(narrow.columns)==["session","steering","throttle","mode"]
        assert plot_sessions_for_combo(wide)==plot_sessions_for_combo(narrow)
        old=legacy_filter(wide,name)
        new=filter_plot_dataframe(narrow,name)
        pd.testing.assert_frame_equal(old[narrow.columns],new)
        assert build_plot_summary(old)==build_plot_summary(new)
        for kind in ["Steering + Speed Timeline","Steering Histogram","Speed Histogram",
                     "Steering vs Speed Scatter","Mode Distribution","Session Frame Count"]:
            a=Figure().add_subplot(111);b=Figure().add_subplot(111)
            render_plot(a,old,kind,name);render_plot(b,new,kind,name)
            assert artist_signature(a)==artist_signature(b)
        narrow.iloc[0,narrow.columns.get_loc("steering")]=.99
        pd.testing.assert_frame_equal(frame,before)


def test_unusual_schema_fallback():
    for df in [pd.DataFrame({"metadata":[1,2]},index=[5,6]),
               pd.DataFrame([[1,2]],columns=["session","session"])]:
        pd.testing.assert_frame_equal(plot_input_snapshot(df),df.reset_index(drop=True))
    assert plot_input_snapshot(pd.DataFrame(columns=["session"])).empty
