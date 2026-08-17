import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {'application/pdf', 'image/jpeg', 'image/png', 'image/webp'}
CONTENT_SIGNATURES = {
    'application/pdf': (b'%PDF-',),
    'image/jpeg': (b'\xff\xd8\xff',),
    'image/png': (b'\x89PNG\r\n\x1a\n',),
    'image/webp': (b'RIFF',),
}
SAFE_SUFFIXES = {
    'application/pdf': '.pdf',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
}


def upload_dir() -> Path:
    return get_settings().upload_dir


def max_storage_bytes() -> int:
    return get_settings().max_upload_storage_mb * 1024 * 1024


def validate_file_content(content: bytes, content_type: str) -> str:
    signatures = CONTENT_SIGNATURES.get(content_type)
    if not signatures or not any(content.startswith(signature) for signature in signatures):
        raise HTTPException(status_code=415, detail='El contenido del archivo no coincide con su formato declarado')
    if content_type == 'image/webp' and (len(content) < 12 or content[8:12] != b'WEBP'):
        raise HTTPException(status_code=415, detail='El archivo WEBP no es válido')
    return SAFE_SUFFIXES[content_type]


def ensure_storage_capacity(additional_bytes: int) -> None:
    directory = upload_dir()
    directory.mkdir(parents=True, exist_ok=True)
    used_bytes = sum(path.stat().st_size for path in directory.iterdir() if path.is_file())
    if used_bytes + additional_bytes > max_storage_bytes():
        raise HTTPException(
            status_code=507,
            detail=f'El almacenamiento de documentos alcanzó su límite de {get_settings().max_upload_storage_mb} MB',
        )


def read_upload(upload: UploadFile, *, label: str = 'archivo') -> tuple[bytes, str, str, str]:
    content_type = upload.content_type or ''
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail=f'El {label} debe ser PDF, JPG, PNG o WEBP')
    content = upload.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f'El {label} debe pesar máximo 10 MB')
    suffix = validate_file_content(content, content_type)
    original_name = Path(upload.filename or label).name[:255]
    stored_name = f'{secrets.token_hex(20)}{suffix}'
    return content, content_type, original_name, stored_name


def write_document(stored_name: str, content: bytes) -> Path:
    ensure_storage_capacity(len(content))
    directory = upload_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / stored_name
    path.write_bytes(content)
    return path


def document_path(stored_name: str) -> Path:
    return upload_dir() / stored_name
