from typing import List, Optional
from pydantic import BaseModel, Field

class IdeaOutput(BaseModel):
    topic: str = Field(description="Topik utama edukasi kesehatan")
    target_audience: str = Field(description="Target audiens media sosial (misal: orang tua muda, gen-z)")
    angle: str = Field(description="Sudut pandang/angle unik yang menarik perhatian")
    core_premise: str = Field(description="Gagasan pokok atau kesalahpahaman yang ingin diluruskan")

class ResearchOutput(BaseModel):
    national_context: str = Field(description="Situasi kesehatan terkini di Indonesia (Kemenkes, BPOM, dsb)")
    global_context: str = Field(description="Rekomendasi atau peringatan global (WHO, CDC, dsb)")
    verified_statistics: List[str] = Field(description="Statistik angka valid dari sumber resmi")
    primary_sources: List[str] = Field(description="Nama lembaga/jurnal rujukan (misal: Kemenkes RI, WHO, IDAI)")

class VisualSlide(BaseModel):
    slide_number: int
    headline: str
    body_text: str
    image_prompt: str = Field(description="Prompt visual untuk AI image generator (Midjourney/Flux/DALL-E)")

class ContentDraft(BaseModel):
    hook: str = Field(description="Hook 3 detik pertama / headline pembuka yang menghentikan scroll")
    slides: List[VisualSlide] = Field(description="Rangkaian 3-5 slide konten carousel / storyboard video")
    caption: str = Field(description="Caption lengkap media sosial beserta hashtag relevan")
    call_to_action: str = Field(description="Ajakan bertindak positif untuk audiens")

class FactCheckAudit(BaseModel):
    is_medically_accurate: bool = Field(description="Apakah konten secara medis benar dan tidak menyesatkan")
    accuracy_score: int = Field(description="Skor akurasi medis dari skala 1-100")
    prohibited_claims_found: List[str] = Field(default_factory=list, description="Klaim overclaim, sensasional, atau tanpa rujukan yang ditemukan")
    approved_citations: List[str] = Field(description="Daftar sitasi resmi yang telah diverifikasi")
    revision_feedback: Optional[str] = Field(default=None, description="Catatan perbaikan jika ada poin yang salah secara medis")

class PlenoDecision(BaseModel):
    status: str = Field(description="'APPROVED' jika disetujui, 'REVISION_NEEDED' jika perlu revisi")
    medical_score: int = Field(description="Skor akurasi medis (1-100)")
    engagement_score: int = Field(description="Skor daya tarik & kejelasan bahasa (1-100)")
    editorial_consensus_notes: str = Field(description="Catatan kesepakatan rapat pleno antar agen")
    final_content: Optional[ContentDraft] = Field(default=None, description="Versi naskah final yang siap tayang")
