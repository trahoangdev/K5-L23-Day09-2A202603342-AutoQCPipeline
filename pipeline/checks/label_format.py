"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from collections import defaultdict
from math import isclose

from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    rules = cfg["label_format"]
    tolerance = rules["overflow_tol"]
    issues = []
    for path in ds.label_files():
        stem = path.stem
        size = ds.image_size(stem)
        previous_by_class = defaultdict(list)
        for line, text in ds.read_label_lines(stem) or []:
            try:
                class_id, cx, cy, width, height = parse_yolo_line(text)
            except (ValueError, OverflowError) as exc:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, str(exc), line))
                continue
            if not 0 <= class_id < len(ds.classes):
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem,
                                    f"ID lớp {class_id} ngoài khoảng 0–{len(ds.classes) - 1}", line))
                continue
            if width <= 0 or height <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem,
                                    f"rộng {width:g} hoặc cao {height:g} không dương", line))
                continue

            overflow = max(0.0, width / 2 - cx, height / 2 - cy,
                           cx + width / 2 - 1, cy + height / 2 - 1)
            if overflow > tolerance and not isclose(overflow, tolerance, rel_tol=1e-12):
                issues.append(Issue("label_format", ERROR, "BOX_OUT_OF_IMAGE", stem,
                                    f"mép box tràn {overflow:.4g} > {tolerance:g}", line,
                                    {"overflow": overflow}))

            box = (cx, cy, width, height)
            for previous_line, previous_box in previous_by_class[class_id]:
                overlap = iou_xywh(box, previous_box)
                if overlap > rules["dup_box_iou"]:
                    issues.append(Issue("label_format", ERROR, "DUP_BOX", stem,
                                        f"trùng box cùng lớp ở dòng {previous_line} (IoU {overlap:.3f})",
                                        line, {"of_line": previous_line, "iou": overlap}))
                    break
            previous_by_class[class_id].append((line, box))

            if size is not None:
                short_side = min(width * size[0], height * size[1])
                if short_side < rules["min_box_px"]:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem,
                                        f"cạnh ngắn {short_side:.1f} px < {rules['min_box_px']} px", line))
            area = width * height
            if area > rules["max_box_frac"]:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem,
                                    f"diện tích {area:.1%} ảnh > {rules['max_box_frac']:.0%}", line))
    return issues
