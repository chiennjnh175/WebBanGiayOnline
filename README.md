# Website Bán Giày Online

---

## Chức năng 

### Nhóm Chức năng Người dùng (User & Authentication)
- Đăng ký tài khoản: Cho phép người dùng tạo tài khoản mới với các trường bắt buộc (Họ tên, Email, Username).
- Đăng nhập/Đăng xuất: Xác thực người dùng và quản lý phiên làm việc.
Quản lý hồ sơ (Profile): Người dùng có thể cập nhật thông tin cá nhân như số điện thoại và địa chỉ giao hàng mặc định.

### Nhóm Chức năng Mua sắm (Shopping & Browsing)
- Xem danh sách sản phẩm: Hiển thị tất cả giày trên trang chủ.
- Tìm kiếm sản phẩm: Tìm kiếm thông minh theo tên giày, tên hãng hoặc tên thể loại (Sử dụng Q objects).
- Lọc kép (Cumulative Filtering): Cho phép lọc đồng thời theo Hãng (Brand) và Thể loại (Category) mà không làm mất trạng thái của nhau.
- Xem chi tiết sản phẩm:
 + Hiển thị thông tin, giá cả và mô tả.
 + Slide ảnh: Tự động quét và hiển thị các ảnh liên quan của sản phẩm từ thư mục media.
- Quản lý biến thể (Variants): Chọn Màu sắc và Size. Hệ thống tự động kiểm tra tồn kho theo từng cặp Màu/Size bằng JavaScript mà không cần tải lại trang.

### Nhóm Chức năng Giỏ hàng (Cart Management)
- Thêm vào giỏ hàng: Lưu chính xác biến thể (Size/Màu) khách đã chọn.
- Kiểm tra tồn kho tức thời: Ngăn chặn việc thêm vào giỏ nếu sản phẩm đã hết hàng hoặc số lượng trong giỏ vượt quá số lượng trong kho.
- Điều chỉnh giỏ hàng: Cho phép tăng, giảm số lượng hoặc xóa sản phẩm khỏi giỏ.
- Tính toán tự động: Tự động tính thành tiền cho từng sản phẩm và tổng giá trị giỏ hàng.

### Nhóm Chức năng Đơn hàng (Order System)
- Thanh toán (Checkout): Xác nhận thông tin giao hàng và tạo đơn hàng.
- Quản lý tồn kho tự động: Trừ số lượng kho của từng biến thể ngay khi đơn hàng được tạo thành công.
- Lịch sử đơn hàng: Người dùng xem lại danh sách các đơn đã đặt.
- Chi tiết đơn hàng: Xem cụ thể từng món đồ trong một đơn hàng cũ.
- Hủy đơn hàng & Hoàn kho: Cho phép khách hủy đơn ở trạng thái "Chờ xử lý" và tự động cộng trả lại số lượng vào kho.

### Nhóm Chức năng Quản trị (Admin Panel - Dành cho Staff)
- Dashboard thống kê:
+ Thống kê doanh thu (tổng tiền các đơn đã hoàn thành).
+ Đếm số lượng đơn hàng theo từng trạng thái (Chờ xử lý, Đang giao, v.v.).
+ Thống kê tổng số sản phẩm, người dùng.
+ Cảnh báo hàng sắp hết: Hiển thị danh sách các biến thể có số lượng tồn kho <= 5 để Admin nhập hàng kịp thời.
- Quản lý sản phẩm & Biến thể: Admin có thể thêm mới sản phẩm và quản lý các Size/Màu đi kèm thông qua giao diện Inline (quản lý nhiều size cùng lúc).
- Cập nhật trạng thái đơn hàng: Thay đổi lộ trình đơn hàng (từ Chờ xử lý -> Đang giao -> Hoàn thành).

### Hướng dẫn cài đặt
- Clone dự án 
```bash
git clone git@github.com:chiennjnh175/webBanGiayOnline.git
```
- Thiết lập môi trường ảo
```bash
python -m venv venv
```

- Cài thư viện cần thiết
```bash
pip install django pillow
```
- Khởi tạo database, tạo tài khoản admin và chạy dự án
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
