# bao — PDF → JSON pipeline (ocr_sgk)

- **main.py**: workflow + CLI (gọi core).
- **core/**: config, env, pdf, schema, pipeline, models.
- **colab_setup.py**: chạy local, điền token ngrok → in ra URL API cho .env (Colab).

## Lệnh

```bash
python -m bao.main run path/to/file.pdf -o output/out.json --pipeline
python -m bao.main run path/to/file.pdf -o out.json
python -m bao.main load-models
python -m bao.main schema
```

## Cài đặt

```bash
pip install -r bao/requirements.txt
cp bao/.env.example .env
```

## Colab: lấy URL API cho .env

1. **Trên máy local** (có file .env ở thư mục gốc repo):
   - Mở `bao/colab_setup.py`, điền **NGROK_TOKEN** (token ngrok của bạn) vào biến `NGROK_TOKEN` ở đầu file (hoặc set env `NGROK_TOKEN`).
   - Chạy: `pip install pyngrok && python -m bao.colab_setup`
   - Script khởi động server trả nội dung `.env` tại `/env`, mở tunnel ngrok, rồi **in ra 2 dòng** dạng:
     - `COLAB_ENV_URL=https://xxxx.ngrok.io/env`
     - `NGROK_TOKEN=...`
2. **Trên Colab**: tạo hoặc sửa file `.env` (hoặc cell) và thêm 2 dòng trên. Sau đó chạy `python -m bao.main load-models` sẽ tải env từ URL đó.

## Cấu trúc

- **main.py** — entrypoint: load env, parse CLI, gọi core.
- **core/** — env, config, pdf, **images** (pdf2image, opencv/pillow), **layout** (PaddleOCR), **ocr_text**, **ocr_math** (pix2tex), **table**, **vision_figure**, schema, pipeline, models.
- **COLAB_STACK.md** — stack chọn cho Colab (apt + pip, model), xem để cài đúng.
- **requirements-colab.txt** — `pip install -r requirements-colab.txt` trên Colab.
- **colab_setup.py** — token ngrok → in URL cho .env.
- **requirements.txt**, **.env.example**, **README.md**.
