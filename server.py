import os
import sys
import json
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Muat environment variable
load_dotenv()

from agents import HealthAgentsPipeline

app = FastAPI(title="Health Content Multi-Agent Studio")

# Pastikan folder static ada
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

# Melayani file HTML utama di root (/)
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>File index.html tidak ditemukan di folder static</h1>"

@app.post("/api/generate-imagen")
async def generate_imagen(payload: dict):
    """
    Generate visual resolusi tinggi menggunakan model Google Imagen 3 (imagen-3.0-generate-002)
    melalui Google GenAI SDK resmi.
    """
    prompt = payload.get("prompt", "")
    if not prompt:
        return {"success": False, "error": "Prompt tidak boleh kosong"}
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY belum disetel di server.",
            "hint": "Gunakan Google Flow di flow.google dengan akun Google Anda."
        }
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        full_prompt = (
            f"Cinematic medical 3D photorealism, scientific accuracy, clean clinical studio lighting, "
            f"subsurface scattering, 8k resolution, crisp detail, no text artifacts, 1:1 square: {prompt}"
        )
        loop = asyncio.get_event_loop()
        
        def _call_imagen():
            return client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=full_prompt,
                config=dict(number_of_images=1, aspect_ratio="1:1")
            )
        
        result = await loop.run_in_executor(None, _call_imagen)
        if result and result.generated_images and len(result.generated_images) > 0:
            import base64
            img_bytes = result.generated_images[0].image.image_bytes
            b64_str = base64.b64encode(img_bytes).decode("utf-8")
            return {
                "success": True,
                "image_data": f"data:image/jpeg;base64,{b64_str}",
                "model": "Google Imagen 3 (imagen-3.0-generate-002)"
            }
        else:
            return {
                "success": False,
                "error": "Google Imagen 3 tidak mengembalikan gambar.",
                "hint": "Gunakan Google Flow di flow.google untuk generate langsung."
            }
    except Exception as e:
        err_msg = str(e)
        return {
            "success": False,
            "error": err_msg,
            "hint": "Jika API key belum memiliki izin/kuota Imagen 3 di Google AI Studio, gunakan tombol 'Buka Google Flow' (flow.google) untuk generate visual sinematik gratis langsung di Google Labs!"
        }

@app.get("/api/stream-pipeline")
async def stream_pipeline(topic: str = Query(..., description="Topik konten kesehatan")):
    """
    Endpoint SSE (Server-Sent Events) untuk menjalankan 5 agen secara bergantian
    dan mengirimkan update visual secara real-time ke antarmuka web.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        async def err_gen():
            err_payload = {
                "type": "error",
                "message": "GEMINI_API_KEY belum disetel! Tambahkan di file .env atau export di terminal."
            }
            yield f"data: {json.dumps(err_payload)}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            pipeline = HealthAgentsPipeline(api_key=api_key)
            loop = asyncio.get_event_loop()

            # --- TAHAP 1: IDEATOR ---
            start_payload = {
                "type": "agent_start",
                "agent_id": 1,
                "agent_name": "Dr. Idea (Ideator)",
                "icon": "💡",
                "status_badge": "Merumuskan Gagasan",
                "thought": "Mencari sudut pandang unik yang memecah mitos...",
                "log": f"Menganalisis topik: '{topic}'"
            }
            yield f"data: {json.dumps(start_payload)}\n\n"
            await asyncio.sleep(0.5)

            idea = await loop.run_in_executor(None, pipeline.run_ideator, topic)

            done_payload = {
                "type": "agent_complete",
                "agent_id": 1,
                "agent_name": "Dr. Idea",
                "thought": f"Angle: {idea.angle}",
                "summary": f"Gagasan selesai: '{idea.topic}' untuk target {idea.target_audience}"
            }
            yield f"data: {json.dumps(done_payload)}\n\n"
            await asyncio.sleep(0.6)

            # --- TAHAP 2: RESEARCHER ---
            start_payload = {
                "type": "agent_start",
                "agent_id": 2,
                "agent_name": "Nexus (Researcher)",
                "icon": "🌐",
                "status_badge": "Google Search Grounding",
                "thought": "Mengumpulkan rilis pers Kemenkes & rekomendasi WHO...",
                "log": "Menyelidiki statistik epidemiologi & rujukan resmi nasional/global"
            }
            yield f"data: {json.dumps(start_payload)}\n\n"
            await asyncio.sleep(0.5)

            research = await loop.run_in_executor(None, pipeline.run_researcher, idea)

            done_payload = {
                "type": "agent_complete",
                "agent_id": 2,
                "agent_name": "Nexus",
                "thought": f"Sumber: {len(research.primary_sources)} rujukan terverifikasi",
                "summary": f"Data Kemenkes & WHO terhimpun ({len(research.primary_sources)} sumber valid)"
            }
            yield f"data: {json.dumps(done_payload)}\n\n"
            await asyncio.sleep(0.6)

            # --- TAHAP 3: CREATIVE & VISUAL ---
            start_payload = {
                "type": "agent_start",
                "agent_id": 3,
                "agent_name": "Canvas (Creator)",
                "icon": "🎨",
                "status_badge": "Menyusun Naskah & Visual",
                "thought": "Menulis hook 3 detik & prompt Midjourney...",
                "log": "Merancang hook carousel dan estetika render visual 3D"
            }
            yield f"data: {json.dumps(start_payload)}\n\n"
            await asyncio.sleep(0.5)

            draft = await loop.run_in_executor(None, pipeline.run_creator, idea, research)

            done_payload = {
                "type": "agent_complete",
                "agent_id": 3,
                "agent_name": "Canvas",
                "thought": f"Naskah {len(draft.slides)} slide selesai",
                "summary": f"Naskah carousel ({len(draft.slides)} slide) dan prompt AI selesai diracik"
            }
            yield f"data: {json.dumps(done_payload)}\n\n"
            await asyncio.sleep(0.6)

            # --- TAHAP 4: FACT CHECKER ---
            start_payload = {
                "type": "agent_start",
                "agent_id": 4,
                "agent_name": "Dr. Verif (Fact-Checker)",
                "icon": "🩺",
                "status_badge": "Audit Medis Kritis",
                "thought": "Memeriksa kebenaran ilmiah dan potensi overclaim...",
                "log": "Menguji klaim terhadap pedoman klinis Kemenkes/IDAI dan menyaring hoaks"
            }
            yield f"data: {json.dumps(start_payload)}\n\n"
            await asyncio.sleep(0.5)

            audit = await loop.run_in_executor(None, pipeline.run_fact_checker, draft, research)

            done_payload = {
                "type": "agent_complete",
                "agent_id": 4,
                "agent_name": "Dr. Verif",
                "thought": f"Skor Medis: {audit.accuracy_score}/100",
                "summary": f"Audit klinis tuntas: Skor {audit.accuracy_score}/100. Klaim divalidasi sah."
            }
            yield f"data: {json.dumps(done_payload)}\n\n"
            await asyncio.sleep(0.6)

            # --- TAHAP 5: RAPAT PLENO ---
            start_payload = {
                "type": "agent_start",
                "agent_id": 5,
                "agent_name": "Rapat Pleno (Dewan Redaksi)",
                "icon": "🏛️",
                "status_badge": "Sidang Konsensus",
                "thought": "Menggabungkan masukan dokter dan mengesahkan versi final...",
                "log": "Semua agen berkumpul untuk skoring akhir dan validasi paket konten"
            }
            yield f"data: {json.dumps(start_payload)}\n\n"
            await asyncio.sleep(0.5)

            pleno = await loop.run_in_executor(None, pipeline.run_pleno_council, idea, research, draft, audit)

            done_payload = {
                "type": "agent_complete",
                "agent_id": 5,
                "agent_name": "Rapat Pleno",
                "thought": f"Status: {pleno.status}",
                "summary": f"Sidang Pleno selesai. Status: {pleno.status} (Konsensus Disetujui)"
            }
            yield f"data: {json.dumps(done_payload)}\n\n"
            await asyncio.sleep(0.6)

            # --- HASIL AKHIR ---
            final_payload = {
                "type": "pipeline_finished",
                "data": {
                    "idea": idea.model_dump(),
                    "research": research.model_dump(),
                    "draft": draft.model_dump(),
                    "audit": audit.model_dump(),
                    "pleno": pleno.model_dump()
                }
            }
            yield f"data: {json.dumps(final_payload)}\n\n"

        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                user_msg = "Server Google Gemini sedang mengalami lonjakan trafik global (503 High Demand). Sistem telah mencoba melakukan retry otomatis. Silakan tunggu sekitar 15-30 detik lalu klik tombol 'Jalankan Pipeline' lagi."
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                user_msg = "Batas kuota Gemini API tercapai sementara (429 Rate Limit). Silakan jeda beberapa saat lalu coba kembali."
            elif "API_KEY_INVALID" in err_str:
                user_msg = "GEMINI_API_KEY tidak valid atau belum disetel di Render Environment Variables."
            else:
                user_msg = f"Kendala Pipeline: {err_str}"

            err_payload = {"type": "error", "message": user_msg}
            yield f"data: {json.dumps(err_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"\n=======================================================")
    print(f"🚀 Health Content Multi-Agent Studio Aktif!")
    print(f"👉 Buka di browser Anda: http://localhost:{port}")
    print(f"=======================================================\n")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
