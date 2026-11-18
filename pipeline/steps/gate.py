"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.   ★

Test:  pytest tests/test_gate.py -q

Cây quyết định Day 07 (slide Day 09: "Lỗi bắt buộc chặn pipeline; lỗi cảnh báo chuyển người xem"):

  còn ≥ 1 lỗi bắt buộc (severity ERROR)                          -> "Rework"
  không còn lỗi bắt buộc, nhưng tỉ lệ ẢNH còn cảnh báo
      >= cfg["gate"]["warn_ratio_hold"]                          -> "Hold"
  còn lại                                                        -> "Release"

Tỉ lệ cảnh báo = (số ẢNH khác nhau có ≥ 1 cảnh báo) / (tổng số ảnh).  Chú ý:
- chỉ đếm issue có `image` nằm trong `image_stems` (bỏ "<dataset>", "data.yaml");
- bỏ qua ảnh nằm trong `reviewed` (người đã xem, cảnh báo của ảnh đó coi như đã xử lý) — nhưng LỖI BẮT BUỘC thì không bao giờ được bỏ qua;
- mẫu số là số ảnh, không phải số issue.

Trả về dict: decision, n_errors, n_warn_images, n_images, warn_ratio (làm tròn 4 chữ số), reasons (list[str], giải thích bằng tiếng Việt, có số liệu).
"""
from ..common import ERROR, WARN


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    pending = stems.difference(reviewed)
    n_errors = 0
    warn_images = set()
    for issue in issues:
        if issue.severity == ERROR:
            n_errors += 1
        elif issue.severity == WARN and issue.image in pending:
            warn_images.add(issue.image)

    ratio = len(warn_images) / len(stems) if stems else 0.0
    threshold = cfg["gate"]["warn_ratio_hold"]
    warning_summary = f"{len(warn_images)}/{len(stems)} ảnh còn cảnh báo chưa duyệt ({ratio:.2%})"
    if n_errors:
        decision = "Rework"
        reasons = [f"Còn {n_errors} lỗi bắt buộc", warning_summary]
    elif ratio >= threshold:
        decision = "Hold"
        reasons = ["Đã hết lỗi bắt buộc", f"{warning_summary}, đạt hoặc vượt ngưỡng Hold {threshold:.0%}"]
    else:
        decision = "Release"
        reasons = ["Đã hết lỗi bắt buộc", f"{warning_summary}, dưới ngưỡng Hold {threshold:.0%}"]

    return dict(decision=decision, n_errors=n_errors, n_warn_images=len(warn_images),
                n_images=len(stems), warn_ratio=round(ratio, 4), reasons=reasons)
