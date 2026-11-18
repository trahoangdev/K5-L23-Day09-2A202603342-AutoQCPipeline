# Báo cáo Day 09 — Hoàng Trọng Trà, 2A202603342

## 1. Kết luận trước

**Hold (mã thoát 10).** Cửa vào giữ **205/224 ảnh** và loại 19 ảnh. Sau sửa tự động và duyệt mô phỏng, tập còn **0 lỗi bắt buộc**. Có **38/205 ảnh (18,54%)** còn cảnh báo chưa duyệt, vượt ngưỡng 10%. Bản nháp `export/clean_v1` chứa 205 ảnh theo manifest. [Tóm tắt](reports/08_summary.json) · [Manifest](export/clean_v1/manifest.json)

## 2. Lỗi và phân việc

V1 gồm 19 dòng ở cửa vào trên 224 ảnh và 189 dòng QC trên 205 ảnh. Mỗi ảnh có thể sinh nhiều dòng QC. [Danh sách lỗi V1](reports/02_error_list_v1.csv)

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `CORRUPT_IMAGE` | 2 ảnh | Máy | Loại ảnh giải mã thất bại. |
| `BAD_SIZE` | 3 ảnh | Máy | Loại ảnh dưới chuẩn kích thước. |
| `DUP_IMAGE_EXACT` | 8 ảnh | Máy | Loại ảnh trùng từng byte. |
| `DUP_IMAGE_NEAR` | 2 ảnh | Máy | Loại ảnh gần trùng theo ngưỡng pHash. |
| `BAD_FORMAT` | 3 dòng | Máy | Xóa dòng sai định dạng. |
| `BAD_CLASS_ID` | 6 dòng | Máy | Xóa dòng có ID ngoài bảng lớp. |
| `BOX_ZERO` | 4 dòng | Máy | Xóa box có kích thước không dương. |
| `DUP_BOX` | 7 dòng | Máy | Xóa box lặp cùng lớp. |
| `BOX_OUT_OF_IMAGE` | 8 dòng | Máy | Cắt box về biên ảnh. |
| `BAD_CLASS_NAME` | 2 dòng báo lỗi | Máy | Chuẩn hóa bảng tên lớp trong YAML. |
| `MISSING_LABEL_FILE` | 6 ảnh | Người | Người gán nhãn. Máy chỉ ghi `needs_label`. |
| `EMPTY_LABEL` | 12 ảnh | Người | Xem ảnh nền hay bỏ sót nhãn. |
| `BOX_TINY` | 6 dòng | Người | Kiểm box quá nhỏ theo quy tắc gán nhãn. |
| `BOX_HUGE` | 3 dòng | Người | Xem box lớn có phủ đúng vật hay không. |
| `CLASS_RARE` | 4 dòng ở cấp tập dữ liệu | Người | Rà các token lớp có tần suất thấp. |
| `POSSIBLE_MISSING` | 53 dòng | Người | Xác nhận vật bị bỏ sót. |
| `POSSIBLE_WRONG_CLASS` | 18 dòng | Người | Xác nhận đúng lớp của vật. |
| `POSSIBLE_LOOSE_BOX` | 28 dòng | Người | Kiểm box có ôm sát vật hay không. |
| `POSSIBLE_FALSE_POS` | 29 dòng | Người | Kiểm box có gán nhầm nền hoặc vật khác. |

Máy ghi 35 thao tác gồm 20 xóa dòng, 8 cắt box, 1 chuẩn hóa tên lớp và 6 chuyển gán nhãn. Hàng đợi có **125 ảnh**. `img_0020` đứng đầu với 11,524 điểm do cộng điểm xóa dòng, thiếu box và sai lớp. Sáu ảnh thiếu file nhãn xếp ngay sau với 10 điểm mỗi ảnh. Lượt duyệt mô phỏng xem **80/125 ảnh**. Trong số đó, 74 ảnh có **94/123 dòng cảnh báo ngữ nghĩa V2**. Các dòng này là nghi vấn cần xem. [Nhật ký sửa](reports/03_fixes.csv) · [Hàng đợi](reports/05_review_queue.csv) · [Nhật ký duyệt](reports/06_review_log.csv)

## 3. Calibration (2 ngưỡng)

| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 4 | Gần trùng **1,00 / 0,50 → 1,00 / 0,67**. Trùng byte **1,00 / 1,00** ở cả hai mốc. | Bắt thêm 1/6 ca gần trùng. Mốc 4 đạt cùng kết quả với các mốc 6–14 và hạn chế loại nhầm ảnh. |
| `second_opinion.conf` | 0.25 | 0.60 | Thiếu box **0,50 / 1,00 → 0,57 / 1,00**. Sai lớp **0,56 / 0,83 → 0,62 / 0,83**. Box lỏng **0,29 / 0,40 → 0,20 / 0,20**. Box thừa giữ **0,31 / 1,00**. | Giảm báo nhầm thiếu box và sai lớp, giữ recall của hai nhóm. Bỏ sót thêm một ca box lỏng. Box thừa dùng `fp_conf` riêng. |

Bộ calib chỉ có sáu ca gần trùng và năm trong sáu ca sai lớp là `person → car`. Tỷ lệ đo được khó đại diện cho các lỗi nhầm giữa các loại xe. Ở raw, cả hai cặp bị gắn cờ gần trùng có khoảng cách pHash bằng 0 và chênh lệch mức xám trung bình dưới 0,5/255 sau khi đưa về cùng kích thước. [Bảng sweep](calibration/calibration_report.md)

## 4. Cửa chặn và điều pipeline KHÔNG bắt được

Lần thử `python -m pipeline.run --budget 0 --work work/no_review_demo --reports work/no_review_reports --export-dir work/no_review_export` còn **6 `MISSING_LABEL_FILE`**. Gate trả **Rework**, mã **20**, và không tạo manifest. Chạy lại cấu hình chính trên thư mục riêng cho cùng CSV, quyết định và manifest.

Ba ví dụ đối chiếu từ nhãn raw và báo cáo V1 gồm box lặp cùng lớp ở `img_0001` dòng 3 (IoU 0,995 với dòng 1), ID 93 ở `img_0020` dòng 3 và box tràn biên 0,023 ở `img_0030` dòng 9. [Báo cáo V1](reports/02_error_list_v1.csv)

- **Ảnh gần trùng biến đổi mạnh.** `calib_038` là biến thể của `calib_024` trong đáp án calibration. Khoảng cách pHash là **18**, vượt ngưỡng 4 nên cặp này bị bỏ sót.
- **Box lỏng khi model thiếu tự tin.** Tại `calib_012` dòng 1, box đã được nới 1,45 lần. Dự đoán cùng lớp có IoU **0,465** và confidence **0,155**. Dự đoán bị lọc ở ngưỡng 0,60 trước khi xét độ khớp, nên checker bỏ sót cảnh báo box lỏng. [Đáp án calibration](../data/calib/MANIFEST.csv)

## 5. Train: raw vs clean (tùy chọn, chấm riêng)

Chạy trên Google Colab Tesla T4 với Ultralytics 8.4.214. Hai biến thể cùng khởi tạo từ `yolo26n.pt`, train 20 epoch với seed 0 và 1, batch 16 và ảnh 640 px. Cả hai dùng 40 ảnh `gold_val` để chọn checkpoint và cùng 100 ảnh `test` để đánh giá cuối.

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 205 | 2 | 0.700 ± 0.030 | 0.486 ± 0.013 | 0.715 ± 0.073 | 0.615 ± 0.017 |

Cột số ảnh là số ảnh đưa vào loader. Trong lượt chạy, Ultralytics giữ **213/224** ảnh raw và **205/205** ảnh clean. Chênh mAP50 trung bình `clean − raw` là **−0,0254**, nhỏ hơn độ lệch giữa hai seed của clean (**0,0305**). Raw cao hơn trong cả hai seed, nhưng chênh lệch dao động từ **−0,0468** đến **−0,0040**. Hai seed chưa đủ để kết luận khác biệt sẽ lặp lại. Trong bốn lớp, AP50 trung bình của `car` tăng khoảng **0,011**, còn `truck` giảm khoảng **0,090**. [Bảng và biểu đồ so sánh](results/comparison.md)

- **Rò rỉ test có thể nâng điểm raw.** Cửa vào gắn cờ 4 ảnh raw trùng với test. Có thể đánh giá lại cùng các checkpoint trên phần test còn lại sau khi loại bốn ảnh đối ứng để xem chênh lệch phụ thuộc vào rò rỉ đến đâu. [Cờ rò rỉ](reports/01_intake.csv)
- **Thành phần ảnh và chất lượng nhãn cùng thay đổi.** Hai loader dùng số ảnh khác nhau, và clean vẫn còn 38 ảnh có cảnh báo chưa duyệt. Để tách tác động của sửa nhãn, có thể so sánh hai bộ nhãn trên cùng các ảnh hợp lệ và kiểm tra số box cùng lỗi theo từng lớp, trước hết là `truck`. [Cảnh báo sau duyệt](reports/07_error_list_v3.csv)

## 6. Quyết định và ghi chú AI

Giữ **Hold**. Với 205 ảnh, Release cần tiếp tục duy trì 0 lỗi bắt buộc và còn tối đa 20 ảnh có cảnh báo chưa duyệt. Nếu số ảnh và các cờ khác giữ nguyên, cần xử lý hoặc duyệt thêm ít nhất **18 trong 38 ảnh** đang có cờ.

- **Prompt chính.** Đầu vào là nhãn YOLO và dự đoán cache. Dùng quy tắc trong docstring và ngưỡng trong `cfg` để sinh `Issue`, ghi thay đổi và quyết định gate. Chỉ sửa nhãn trên bản làm việc.
- **Kiểm code AI.** Chạy 79 test của repo, thêm một phép thử tạm cho ID vô hạn, mép đúng ngưỡng và giữ số dòng gốc, rồi đo trên tập lỗi chèn và chạy lại pipeline.
- **Một lần AI sai.** Bản đầu dùng tham số `newline` của `Path.write_text`, không phù hợp Python 3.9. Đã đổi sang `Path.open` khi ghi file.

**CVAT.** Task 20 dùng 20 ảnh đầu hàng đợi QC và nhãn `work/run/ds` nhập bằng YOLO 1.1. Bộ lọc `Width < 20` khớp **9 box trên 4/20 ảnh** gồm `img_0020` (3), `img_0030` (3), `img_0053` (1) và `img_0135` (2). Bốn ảnh này có **0 dòng `BOX_TINY`** trong V3. Chín box có chiều rộng từ 15,01 đến 19,29 px, còn pipeline dùng cạnh ngắn dưới 12 px. Bộ lọc chỉ dùng để rà nhãn. Người gán có thể bật `can_review` trên box còn nghi ngờ để chuyển người khác xem, tương tự cách cảnh báo `POSSIBLE_*` đưa ảnh vào hàng đợi của pipeline. CVAT 2.74.1 yêu cầu danh sách giá trị checkbox khác rỗng, nên project dùng `values: ["false"]` khi nhập cấu hình nhãn. [Ảnh bộ lọc](cvat_width_lt20.jpg) · [Báo cáo V3](reports/07_error_list_v3.csv)
