"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line


DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _clip_box(text):
    try:
        class_id, cx, cy, width, height = parse_yolo_line(text)
    except (ValueError, OverflowError):
        return None
    left = max(0.0, cx - width / 2)
    top = max(0.0, cy - height / 2)
    right = min(1.0, cx + width / 2)
    bottom = min(1.0, cy + height / 2)
    if right <= left or bottom <= top:
        return None
    box = ((left + right) / 2, (top + bottom) / 2, right - left, bottom - top)
    return f"{class_id} " + " ".join(f"{value:.12g}" for value in box)


def _fix_label(path, edits):
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    kept, fixes = [], []
    for line, original in enumerate(lines, 1):
        action = edits.get(line)
        if action is None or not original.strip():
            kept.append(original)
            continue
        before = original.rstrip("\n")
        after = _clip_box(before) if action == "clip_box" else None
        if after == before:
            kept.append(original)
            continue
        if after is not None:
            kept.append(after + ("\n" if original.endswith("\n") else ""))
        fixes.append(dict(image=path.stem, line=line, action="drop_line" if after is None else action,
                          before=before, after="" if after is None else after))
    if fixes:
        with path.open("w", encoding="utf-8", newline="\n") as output:
            output.writelines(kept)
    return fixes


def _rename_classes(path, classes):
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError):
        content = {}
    if not isinstance(content, dict):
        content = {}
    before = content.get("names")
    names = dict(enumerate(classes))
    if before == names or before == classes:
        return []
    content["names"] = names
    with path.open("w", encoding="utf-8", newline="\n") as output:
        yaml.safe_dump(content, output, allow_unicode=True, sort_keys=False)
    return [dict(image="data.yaml", line="", action="rename_classes", before=str(before), after=str(names))]


def fix(ds, issues, cfg):
    removals, unlabeled = set(), set()
    edits = defaultdict(dict)
    rename = False
    for issue in issues:
        if issue.severity != ERROR:
            continue
        code = issue.code
        if code in REMOVE_CODES or code.startswith("DUP_IMAGE_"):
            removals.add(issue.image)
        elif code == "MISSING_LABEL_FILE":
            unlabeled.add(issue.image)
        elif code == "BAD_CLASS_NAME":
            rename = True
        elif issue.line is not None:
            if code in DROP_CODES:
                edits[issue.image][issue.line] = "drop_line"
            elif code == "BOX_OUT_OF_IMAGE":
                edits[issue.image].setdefault(issue.line, "clip_box")

    fixes = []
    for stem in sorted(removals):
        image = ds.image_path(stem)
        if image is None:
            continue
        image.unlink()
        ds.label_path(stem).unlink(missing_ok=True)
        fixes.append(dict(image=stem, line="", action="remove_image", before=image.name, after=""))

    if rename:
        fixes.extend(_rename_classes(ds.yaml_path, cfg["classes"]))
    for stem in sorted(edits.keys() - removals):
        fixes.extend(_fix_label(ds.label_path(stem), edits[stem]))
    for stem in sorted(unlabeled - removals):
        if not ds.label_path(stem).exists():
            fixes.append(dict(image=stem, line="", action="needs_label",
                              before="(không có file)", after="chuyển người gán"))
    return fixes
