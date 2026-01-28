# Website Bán Giày Online

Đây là một Website bán giày được xây dựng bằng Django

---

## Chức năng 

- Đăng ký, Đăng nhập: Người dùng có thể tạo tài khoản để đăng nhập vào website. Admin có quyền thêm, sửa, xoá thông tin người dùng
- Quản lý sản phẩm: Admin có quyền thêm, sửa, xoá sản phẩm, thể loại hiển thị trên trang chủ

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
