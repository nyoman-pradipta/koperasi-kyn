"""
Skrip menjalankan server produksi (satu perintah).

Pemakaian:
    python run.py

Server akan berjalan di http://127.0.0.1:8000 dan menyajikan frontend yang
sudah di-build sekaligus API-nya. Cocok untuk dipindahkan ke komputer lain:
cukup copy folder, install dependency, lalu `python run.py`.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8003,
        reload=False,
    )
