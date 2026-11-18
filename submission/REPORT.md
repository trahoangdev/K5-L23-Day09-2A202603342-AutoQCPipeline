# Báo cáo Day 09 — Hoàng Trọng Trà, 2A202603342

## 1. Kết luận

**Hold (mã thoát 10).** Cửa vào giữ **205/224 ảnh** và loại 19 ảnh. Sau sửa tự động và duyệt mô phỏng, tập còn **0 lỗi bắt buộc**. Có **38/205 ảnh (18,54%)** còn cảnh báo chưa duyệt, vượt ngưỡng 10%. Bản nháp `export/clean_v1` chứa 205 ảnh theo manifest. [Tóm tắt](reports/08_summary.json) · [Manifest](export/clean_v1/manifest.json)

## 2. Lỗi và phân việc

V1 gồm 19 dòng tại cửa vào và 189 dòng QC trên 205 ảnh. Các số dưới đây đếm **dòng báo cáo** theo mã. Mẫu số kiểm tra là 224 ảnh ở cửa vào và 205 ảnh ở các vòng QC. Một ảnh có thể có nhiều dòng cảnh báo. [Danh sách lỗi V1](reports/02_error_list_v1.csv) · [Danh sách lỗi V3](reports/07_error_list_v3.csv)

| Mã | V1 | V3 | Ai xử lý |
|---|---:|---:|---|
| `CORRUPT_IMAGE`, `BAD_SIZE` | 2, 3 | 0, 0 | Máy loại ảnh hỏng hoặc dưới chuẩn |
| `DUP_IMAGE_EXACT`, `DUP_IMAGE_NEAR`, `LEAK_TEST` | 8, 2, 4 | 0, 0, 0 | Máy loại ảnh trùng và ảnh có cờ rò rỉ |
| `BAD_FORMAT`, `BAD_CLASS_ID`, `BOX_ZERO`, `DUP_BOX` | 3, 6, 4, 7 | 0, 0, 0, 0 | Máy xóa dòng lỗi, người rà lại ảnh đã sửa |
| `BOX_OUT_OF_IMAGE` | 8 | 0 | Máy cắt box về biên ảnh |
| `BAD_CLASS_NAME` | 2 | 0 | Máy chuẩn hóa bảng tên lớp bằng một lần ghi YAML |
| `MISSING_LABEL_FILE` | 6 | 0 | Người gán nhãn. Máy ghi `needs_label` |
| `EMPTY_LABEL`, `BOX_TINY`, `BOX_HUGE` | 12, 6, 3 | 4, 7, 3 | Người kiểm ảnh nền và kích thước box |
| `CLASS_RARE` | 4 | 0 | Rà thống kê token lớp ở cấp tập dữ liệu |
| `POSSIBLE_MISSING`, `POSSIBLE_WRONG_CLASS` | 53, 18 | 13, 3 | Người xác nhận thiếu box hoặc sai lớp |
| `POSSIBLE_LOOSE_BOX`, `POSSIBLE_FALSE_POS` | 28, 29 | 20, 21 | Người xác nhận box lỏng hoặc thừa |

Máy ghi 35 thao tác gồm 20 xóa dòng, 8 cắt box, 1 chuẩn hóa tên lớp và 6 chuyển gán nhãn. Hàng đợi có **125 ảnh**. `img_0020` đứng đầu với 11,524 điểm do cộng điểm xóa dòng, thiếu box và sai lớp. Sáu ảnh thiếu file nhãn xếp ngay sau với 10 điểm mỗi ảnh. Lượt duyệt mô phỏng xem **80/125 ảnh**. Trong số đó, 74 ảnh có **94/123 dòng cảnh báo ngữ nghĩa V2**. Các dòng này là nghi vấn cần xem. [Nhật ký sửa](reports/03_fixes.csv) · [Hàng đợi](reports/05_review_queue.csv) · [Nhật ký duyệt](reports/06_review_log.csv)

## 3. Calibration

| Ngưỡng | Trước → Sau | Precision / Recall trước → sau |
|---|---|---|
| `duplicates.phash_dist` | `2 → 4` | Gần trùng **1,00 / 0,50 → 1,00 / 0,67**. Trùng byte **1,00 / 1,00** ở cả hai mốc. |
| `second_opinion.conf` | `0.25 → 0.60` | Thiếu box **0,50 / 1,00 → 0,57 / 1,00**. Sai lớp **0,56 / 0,83 → 0,62 / 0,83**. Box lỏng **0,29 / 0,40 → 0,20 / 0,20**. Box thừa giữ **0,31 / 1,00** vì dùng `fp_conf` riêng. |

Chọn pHash 4 vì bắt thêm 1/6 ca gần trùng và có cùng kết quả với các mốc 6–14. Ngưỡng nhỏ giúp hạn chế loại nhầm ảnh khác nhau. Trên raw, hai cặp gần trùng có khoảng cách pHash bằng 0 và chênh lệch mức xám trung bình dưới 0,5/255 sau khi đưa về cùng kích thước. Chọn confidence 0,60 vì giảm báo nhầm ở hai nhóm ưu tiên là thiếu box và sai lớp, đồng thời giữ nguyên recall của cả hai. Đánh đổi là bỏ sót thêm một trong năm ca box lỏng. Bộ calib chỉ có sáu ca gần trùng và năm trong sáu ca sai lớp là `person → car`, nên các tỷ lệ này khó đại diện cho cảnh hiếm hoặc lỗi nhầm giữa các loại xe trong raw. [Bảng sweep](calibration/calibration_report.md)

## 4. Cửa chặn và điểm mù

Lần thử `python -m pipeline.run --budget 0 --work work/no_review_demo --reports work/no_review_reports --export-dir work/no_review_export` còn **6 `MISSING_LABEL_FILE`**. Gate trả **Rework**, mã **20**, và không tạo manifest. Chạy lại cấu hình chính trên thư mục riêng cho cùng CSV, quyết định và manifest.

- **Ảnh gần trùng biến đổi mạnh.** `calib_038` là biến thể của `calib_024` trong đáp án calibration. Khoảng cách pHash là **18**, vượt ngưỡng 4 nên cặp này bị bỏ sót.
- **Box lỏng khi model thiếu tự tin.** Tại `calib_012` dòng 1, box đã được nới 1,45 lần. Dự đoán cùng lớp có IoU **0,465** và confidence **0,155**. Dự đoán bị lọc ở ngưỡng 0,60 trước khi xét độ khớp, nên checker bỏ sót cảnh báo box lỏng. [Đáp án calibration](../data/calib/MANIFEST.csv)

## 5. Train raw và clean

Chưa chạy. Phần thực hiện tập trung vào QC và kiểm lại gate. Môi trường PyTorch hiện tại chỉ dùng CPU. Dữ liệu hiện có chưa cho phép kết luận về chênh lệch mAP.

## 6. Quyết định và ghi chú AI

Giữ **Hold**. Với 205 ảnh, Release cần tiếp tục duy trì 0 lỗi bắt buộc và còn tối đa 20 ảnh có cảnh báo chưa duyệt. Nếu số ảnh và các cờ khác giữ nguyên, cần xử lý hoặc duyệt thêm ít nhất **18 trong 38 ảnh** đang có cờ.

- **Prompt chính.** Tiếp tục các bước 2–5 theo đề. Đầu vào là nhãn YOLO và dự đoán cache. Dùng quy tắc trong docstring và ngưỡng trong `cfg` để sinh `Issue`, ghi thay đổi và quyết định gate. Chỉ sửa nhãn trên bản làm việc.
- **Kiểm code AI.** Chạy 79 test của repo, thêm một phép thử tạm cho ID vô hạn, mép đúng ngưỡng và giữ số dòng gốc, rồi đo trên tập lỗi chèn và chạy lại pipeline.
- **Một lần AI sai.** Bản đầu dùng tham số `newline` của `Path.write_text`, không phù hợp Python 3.9. Đã đổi sang `Path.open` khi ghi file.
