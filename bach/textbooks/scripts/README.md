# Scripts – SGK Văn 9 tập 1 (Cánh diều)

Thư mục này chứa script/notebook liên quan đến bộ sách **SGK Văn 9 tập 1 - Cánh diều**. Cấu trúc nguồn (Mục lục, Các bài lớn, Các bài nhỏ) nằm ở thư mục cha của `scripts/`.

---

## Generate Chapters JSON (RAG) – notebook dùng chung

Notebook **`RAG/generate_chapters_json.ipynb`** (nằm trong repo, thư mục `RAG/`) sinh file JSON theo cấu trúc **chapter / lessons** từ **chính bộ sách này** (hoặc bất kỳ bộ sách nào có cùng cấu trúc thư mục).

### Input: cấu trúc thư mục sách (thư mục cha của `scripts/`)

| Thành phần | Đường dẫn | Vai trò |
|------------|-----------|--------|
| Mục lục | `Các bài lớn/Mục lục.md` | Thứ tự bài, tên từng đầu mục (lessons) |
| Bài lớn | `Các bài lớn/*.md` | Nội dung bài → dùng để sinh **description** (RAG) |
| Bài nhỏ | `Các bài nhỏ/<Tên bài>/*.md` | Nội dung từng đầu mục → dùng để sinh **summary** và trường **file** (RAG) |

### Output

- File JSON (mặc định: `RAG/output_chapters.json` khi chạy từ thư mục `RAG/`) là **mảng** các chapter.
- Mỗi phần tử có dạng:

```json
{
  "chapter": {
    "title": "Tên bài lớn",
    "description": "Mô tả do LLM sinh từ nội dung bài lớn (RAG)",
    "lessons": [
      {
        "lessonTitle": "Tên đầu mục",
        "type": "objectives | reading | writing | ...",
        "summary": "Tóm tắt do LLM sinh từ bài nhỏ (RAG)",
        "file": "Các bài nhỏ/Bài X/...md hoặc rỗng"
      }
    ]
  }
}
```

### Cách chạy notebook `RAG/generate_chapters_json.ipynb` cho bộ sách này

1. Mở notebook **`RAG/generate_chapters_json.ipynb`** (từ gốc repo: `RAG/generate_chapters_json.ipynb`).

2. Ở **ô 1. Cấu hình**:
   - **BASE_PATH**: trỏ tới thư mục gốc của SGK (thư mục chứa `Các bài lớn`, `Các bài nhỏ`).  
     Ví dụ cho bộ sách này:
     ```text
     <path-repo>/textbooks/Văn 9/SGK Văn 9 tập 1 - Cánh diều
     ```
   - **LLM** (chọn một trong hai):
     - **Trực tiếp Alibaba Intl:** `USE_9ROUTER = False`, điền `ALIBABA_API_KEY`.
     - **Qua 9Router:** `USE_9ROUTER = True`, chạy `npx 9router`, cấu hình provider Alibaba/Qwen trong Dashboard, điền `ROUTER_API_KEY` (hoặc biến môi trường `9ROUTER_API_KEY`).
   - **LLM_MODEL**: tên model (vd. `qwen-max` hoặc tên Combo trong 9Router).
   - **OUTPUT_PATH**: đường dẫn file JSON đầu ra (mặc định `./output_chapters.json` trong thư mục làm việc của notebook).

3. Chạy toàn bộ notebook (Run All). Kết quả ghi vào `OUTPUT_PATH`.

### Các bước trong notebook (tóm tắt)

| Bước | Nội dung |
|------|----------|
| 1 | Cấu hình (BASE_PATH, API key, 9Router, OUTPUT_PATH) |
| 2 | Import thư viện |
| 3 | Data classes (Chapter, Lesson, …) |
| 4 | RAG: parent/child chunks, DocumentChunker |
| 5 | Qwen LLM client (OpenAI-compatible, hỗ trợ base_url cho 9Router) |
| 6 | Lesson type classifier (objectives, reading, writing, …) |
| 7 | Parse Mục lục |
| 8 | File manager (đọc bài lớn / bài nhỏ) |
| 9 | ChapterJSONGenerator (sinh description & summary bằng LLM) |
| 10 | Chạy generation |
| 11 | Lưu JSON |
| 12 | Preview |
| 13 | (Tùy chọn) Export từng chapter ra file riêng |

### Giá trị `type` của lesson

Suy luận từ tên đầu mục: `reading`, `writing`, `speaking`, `language`, `knowledge`, `objectives`, `assessment`, `self_study`, `overview`.

### Yêu cầu

- Python 3.10+
- Thư viện: `openai` (client OpenAI-compatible để gọi Qwen / 9Router)
- API: Alibaba Intl (Qwen) hoặc 9Router đã cấu hình provider Alibaba/Qwen

---

## generate_chapter_json.ipynb (bản local trong thư mục scripts)

Notebook **`scripts/generate_chapter_json.ipynb`** là bản chạy **tại chỗ** (thư mục hiện tại = thư mục gốc SGK khi chạy). Cùng ý tưởng: sinh JSON chapter/lessons từ Mục lục + Các bài lớn + Các bài nhỏ, với description và summary do Qwen (RAG) sinh.

- Cấu hình: **ALIBABA_API_KEY**, **ROOT_DIR**, **output_file**, **filter_chapter** (vd. chỉ một bài).
- Chạy: mở notebook, đặt thư mục làm việc là thư mục gốc SGK (cha của `Các bài lớn`, `Các bài nhỏ`), rồi Run All.

Chi tiết cấu trúc JSON và giá trị `type` tương tự phần trên.
