import json
import os
import time
import logging
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from models import IdeaOutput, ResearchOutput, ContentDraft, FactCheckAudit, PlenoDecision

logger = logging.getLogger("health_agents")
logger.setLevel(logging.INFO)

class HealthAgentsPipeline:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        Inisialisasi pipeline agen edukasi kesehatan menggunakan Google Gemini API.
        Dilengkapi sistem Auto-Retry (Exponential Backoff) dan Cascading Model Fallback
        untuk mengatasi lonjakan trafik Google (503 UNAVAILABLE / 429).
        """
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY tidak ditemukan! Set env variable GEMINI_API_KEY atau masukkan saat inisialisasi."
            )
        self.client = genai.Client(api_key=api_key)
        
        # Model primer dan daftar model cadangan
        # Default diarahkan ke gemini-3.5-flash untuk kestabilan tinggi bebas antrean 503
        self.primary_model = model_name or os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
        
        # Urutan prioritas model aktif Gemini 3 / Gemini 2.5
        fallback_candidates = [
            self.primary_model,
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.8-flash",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.0-flash"
        ]
        # Hapus duplikat sambil mempertahankan urutan prioritas
        self.model_candidates = list(dict.fromkeys(fallback_candidates))
        self.active_model = self.primary_model

    def _generate_with_retry_and_fallback(
        self,
        contents: str,
        config: types.GenerateContentConfig,
        task_name: str = "Agent Task",
        max_retries_per_model: int = 2
    ) -> Any:
        """
        Menjalankan permintaan generate_content dengan perlindungan multi-lapis:
        - Jika 503 UNAVAILABLE / 429 (Spike trafik): Cepat coba ulang lalu beralih ke model berikutnya.
        - Jika model tidak didukung (404/403): Langsung beralih ke model aktif berikutnya.
        - Hanya melempar exception jika SEMUA model dalam daftar fallback gagal.
        """
        last_exception = None

        for model in self.model_candidates:
            for attempt in range(1, max_retries_per_model + 1):
                try:
                    logger.info(f"[{task_name}] Menjalankan model '{model}' (Percobaan {attempt}/{max_retries_per_model})...")
                    response = self.client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=config
                    )
                    self.active_model = model
                    return response
                except Exception as e:
                    err_str = str(e)
                    last_exception = e
                    logger.warning(f"[{task_name}] Kendala pada model '{model}': {err_str}")

                    # Kasus 1: 503 UNAVAILABLE atau 429 (Trafik tinggi sementara pada model ini)
                    if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str or "429" in err_str:
                        if attempt < max_retries_per_model:
                            wait_time = 1.5 * attempt
                            logger.info(f"[{task_name}] Model '{model}' mengalami lonjakan trafik (503). Menunggu {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            # Segera beralih ke model cadangan berikutnya yang tidak overload
                            logger.info(f"[{task_name}] Beralih dari '{model}' ke model cadangan berikutnya...")
                            break
                    else:
                        # Error lain (misal 404/403/kebijakan), langsung coba model cadangan berikutnya
                        logger.info(f"[{task_name}] Model '{model}' dilewati ({err_str[:40]}...). Mencoba model cadangan...")
                        break

        # Jika seluruh model dalam daftar fallback gagal
        raise last_exception

    def run_ideator(self, raw_input: str) -> IdeaOutput:
        """Agen 1: Merumuskan gagasan pokok, angle unik, dan target audiens."""
        prompt = f"""
        Anda adalah Dr. Idea, seorang Konseptor Konten Edukasi Kesehatan Media Sosial berpengalaman.
        Tugas Anda adalah merumuskan ide konten yang segar, relevan, dan memecah mitos yang beredar di masyarakat.
        
        Permintaan Pengguna: "{raw_input}"
        
        Kembalikan output dalam format JSON sesuai skema berikut:
        - topic: Topik utama edukasi
        - target_audience: Target audiens yang tepat
        - angle: Sudut pandang unik (contoh: mitos vs fakta, kebiasaan sehari-hari yang salah)
        - core_premise: Gagasan utama yang ingin disampaikan agar audiens tercerahkan
        """
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=IdeaOutput,
            temperature=0.7
        )
        response = self._generate_with_retry_and_fallback(
            contents=prompt,
            config=config,
            task_name="Agen 1: Ideator"
        )
        return IdeaOutput.model_validate_json(response.text)

    def run_researcher(self, idea: IdeaOutput) -> ResearchOutput:
        """Agen 2: Mengumpulkan data terkini, rilis Kemenkes, situasi nasional dan global (WHO)."""
        prompt = f"""
        Anda adalah Nexus, seorang Peneliti Medis dan Trend Analyst Kesehatan Global & Nasional Indonesia.
        
        Ide Konten:
        - Topik: {idea.topic}
        - Angle: {idea.angle}
        - Premis: {idea.core_premise}
        
        Tugas Anda:
        1. Cari keterkaitan ide ini dengan situasi kesehatan nasional terkini di Indonesia (Kemenkes RI, Riskesdas, BPOM, IDAI/PAPDI).
        2. Cari data/standar internasional dari WHO atau CDC.
        3. Berikan data statistik angka konkret yang valid dan sebutkan nama lembaga rujukan resmi. Dilarang mengarang angka!
        """
        # Coba jalankan dengan Google Search Grounding terlebih dahulu
        try:
            config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json",
                response_schema=ResearchOutput,
                temperature=0.2
            )
            response = self._generate_with_retry_and_fallback(
                contents=prompt,
                config=config,
                task_name="Agen 2: Researcher (Google Grounded)"
            )
            return ResearchOutput.model_validate_json(response.text)
        except Exception as e:
            # Jika Search Tool mengalami kendala kuota, fallback ke knowledge base medis model
            logger.warning(f"[Agen 2: Researcher] Grounding search gagal ({e}), menggunakan knowledge medis internal.")
            fallback_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResearchOutput,
                temperature=0.2
            )
            response = self._generate_with_retry_and_fallback(
                contents=prompt + "\n\nGunakan referensi literatur medis standar Kemenkes RI dan WHO.",
                config=fallback_config,
                task_name="Agen 2: Researcher (Internal Medical Knowledge)"
            )
            return ResearchOutput.model_validate_json(response.text)

    def run_creator(self, idea: IdeaOutput, research: ResearchOutput) -> ContentDraft:
        """Agen 3: Meracik copywriting medsos (hook, slide carousel) & prompt visual AI (Midjourney/Flux)."""
        prompt = f"""
        Anda adalah Canvas, seorang Creative Director Medsos & Visual Prompt Engineer.
        
        Gagasan:
        - Topik: {idea.topic}
        - Target Audiens: {idea.target_audience}
        - Angle: {idea.angle}
        
        Data & Riset:
        - Situasi Nasional: {research.national_context}
        - Situasi Global: {research.global_context}
        - Statistik Resmi: {research.verified_statistics}
        - Sumber: {research.primary_sources}
        
        Tugas Anda:
        1. Buat Hook 3 detik pertama yang sangat memikat tanpa nada murahan.
        2. Rancang 3-5 slide carousel informatif.
        3. Buat prompt visual AI spesifik (estetika medis 3D/ilustrasi profesional) untuk setiap slide.
        4. Tulis caption ramah pembaca dan Call-to-Action (CTA).
        """
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ContentDraft,
            temperature=0.6
        )
        response = self._generate_with_retry_and_fallback(
            contents=prompt,
            config=config,
            task_name="Agen 3: Creator"
        )
        return ContentDraft.model_validate_json(response.text)

    def run_fact_checker(self, draft: ContentDraft, research: ResearchOutput) -> FactCheckAudit:
        """Agen 4: Melakukan verifikasi medis ketat, memastikan sitasi terpercaya, dan melarang klaim palsu."""
        draft_json = draft.model_dump_json(indent=2)
        research_json = research.model_dump_json(indent=2)
        
        prompt = f"""
        Anda adalah Dr. Verif, Dokter Spesialis sekaligus Editor Medis Kepala (Fact-Checker).
        Prinsip utama Anda: "Primum non nocere" (Yang terpenting, jangan merugikan pasien/masyarakat).
        
        Periksa draf konten berikut secara kritis:
        {draft_json}
        
        Rujukan Data Riset:
        {research_json}
        
        Aturan Audit:
        1. Apakah ada klaim absolut atau menakut-nakuti (fear-mongering) yang tidak berdasar?
        2. Apakah semua angka statistik sesuai dengan rujukan Kemenkes/WHO?
        3. Jika ada informasi yang keliru secara medis, sebutkan di revision_feedback dan beri prohibited_claims_found.
        4. Berikan nilai akurasi medis (1-100).
        """
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FactCheckAudit,
            temperature=0.1
        )
        response = self._generate_with_retry_and_fallback(
            contents=prompt,
            config=config,
            task_name="Agen 4: Fact-Checker"
        )
        return FactCheckAudit.model_validate_json(response.text)

    def run_pleno_council(
        self,
        idea: IdeaOutput,
        research: ResearchOutput,
        draft: ContentDraft,
        audit: FactCheckAudit
    ) -> PlenoDecision:
        """Agen 5: Rapat Pleno untuk memutuskan kelayakan konten, memperbaiki catatan medis, dan menerbitkan paket final."""
        prompt = f"""
        Ini adalah sesi Rapat Pleno Editorial Dewan Edukasi Kesehatan.
        Dihadiri oleh:
        1. Ideator ({idea.topic})
        2. Researcher (Data Kemenkes/WHO: {research.primary_sources})
        3. Creative Director (Draf Naskah & Visual)
        4. Editor Medis / Fact-Checker (Status Akurat: {audit.is_medically_accurate}, Skor Medis: {audit.accuracy_score})
        
        Catatan dari Editor Medis:
        {audit.revision_feedback or 'Tidak ada keberatan medis, konten akurat.'}
        
        Draf Awal:
        {draft.model_dump_json(indent=2)}
        
        Tugas Rapat Pleno:
        1. Evaluasi apakah naskah sudah siap tayang atau perlu perbaikan kalimat berdasarkan catatan editor medis.
        2. Berikan skor keterlibatan (Engagement Score) dan skor medis final.
        3. Tuliskan ringkasan konsensus editorial.
        4. Terbitkan naskah final yang telah disempurnakan (perbaiki teks jika ada teguran dari dokter).
        """
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PlenoDecision,
            temperature=0.4
        )
        response = self._generate_with_retry_and_fallback(
            contents=prompt,
            config=config,
            task_name="Agen 5: Pleno Council"
        )
        return PlenoDecision.model_validate_json(response.text)
