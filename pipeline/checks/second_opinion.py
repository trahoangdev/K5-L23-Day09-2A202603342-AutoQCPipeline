"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l).   ★★★ (khó nhất, đáng điểm nhất)

Test:  pytest tests/test_second_opinion.py -q

Máy kiểm quy tắc, người kiểm ý nghĩa (slide). Các lỗi như thiếu nhãn / gán nhầm lớp hợp lệ / box lỏng
KHÔNG bắt được bằng quy tắc cú pháp. Ta nhờ một model mạnh hơn "nhìn lại" và CHỈ CẢNH BÁO (model cũng có thể sai):
những ảnh bị cờ sẽ vào hàng đợi cho NGƯỜI duyệt.

`preds[stem]` = list `[id_lớp, conf, cx, cy, w, h]` của model (lấy qua `get_preds(ds, cfg, "checker")` nếu preds=None).
`L = ds.valid_boxes(stem)` = list `(id_lớp, cx, cy, w, h)` của nhãn (đã bỏ dòng hỏng).
Ngưỡng ở `cfg["second_opinion"]`: conf, min_area_px, fp_conf, iou_missing, iou_match, iou_loose.

Thuật toán gợi ý, với từng ảnh (bỏ qua ảnh không có trong preds hoặc không có file nhãn):
  P = dự đoán có conf >= conf  VÀ diện tích px (w*W * h*H) >= min_area_px
  Với mỗi dự đoán r trong P: lấy các nhãn có IoU(r, nhãn) >= iou_missing  (cands)
   - không có cands                            -> POSSIBLE_MISSING     (model thấy vật mà nhãn không có box)
   - có cands cùng lớp, tốt nhất IoU < iou_loose -> POSSIBLE_LOOSE_BOX  (đúng vật, box lỏng/lệch)
   - không có cands cùng lớp, nhưng cands tốt nhất IoU >= iou_match (khác lớp) -> POSSIBLE_WRONG_CLASS
  Với mỗi dòng nhãn hợp lệ: nếu IoU với MỌI dự đoán (conf >= fp_conf, không lọc diện tích) đều < iou_missing
                                             -> POSSIBLE_FALSE_POS  (box nhãn không khớp vật nào model thấy; Issue.line = số dòng)

Chi tiết các ca biên (test kiểm đúng các ca này)
- `cands` gồm nhãn MỌI lớp có IoU >= iou_missing; "tốt nhất cùng lớp" = cands cùng lớp có IoU lớn nhất; "tốt nhất khác lớp" tương tự với cands khác lớp.
- Thứ tự quyết định cho mỗi dự đoán: (1) cands rỗng -> MISSING. (2) có cands cùng lớp: IoU tốt nhất < iou_loose -> LOOSE_BOX, ngược lại KHÔNG cờ
  (nhãn đúng lớp đã phủ vật này, kể cả khi còn nhãn khác lớp chồng lên). (3) không có cands cùng lớp: nếu IoU tốt nhất khác lớp >= iou_match -> WRONG_CLASS;
  nếu chỉ có khác lớp với IoU trong [iou_missing, iou_match) -> không cờ gì (mơ hồ: để cho FALSE_POS / lần duyệt khác).
- Một dự đoán sinh tối đa MỘT issue (MISSING / LOOSE_BOX / WRONG_CLASS); một ảnh có thể có nhiều issue.
- Thứ tự issue: theo `ds.image_files()` rồi theo thứ tự dự đoán trong `preds[stem]`, cuối cùng là các FALSE_POS theo số dòng; `Issue.image` = stem, `Issue.line` chỉ đặt cho FALSE_POS.

Lưu ý số dòng: dùng `ds.read_label_lines(stem)` (giữ số dòng gốc, kể cả dòng hỏng/trống) để lấy `Issue.line`; `valid_boxes` KHÔNG giữ số dòng.

Tất cả severity WARN; `Issue.extra` nên có {"conf": ...} hoặc {"iou": ...} (hàng đợi duyệt dùng conf để xếp ưu tiên).

Gợi ý
- `iou_xywh` có sẵn. Dòng nhãn hỏng không được làm script chết (dùng `ds.valid_boxes` và `parse_yolo_line` trong try).
- Kết quả phụ thuộc mạnh vào ngưỡng: calibrate chúng ở Bước 3 thay vì đoán.
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line
from ..model_cache import get_preds


def _labeled_boxes(lines, n_classes):
    boxes = []
    for line, text in lines:
        try:
            class_id, *box = parse_yolo_line(text)
        except (ValueError, OverflowError):
            continue
        if 0 <= class_id < n_classes:
            boxes.append((line, class_id, box))
    return boxes


def _prediction_issue(stem, class_id, conf, box, labels, rules, classes):
    candidate_ious = []
    same_class_ious = []
    for _, label_class, label_box in labels:
        overlap = iou_xywh(box, label_box)
        if overlap >= rules["iou_missing"]:
            candidate_ious.append(overlap)
            if class_id == label_class:
                same_class_ious.append(overlap)

    name = classes[class_id]
    if not candidate_ious:
        code, message = "POSSIBLE_MISSING", f"model thấy {name} nhưng chưa có box khớp"
        best_iou = None
    elif same_class_ious:
        best_iou = max(same_class_ious)
        if best_iou >= rules["iou_loose"]:
            return None
        code, message = "POSSIBLE_LOOSE_BOX", f"box {name} cùng lớp nhưng IoU chỉ {best_iou:.3f}"
    else:
        best_iou = max(candidate_ious)
        if best_iou < rules["iou_match"]:
            return None
        code, message = "POSSIBLE_WRONG_CLASS", f"model dự đoán {name} tại box khác lớp (IoU {best_iou:.3f})"

    extra = {"conf": conf, "class_id": class_id, "box": box}
    if best_iou is not None:
        extra["iou"] = best_iou
    return Issue("second_opinion", WARN, code, stem, message, extra=extra)


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")
    rules = cfg["second_opinion"]
    issues = []
    for path in ds.image_files():
        stem = path.stem
        if stem not in preds:
            continue
        lines = ds.read_label_lines(stem)
        if lines is None:
            continue
        size = ds.image_size(stem)
        if size is None:
            continue

        labels = _labeled_boxes(lines, len(ds.classes))
        fp_boxes = []
        for class_id, conf, cx, cy, width, height in preds[stem]:
            box = (cx, cy, width, height)
            if conf >= rules["fp_conf"]:
                fp_boxes.append(box)
            area_px = (width * size[0]) * (height * size[1])
            if conf >= rules["conf"] and area_px >= rules["min_area_px"]:
                issue = _prediction_issue(stem, class_id, conf, box, labels, rules, ds.classes)
                if issue is not None:
                    issues.append(issue)

        for line, class_id, box in labels:
            best_iou = max((iou_xywh(box, pred_box) for pred_box in fp_boxes), default=0.0)
            if not fp_boxes or best_iou < rules["iou_missing"]:
                issues.append(Issue("second_opinion", WARN, "POSSIBLE_FALSE_POS", stem,
                                    f"box {ds.classes[class_id]} không khớp dự đoán nào",
                                    line, {"iou": best_iou}))
    return issues
