import os
import sys
import time
from dotenv import load_dotenv

# Muat environment variable dari file .env jika ada
load_dotenv()

from agents import HealthAgentsPipeline

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

def log_agent(step_num: int, name: str, icon: str, message: str, color: str = "cyan"):
    if HAS_RICH:
        console.print(Panel(f"[{color}][bold]{icon} {name}[/bold]: {message}[/{color}]", title=f"Tahap {step_num}/5"))
    else:
        print(f"\n[{step_num}/5] {icon} {name}: {message}")

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n[!] PERINGATAN: Variabel lingkungan GEMINI_API_KEY belum disetel.")
        print("Silakan masukkan Google Gemini API Key Anda:")
        api_key = input("API Key: ").strip()
        if not api_key:
            print("API Key wajib diisi untuk menjalankan agen. Keluar.")
            sys.exit(1)
        os.environ["GEMINI_API_KEY"] = api_key

    pipeline = HealthAgentsPipeline(api_key=api_key)

    if HAS_RICH:
        console.rule("[bold green]🏥 Health Content Multi-Agent Studio[/bold green]")
        console.print("[dim]Didukung oleh Google Gemini 2.5 & Google Search Grounding[/dim]\n")
    else:
        print("="*60)
        print("🏥 Health Content Multi-Agent Studio (Gemini)")
        print("="*60)

    # Input topik dari pengguna
    topic_input = input("Masukkan ide/isu kesehatan yang ingin dibuatkan konten (default: Gula tersembunyi minuman anak): ").strip()
    if not topic_input:
        topic_input = "Bahaya konsumsi gula tersembunyi pada minuman kemasan anak dan kaitannya dengan diabetes usia dini"

    print(f"\nMemulai rapat dan produksi konten untuk topik: '{topic_input}'...\n")

    # 1. Ideator
    log_agent(1, "Dr. Idea (Ideator)", "💡", "Merumuskan gagasan pokok, angle unik, dan target audiens...", "yellow")
    idea = pipeline.run_ideator(topic_input)
    if HAS_RICH:
        console.print(f"  • [bold]Topik:[/bold] {idea.topic}")
        console.print(f"  • [bold]Target:[/bold] {idea.target_audience}")
        console.print(f"  • [bold]Angle:[/bold] {idea.angle}\n")
    else:
        print(f"  Topik: {idea.topic}\n  Target: {idea.target_audience}\n  Angle: {idea.angle}\n")

    # 2. Researcher
    log_agent(2, "Nexus (Trend Researcher)", "🌐", "Mencari konteks nasional (Kemenkes/IDAI) & global (WHO)...", "cyan")
    research = pipeline.run_researcher(idea)
    if HAS_RICH:
        console.print(f"  • [bold]Nasional:[/bold] {research.national_context}")
        console.print(f"  • [bold]Global:[/bold] {research.global_context}")
        console.print(f"  • [bold]Sumber Terverifikasi:[/bold] {', '.join(research.primary_sources)}\n")
    else:
        print(f"  Nasional: {research.national_context}\n  Global: {research.global_context}\n  Sumber: {research.primary_sources}\n")

    # 3. Creative & Visual Creator
    log_agent(3, "Canvas (Copy & Visual Creator)", "🎨", "Merancang copywriting medsos dan prompt visual AI...", "magenta")
    draft = pipeline.run_creator(idea, research)
    if HAS_RICH:
        console.print(f"  • [bold]Hook Terpilih:[/bold] {draft.hook}")
        console.print(f"  • [bold]Jumlah Slide:[/bold] {len(draft.slides)} slide disusun\n")
    else:
        print(f"  Hook: {draft.hook}\n  Jumlah Slide: {len(draft.slides)}\n")

    # 4. Medical Fact-Checker
    log_agent(4, "Dr. Verif (Medical Fact-Checker)", "🩺", "Melakukan audit ilmiah & verifikasi anti-hoaks...", "red")
    audit = pipeline.run_fact_checker(draft, research)
    if HAS_RICH:
        status_color = "green" if audit.is_medically_accurate else "red"
        console.print(f"  • [bold]Status Medis:[/bold] [{status_color}]{'Lolos Uji Klinis' if audit.is_medically_accurate else 'Perlu Koreksi'}[/{status_color}]")
        console.print(f"  • [bold]Skor Akurasi Medis:[/bold] {audit.accuracy_score}/100")
        if audit.prohibited_claims_found:
            console.print(f"  • [bold red]Klaim Dicoret:[/bold red] {audit.prohibited_claims_found}")
        console.print(f"  • [bold]Sitasi Sah:[/bold] {', '.join(audit.approved_citations)}\n")
    else:
        print(f"  Status Medis: {audit.is_medically_accurate} (Skor: {audit.accuracy_score}/100)")
        print(f"  Sitasi: {audit.approved_citations}\n")

    # 5. Rapat Pleno (Editorial Council)
    log_agent(5, "Rapat Pleno Editorial", "🏛️", "Mengevaluasi keputusan akhir bersama semua agen...", "green")
    decision = pipeline.run_pleno_council(idea, research, draft, audit)

    # Tampilkan Keputusan Akhir
    if HAS_RICH:
        table = Table(title="Keputusan Rapat Pleno Editorial")
        table.add_column("Parameter", style="cyan", no_wrap=True)
        table.add_column("Nilai / Hasil", style="bold")

        table.add_row("Status Publikasi", f"[green]{decision.status}[/green]" if decision.status == "APPROVED" else f"[red]{decision.status}[/red]")
        table.add_row("Skor Akurasi Medis", f"{decision.medical_score} / 100")
        table.add_row("Skor Daya Tarik (Engagement)", f"{decision.engagement_score} / 100")
        table.add_row("Konsensus Dewan", decision.editorial_consensus_notes)
        console.print(table)
        console.print("\n")

        final = decision.final_content or draft
        console.rule("[bold cyan]📦 Paket Konten Siap Publikasi[/bold cyan]")
        console.print(Panel(f"[bold yellow]🎯 Hook Pembuka:[/bold yellow]\n{final.hook}"))

        for s in final.slides:
            console.print(Panel(
                f"[bold]Slide {s.slide_number}: {s.headline}[/bold]\n"
                f"{s.body_text}\n\n"
                f"[dim]🖼️ Visual Prompt (Midjourney/Flux):[/dim]\n[italic]{s.image_prompt}[/italic]",
                title=f"Slide {s.slide_number}"
            ))

        console.print(Panel(f"[bold]📝 Caption Lengkap:[/bold]\n{final.caption}\n\n[bold]📣 CTA:[/bold] {final.call_to_action}"))
        console.print(Panel(f"[bold cyan]📚 Rujukan Sumber Resmi:[/bold cyan]\n" + "\n".join([f"- {src}" for src in audit.approved_citations])))
    else:
        print("\n" + "="*60)
        print("KEPUTUSAN RAPAT PLENO:")
        print(f"Status: {decision.status}")
        print(f"Skor Medis: {decision.medical_score} | Skor Engagement: {decision.engagement_score}")
        print(f"Konsensus: {decision.editorial_consensus_notes}")
        print("="*60)

    # Simpan output ke file Markdown
    output_filename = "hasil_konten_terverifikasi.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        final = decision.final_content or draft
        f.write(f"# {idea.topic}\n\n")
        f.write(f"**Target Audiens:** {idea.target_audience}  \n")
        f.write(f"**Skor Medis:** {decision.medical_score}/100 | **Skor Virality:** {decision.engagement_score}/100  \n\n")
        f.write(f"## 🎯 Hook 3 Detik\n>{final.hook}\n\n")
        f.write("## 📱 Konten Carousel\n")
        for s in final.slides:
            f.write(f"### Slide {s.slide_number}: {s.headline}\n")
            f.write(f"{s.body_text}\n\n")
            f.write(f"*Prompt Visual AI:* `{s.image_prompt}`\n\n")
        f.write(f"## 📝 Caption & CTA\n{final.caption}\n\n**CTA:** {final.call_to_action}\n\n")
        f.write("## 📚 Sitasi Sumber Resmi\n")
        for src in audit.approved_citations:
            f.write(f"- {src}\n")

    print(f"\n[✓] Paket konten lengkap telah disimpan ke file: {output_filename}\n")

if __name__ == "__main__":
    main()
