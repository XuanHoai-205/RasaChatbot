import pandas as pd
import math
import re
from actions.actions import ActionTraLoiCauHoi


# Chuẩn hóa text (giống actions.py)
def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower().strip()

# Tính MRR
def mean_reciprocal_rank(all_ranks):
    return sum([1.0/r if r > 0 else 0 for r in all_ranks]) / len(all_ranks)

# Tính nDCG
def ndcg_at_k(ranked_list, ground_truth, k=10):
    dcg = 0.0
    for i, doc in enumerate(ranked_list[:k], start=1):
        if ground_truth in doc:
            dcg += 1 / math.log2(i + 1)
    idcg = 1.0  # chỉ có 1 ground truth
    return dcg / idcg if idcg > 0 else 0


if __name__ == "__main__":
    # Load file test
    df = pd.read_excel("Bộ dữ liệu hỏi đáp dùng làm test.xlsx", sheet_name="QDND")

    # Load BM25 từ actions
    if ActionTraLoiCauHoi.documents is None:
        action = ActionTraLoiCauHoi()
        action._fetch_all_laws()

    bm25 = ActionTraLoiCauHoi.bm25
    documents = ActionTraLoiCauHoi.documents

    mrr_scores, ndcg_scores = [], []

    for idx, row in df.iterrows():
        query = normalize_text(str(row["Câu hỏi"]))
        ground_truth = normalize_text(str(row["Câu trả lời"]))
        tokenized_query = query.split(" ")

        # Tính điểm BM25
        scores = bm25.get_scores(tokenized_query)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        ranked_docs = [documents[i] for i in ranked_indices]

        # --- Đánh giá ---
        rank_position = 0
        for i, doc in enumerate(ranked_docs, start=1):
            if ground_truth in doc:
                rank_position = i
                break
        mrr_scores.append(rank_position)

        ndcg_score = ndcg_at_k(ranked_docs, ground_truth, k=10)
        ndcg_scores.append(ndcg_score)

        # In thử từng case (MRR + nDCG trước khi gọi Gemini)
        print(f"\nQuery {idx+1}: {query}")
        print(f"Ground truth: {ground_truth}")
        print(f"MRR (reciprocal rank): {1/rank_position if rank_position > 0 else 0:.4f}")
        print(f"nDCG@10: {ndcg_score:.4f}")

        # --- Sau đó gọi Gemini ---
        top_docs = ranked_docs[:5]
        # action = ActionTraLoiCauHoi()
        # answer = action._ask_gemini(query, top_docs)
        # print("Gemini trả lời:", answer)

    # Kết quả tổng hợp
    mrr = mean_reciprocal_rank(mrr_scores)
    avg_ndcg = sum(ndcg_scores) / len(ndcg_scores)

    print("\n=== KẾT QUẢ TRUNG BÌNH ===")
    print(f"MRR: {mrr:.4f}")
    print(f"nDCG@10: {avg_ndcg:.4f}")