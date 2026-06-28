import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile

# Coba import cloudinary, jika tidak ada (meski harusnya ada di requirements) kita tangani
try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"

def setup_cloudinary():
    """Inisialisasi konfigurasi Cloudinary jika CLOUDINARY_URL ada di env"""
    url = os.environ.get("CLOUDINARY_URL")
    if url and CLOUDINARY_AVAILABLE:
        cloudinary.config() # Otomatis membaca CLOUDINARY_URL dari OS ENV
        return True
    return False

def upload_file(file: UploadFile, folder: str) -> str:
    """
    Menyimpan file ke Cloudinary (jika disetup) atau ke folder lokal.
    :param file: fastapi.UploadFile
    :param folder: Nama folder (contoh: 'ktp', 'collaterals')
    :return: String URL (bisa http://... atau relative uploads/...)
    """
    if setup_cloudinary():
        # Cloudinary support PDF tapi resource_type="auto" kadang menganggap raw
        # Sebaiknya kita baca filenya lalu upload
        contents = file.file.read()
        try:
            result = cloudinary.uploader.upload(
                contents,
                folder=f"koperasi/{folder}",
                resource_type="auto",
                filename_override=file.filename
            )
            file.file.seek(0)
            return result.get("secure_url")
        except Exception as e:
            print("Gagal upload Cloudinary, fallback ke lokal:", e)
            file.file.seek(0)
    
    # Fallback ke penyimpanan lokal
    local_dir = UPLOADS_DIR / folder
    local_dir.mkdir(parents=True, exist_ok=True)
    
    # Buat nama file unik
    ext = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = local_dir / unique_name
    
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return f"uploads/{folder}/{unique_name}"
