import json
import os
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from models import IdeaOutput, ResearchOutput, ContentDraft, FactCheckAudit, PlenoDecision

class HealthAgentsPipeline:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        """
        Inisialisasi pipeline agen edukasi kesehatan menggunakan Google Gemini API.
        """
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY tidak ditemukan! Set env variable GEMINI_API_KEY atau masukkan saat inisialisasi."
            )
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

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
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=IdeaOutput,
                temperature=0.7
            )
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
        # Aktifkan Google Search Grounding untuk riset fakta terkini
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json",
                response_schema=ResearchOutput,
                temperature=0.2
            )
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
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ContentDraft,
                temperature=0.6
            )
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
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FactCheckAudit,
                temperature=0.1
            )
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
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PlenoDecision,
                temperature=0.4
            )
        )
        return PlenoDecision.model_validate_json(response.text)
