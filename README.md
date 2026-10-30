# Excel → Google Form

1. Điền file `mau_danh_sach.xlsx`, giữ nguyên 4 tiêu đề. Số điện thoại phải là văn bản, đúng 10 chữ số. Email trống được bỏ qua, không báo lỗi và không điền vào Form. Email thiếu hậu tố và có tên tài khoản hợp lệ sẽ được thêm `@gmail.com` (ví dụ `nguyenvana` → `nguyenvana@gmail.com`). Email đã có `@` giữ nguyên và vẫn được kiểm tra định dạng Gmail.
2. Trong thư mục này chạy `docker compose up -d --build`.
3. Mở http://localhost:8501, tải Excel, kiểm tra lỗi. Nhấn Đọc câu hỏi trên Form và tự ghép bốn cột.
4. Câu trắc nghiệm và checkbox mặc định dùng **🎲 Chọn đáp án ngẫu nhiên**: trắc nghiệm chọn 1 đáp án, checkbox chọn từ 1 đến toàn bộ đáp án (số lượng được bốc ngẫu nhiên). Có thể đổi từng câu sang cột Excel; khi đó dữ liệu phải khớp nhãn đáp án trên Form. Bốn trường Họ và tên, Số điện thoại, Email, Lớp vẫn phải ghép đủ với Excel. Câu văn bản bắt buộc khác cần thêm cột Excel tương ứng.
   Mỗi lần điền thử hoặc gửi sẽ bốc đáp án mới. Checkbox có giới hạn số lựa chọn hoặc đáp án Khác cần nhập chữ có thể không phù hợp với chế độ ngẫu nhiên; hãy ghép dữ liệu Excel cho những câu này.
5. Điền thử, xác nhận phù hợp, rồi gửi 1 dòng để kiểm tra trước khi tăng số lượng.

Điểm Toán, Vật lí, Hoá học, Ngữ Văn, Tiếng Anh và Sinh học tự chọn ngẫu nhiên trong dãy `7,0; 7,2; …; 9,4` (13 mức), độc lập cho từng môn và mỗi lần điền. Không cần cột điểm trong Excel. Vẽ Mỹ thuật, Địa lý và Môn khác luôn để trống, kể cả khi Excel có dữ liệu cho các môn này. Các ô điểm TSA/SPT/VSAT, chứng chỉ quy đổi và khối V/H không áp dụng quy tắc random này.

LƯU Ý: Công cụ dựa vào giao diện Google Forms của thời điểm phát triển; các Form nhiều trang, giới hạn đăng nhập, CAPTCHA hoặc loại câu hỏi đặc biệt có thể không hỗ trợ. Chưa kiểm thử với biểu mẫu HUCE thật. Xác minh phản hồi đầu tiên trước khi gửi hàng loạt. Nếu giao diện Form đổi, dừng và sửa mã thay vì cố gửi.

Nhật ký gửi ghi vào `output/submissions.sqlite3`; giữ nguyên thư mục này khi cập nhật Docker. Khi đổi file Excel, phần mềm xem như một lô mới, nên cần tự đối chiếu trùng với lượt nhập trước.
