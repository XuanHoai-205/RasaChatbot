# RasaChatbot
🚀 Hướng dẫn Cài đặt và Chạy Project Rasa
Tài liệu này hướng dẫn cách thiết lập môi trường ảo và khởi chạy các thành phần cần thiết của chatbot Rasa.

# 1. Kích hoạt Môi trường ảo (Virtual Environment)
Việc sử dụng môi trường ảo giúp quản lý thư viện độc lập, tránh xung đột hệ thống.

Trên Windows:
Nếu chưa tạo: python -m venv .venv
.\.venv\Scripts\activate

Trên macOS/Linux:
Nếu chưa tạo: python3 -m venv .venv
source .venv/bin/activate

# 2. Cài đặt các thư viện cần thiết
Sau khi môi trường ảo đã được kích hoạt, hãy tiến hành cài đặt Rasa và các thư viện liên quan:

pip install --upgrade pip
pip install -r requirements.txt
# 3. Cấu hình Cơ sở dữ liệu (Database)
Project có đi kèm một file cơ sở dữ liệu để lưu trữ thông tin chatbot (ví dụ: lịch sử chat, thông tin người dùng).

File cơ sở dữ liệu: tên_file_của_bạn.db (Hãy đảm bảo file này nằm ở thư mục gốc của project).
# 4. Khởi chạy Rasa Action Server
Action Server là nơi xử lý các logic tùy chỉnh (Custom Actions) như gọi API, truy vấn cơ sở dữ liệu. Lưu ý: Bạn cần chạy lệnh này ở một terminal riêng.

rasa run actions

# 5. Tương tác với Chatbot (Rasa Shell)
Sau khi Action Server đã sẵn sàng, hãy mở một terminal mới (vẫn kích hoạt .venv) và chạy lệnh sau để bắt đầu chat trực tiếp với bot:

rasa shell
Dấu hiệu thành công: Khi terminal hiện dòng Bot loaded. Type a message and press enter (use '/stop' to exit):, bạn có thể bắt đầu nhắn tin.

Dừng lại: Gõ /stop để thoát.

