#!/usr/bin/env python3
# =============================================================================
# concall_analyzer.py — Automated Earnings Call Transcript Evaluator
# =============================================================================
# This module connects to BSE, finds the latest concall transcript PDF, 
# downloads it, extracts the text, and analyzes it for moat/red-flag density.
# =============================================================================

import os
import re
import io
import time
import argparse
import requests
from pypdf import PdfReader
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from qualitative_checker import BSEFilingScanner, BSE_HEADERS
from keyword_signals import MOAT_KEYWORDS, RED_FLAG_KEYWORDS, MOAT_CATEGORY_LABELS

console = Console()

class ConcallAnalyzer:
    def __init__(self):
        self.bse = BSEFilingScanner()
        self.session = requests.Session()
        self.session.headers.update(BSE_HEADERS)
        self.pdf_base_url = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"

    def fetch_latest_transcript_pdf(self, ticker: str):
        """Find and download the latest transcript PDF for a ticker."""
        return self.fetch_latest_document_pdf(ticker, "transcript")

    def fetch_latest_document_pdf(self, ticker: str, doc_type: str = "transcript"):
        """Find and download the latest PDF for a specific document type."""
        scripcode = self.bse.get_scripcode(ticker)
        if not scripcode:
            console.print(f"[red]Could not find BSE scripcode for {ticker}[/red]")
            return None, None

        # Annual reports might only happen once a year, fetch 18 months to be safe
        months = 18 if doc_type == "annual_report" else 12
        announcements = self.bse.fetch_announcements(scripcode, months=months)
        
        target_ann = None
        # Convert internal type to BSE search string (e.g. "annual_report" -> "annual report")
        search_term = doc_type.replace("_", " ")
        
        for ann in announcements:
            subject = str(ann.get("HEADLINE", "")) + " " + str(ann.get("NEWSSUB", ""))
            if search_term in subject.lower() and ann.get("ATTACHMENTNAME"):
                target_ann = ann
                break
                
        if not target_ann:
            return None, None

        attachment = target_ann.get("ATTACHMENTNAME")
        pdf_url = f"{self.pdf_base_url}{attachment}"
        
        # Download PDF
        try:
            resp = self.session.get(pdf_url, timeout=15)
            if resp.status_code == 200:
                return resp.content, target_ann
        except Exception as e:
            console.print(f"[red]Error downloading PDF: {e}[/red]")
            
        return None, None

    def extract_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = []
            for page in reader.pages:
                text.append(page.extract_text() or "")
            return " ".join(text)
        except Exception as e:
            console.print(f"[red]Error parsing PDF: {e}[/red]")
            return ""

    def analyze_transcript(self, text: str) -> dict:
        """Count frequencies of moat and red-flag keywords."""
        text_lower = text.lower()
        word_count = len(text_lower.split())
        
        results = {
            "word_count": word_count,
            "positive_hits": {},
            "negative_hits": {},
            "total_positive_score": 0,
            "total_negative_score": 0,
            "signal_density": 0.0
        }

        if word_count == 0:
            return results

        # Score positive signals
        for cat, meta in MOAT_KEYWORDS.items():
            count = 0
            found_phrases = set()
            for phrase in meta["phrases"]:
                # Count non-overlapping occurrences
                occurrences = len(re.findall(r'\b' + re.escape(phrase) + r'\b', text_lower))
                if occurrences > 0:
                    count += occurrences
                    found_phrases.add(phrase)
            
            if count > 0:
                score = count * meta["weight"]
                results["total_positive_score"] += score
                results["positive_hits"][cat] = {
                    "count": count,
                    "score": score,
                    "phrases": list(found_phrases),
                    "label": MOAT_CATEGORY_LABELS.get(cat, cat)
                }

        # Score negative signals
        for cat, meta in RED_FLAG_KEYWORDS.items():
            count = 0
            found_phrases = set()
            for phrase in meta["phrases"]:
                occurrences = len(re.findall(r'\b' + re.escape(phrase) + r'\b', text_lower))
                if occurrences > 0:
                    count += occurrences
                    found_phrases.add(phrase)
                    
            if count > 0:
                score = count * meta["weight"]
                results["total_negative_score"] += score
                results["negative_hits"][cat] = {
                    "count": count,
                    "score": score,
                    "phrases": list(found_phrases)
                }

        # Calculate density (Net Score per 1,000 words)
        net_score = results["total_positive_score"] - results["total_negative_score"]
        results["signal_density"] = round((net_score / word_count) * 1000, 2)
        
        return results

def print_analysis(ticker: str, ann: dict, results: dict):
    """Pretty print the transcript analysis."""
    date = ann.get("NEWS_DT", "").split("T")[0]
    
    console.print(Panel.fit(
        f"[bold cyan]🎙️ Concall Transcript Analysis: {ticker}[/bold cyan]\n"
        f"[dim]Date: {date} | Length: {results['word_count']:,} words[/dim]",
        border_style="cyan"
    ))

    density = results["signal_density"]
    color = "green" if density > 5 else "yellow" if density > 0 else "red"
    
    console.print(f"\n[bold]Net Signal Density:[/bold] [bold {color}]{density}[/bold {color}] points per 1,000 words")
    if density > 10:
        console.print("[green]🔥 Extremely high conviction language detected.[/green]")
    elif density > 5:
        console.print("[green]✅ Positive moat language detected.[/green]")
    elif density < 0:
        console.print("[red]⚠️ Red flags outweigh positive moat signals in this call.[/red]")

    # Positive Table
    if results["positive_hits"]:
        table_pos = Table(title="[bold green]🟢 Positive Moat Signals[/bold green]", box=box.SIMPLE, show_lines=True)
        table_pos.add_column("Category", style="cyan")
        table_pos.add_column("Mentions", justify="right")
        table_pos.add_column("Score", justify="right")
        table_pos.add_column("Phrases Used", style="dim")
        
        for cat, data in sorted(results["positive_hits"].items(), key=lambda x: x[1]['score'], reverse=True):
            table_pos.add_row(
                data["label"], 
                str(data["count"]), 
                str(data["score"]), 
                ", ".join(data["phrases"])
            )
        console.print(table_pos)

    # Negative Table
    if results["negative_hits"]:
        table_neg = Table(title="[bold red]🔴 Red Flags & Risks[/bold red]", box=box.SIMPLE, show_lines=True)
        table_neg.add_column("Category", style="magenta")
        table_neg.add_column("Mentions", justify="right")
        table_neg.add_column("Score", justify="right")
        table_neg.add_column("Phrases Used", style="dim")
        
        for cat, data in sorted(results["negative_hits"].items(), key=lambda x: x[1]['score'], reverse=True):
            table_neg.add_row(
                cat.replace("_", " ").title(), 
                str(data["count"]), 
                str(data["score"]), 
                ", ".join(data["phrases"])
            )
        console.print(table_neg)

def main():
    parser = argparse.ArgumentParser(description="Automated Concall Transcript Evaluator")
    parser.add_argument("ticker", help="NSE Ticker (e.g., ZENTEC.NS)")
    args = parser.parse_args()

    analyzer = ConcallAnalyzer()
    
    with console.status(f"[bold green]Hunting for {args.ticker} transcript on BSE..."):
        pdf_bytes, ann = analyzer.fetch_latest_transcript_pdf(args.ticker)
    
    if not pdf_bytes:
        console.print(f"[yellow]No transcript found for {args.ticker} in the last 12 months.[/yellow]")
        return
        
    with console.status("[bold green]Extracting and reading PDF text..."):
        text = analyzer.extract_text(pdf_bytes)
        
    if not text.strip():
        console.print("[red]Failed to extract text from the PDF.[/red]")
        return
        
    results = analyzer.analyze_transcript(text)
    print_analysis(args.ticker, ann, results)

if __name__ == "__main__":
    main()
