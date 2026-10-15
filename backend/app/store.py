import os
import secrets
import time
from dataclasses import dataclass, field
from threading import RLock

TTL = int(os.getenv('SESSION_TTL_SECONDS','3600'))
MAX_BYTES = int(os.getenv('MAX_SESSION_BYTES','150000000'))
LOCK = RLock()

@dataclass
class Session:
    name: str
    original: bytes
    history: list[bytes]
    cursor: int = 0
    revision: int = 0
    touched: float = field(default_factory=time.time)
    pending: tuple | None = None
    fonts: dict[str,bytes] = field(default_factory=dict)
    @property
    def current(self): return self.history[self.cursor]
    def commit(self, data):
        proposed = self.history[:self.cursor+1] + [data]
        while len(proposed)>20 or sum(map(len,proposed))+len(self.original)+len(data)>MAX_BYTES:
            if len(proposed)<=1: raise ValueError('เอกสารใหญ่เกินหน่วยความจำที่กำหนด')
            proposed.pop(0)
        self.history=proposed; self.cursor=len(proposed)-1; self.revision+=1; self.pending=None

sessions: dict[str,Session] = {}

def cleanup():
    with LOCK:
        for key in list(sessions):
            if time.time()-sessions[key].touched>TTL: del sessions[key]

def create(name,data):
    cleanup()
    if len(sessions)>=8: raise ValueError('เซิร์ฟเวอร์มีเอกสารครบ 8 เซสชัน กรุณาลองใหม่ภายหลัง')
    token=secrets.token_urlsafe(32)
    sessions[token]=Session(name,data,[data])
    return token
