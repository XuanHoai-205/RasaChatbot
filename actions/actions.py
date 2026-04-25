import sqlite3
from typing import List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rank_bm25 import BM25Okapi
import re
import os
import google.generativeai as genai
import dotenv

dotenv.load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
    print("GOOGLE_API_KEY đã được nạp thành công")
else:
    print("Cảnh báo: GOOGLE_API_KEY chưa được thiết lập!")


class ActionTraLoiCauHoi(Action):
    documents = None
    doc_map = None
    bm25 = None

    def __init__(self):
        """Load toàn bộ dữ liệu ngay khi action server start"""
        if ActionTraLoiCauHoi.documents is None:
            ActionTraLoiCauHoi.documents, ActionTraLoiCauHoi.doc_map = self._fetch_all_laws()
            if ActionTraLoiCauHoi.documents:
                tokenized = [self._normalize_text(doc).split()
                             for doc in ActionTraLoiCauHoi.documents]
                ActionTraLoiCauHoi.bm25 = BM25Okapi(tokenized)
                print(f"BM25 đã khởi tạo với {len(ActionTraLoiCauHoi.documents)} documents")

    def name(self) -> str:
        return "action_tra_loi_cau_hoi"

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).lower().strip()

    def _fetch_all_laws(self):
        """Gom dữ liệu theo từng Điều (bao gồm khoản + điểm)"""
        print("Đang load dữ liệu từ vbpl.db ...")
        all_docs, doc_map = [], {}

        try:
            conn = sqlite3.connect("vbpl.db")
            cursor = conn.cursor()

            # Bật chế độ tối ưu SQLite
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA temp_store=MEMORY;")
            cursor.execute("PRAGMA cache_size=-64000;")          # ~64MB cache
            cursor.execute("PRAGMA group_concat_max_len = 1000000;")  # ~1MB cho GROUP_CONCAT

            query = """
            SELECT 
                v.ten AS vanban_ten, v.so_hieu, v.ngay_ban_hanh, v.ngay_hieu_luc,
                v.co_quan, v.hieu_luc,
                c.ten_chuong,
                d.id_dieu, d.ten_dieu, d.noi_dung,
                all_khoan,
                all_diem
            FROM (
                SELECT 
                    d.id_dieu, d.ten_dieu, d.noi_dung, d.chuong_id,
                    GROUP_CONCAT(k.ten_khoan || ': ' || IFNULL(k.noi_dung, ''), ' || ') AS all_khoan,
                    GROUP_CONCAT(m.ten_diem || ': ' || IFNULL(m.noi_dung, ''), ' || ') AS all_diem
                FROM dieu d
                LEFT JOIN khoan k ON d.id_dieu = k.dieu_id
                LEFT JOIN diem m ON k.id_khoan = m.khoan_id
                GROUP BY d.id_dieu
            ) d
            LEFT JOIN chuong c ON d.chuong_id = c.id_chuong
            LEFT JOIN vanban v ON c.vanban_id = v.id;
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for i, row in enumerate(rows):
                (
                    vanban_ten, so_hieu, ngay_bh, ngay_hl,
                    co_quan, hieu_luc,
                    ten_chuong,
                    id_dieu, ten_dieu, dieu_nd,
                    all_khoan, all_diem
                ) = row

                parts = []
                if vanban_ten:
                    parts.append(f"Văn bản: {vanban_ten} ({so_hieu})")
                if ngay_bh:
                    parts.append(f"Ban hành: {ngay_bh}, Hiệu lực: {ngay_hl}")
                if co_quan:
                    parts.append(f"Cơ quan: {co_quan}, Tình trạng: {hieu_luc}")
                if ten_chuong:
                    parts.append(f"Chương: {ten_chuong}")
                if ten_dieu:
                    parts.append(f"{ten_dieu}: {dieu_nd or ''}")
                if all_khoan:
                    parts.append(f"Khoản: {all_khoan}")
                if all_diem:
                    parts.append(f"Điểm: {all_diem}")

                text = " | ".join(parts)
                all_docs.append(text)
                doc_map[i] = text

            conn.close()
            print(f"Đã load {len(all_docs)} điều (đã gom cả khoản + điểm)")
        except Exception as e:
            print(f"Lỗi khi đọc DB: {e}")

        return all_docs, doc_map

    def _ask_gemini(self, question: str, docs: List[str]) -> str:
        context = "\n\n".join([f"[Đoạn {i+1}] {doc[:500]}" for i, doc in enumerate(docs)])
        prompt = f"""
Người dùng hỏi: {question}

Các đoạn luật liên quan tìm được:
{context}

Hướng dẫn trả lời:
1. Nếu có thông tin chính xác trong dữ liệu:
   - Trích dẫn số điều/khoản luật.
   - Trình bày đẹp, dễ đọc.
   - Khi liệt kê các điểm quan trọng, dùng dấu + và xuống dòng.
    + Điều 5: Quy định về nghĩa vụ... 
    + Điều 6: Quy định về quyền lợi...
2. Nếu không có thông tin chính xác:
   - Dựa trên các đoạn luật được xếp hạng cao nhất, suy luận câu trả lời hợp lý.
   - Ghi chú rằng đây là kết quả suy luận từ các văn bản liên quan.
   - Trình bày vẫn dùng dấu + cho các điểm quan trọng, xuống dòng để người đọc dễ theo dõi.

3. Nếu không thể trả lời:
   - Nói rõ: "Không có trong dữ liệu".

Yêu cầu:
- Trả lời ngắn gọn, dễ hiểu cho người dùng phổ thông.
- Luôn dựa vào dữ liệu và suy luận hợp lý.
- Tránh thêm thông tin không có trong dữ liệu.
Ví dụ trình bày đẹp:
Người dùng hỏi về BHXH:
+ Điều 10: Người lao động có quyền được tham gia BHXH.
+ Điều 12: Người sử dụng lao động có nghĩa vụ đóng BHXH cho người lao động.

"""
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            if not response or not getattr(response, "text", "").strip():
                return "Xin lỗi, tôi không tìm thấy thông tin trong dữ liệu."
            return response.text.strip()
        except Exception as e:
            return f"Lỗi khi gọi Gemini: {e}"

    async def run(self, dispatcher: CollectingDispatcher,
                  tracker: Tracker,
                  domain: dict):

        user_question = tracker.latest_message.get("text")
        print(f"Người dùng hỏi: {user_question}")

        if not ActionTraLoiCauHoi.documents:
            dispatcher.utter_message(text="Không thể load dữ liệu luật.")
            return []

        tokenized_q = self._normalize_text(user_question).split()
        scores = ActionTraLoiCauHoi.bm25.get_scores(tokenized_q)

        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:5]
        top_docs = [ActionTraLoiCauHoi.doc_map[i] for i in top_indices]

        answer = self._ask_gemini(user_question, top_docs)
        dispatcher.utter_message(text=answer)
        return []