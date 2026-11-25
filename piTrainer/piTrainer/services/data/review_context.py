"""Read-only context for the actual selected Data records."""
from __future__ import annotations
import math

def finite(value):
    try:
        number=float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None

def display(value):
    number=finite(value)
    return 'Unknown' if number is None else f'{number:.3f}'

def bulk_preview(records, field, value, limit=5):
    rows=list(records)
    examples=[]
    for row in rows[:max(0,limit)]:
        examples.append(f"{row.get('session','?')} / {row.get('frame_id','?')}: {display(row.get(field))} → {display(value)}")
    remaining=len(rows)-len(examples)
    if remaining:
        examples.append(f"… and {remaining} more selected frame(s).")
    return '\n'.join(examples)

def prediction_pair(record):
    if not isinstance(record,dict):
        return None
    steering=finite(record.get('pred_steering'))
    speed=finite(record.get('pred_throttle',record.get('pred_speed')))
    return (steering,speed) if steering is not None and speed is not None else None

def comparison_text(record):
    pair=prediction_pair(record)
    if pair is None:
        return 'AI comparison unavailable for this frame.'
    actual=(finite(record.get('steering')),finite(record.get('throttle')))
    if None in actual:
        return f"AI S/T {display(pair[0])}/{display(pair[1])}; label unknown."
    return (f"Label S/T {display(actual[0])}/{display(actual[1])} | "
            f"AI S/T {display(pair[0])}/{display(pair[1])} | "
            f"Δ AI−label {display(pair[0]-actual[0])}/{display(pair[1]-actual[1])}")
