from __future__ import annotations

from pathlib import Path

import yaml

from custom_trainer.state import DatasetSummary
from custom_trainer.utils.file_utils import list_images, stem_set
from custom_trainer.utils.yolo_io import read_yolo_label_file


def scan_dataset(images_dir: Path, labels_dir: Path) -> DatasetSummary:
    images = list_images(images_dir)
    labels = sorted(labels_dir.glob('*.txt')) if labels_dir.exists() else []
    image_stems = stem_set(images)
    label_stems = stem_set(labels)
    summary = DatasetSummary(
        image_count=len(images),
        label_count=len(labels),
        missing_labels=len(image_stems - label_stems),
        extra_labels=len(label_stems - image_stems),
    )
    histogram: dict[int, int] = {}
    for label_path in labels:
        for box in read_yolo_label_file(label_path):
            histogram[box.class_id] = histogram.get(box.class_id, 0) + 1
    summary.class_histogram = histogram
    return summary


def create_dataset_yaml(
    yaml_path: Path,
    train_images: str,
    val_images: str,
    class_names: list[str],
    test_images: str | None = None,
) -> Path:
    data = {
        'path': str(yaml_path.parent.resolve()),
        'train': train_images,
        'val': val_images,
        'names': {idx: name for idx, name in enumerate(class_names)},
    }
    if test_images:
        data['test'] = test_images
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')
    return yaml_path
