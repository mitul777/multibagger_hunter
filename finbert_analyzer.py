#!/usr/bin/env python3
# =============================================================================
# finbert_analyzer.py — AI-Driven Concall Sentiment Analysis using FinBERT
# =============================================================================
# Uses the yiyanghkust/finbert-tone model to read every sentence of an 
# earnings call transcript and classify it as Positive, Negative, or Neutral.
# =============================================================================

import os
import re
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track
from rich import box

# Suppress HuggingFace/Torch warnings for clean output
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import logging
logging.getLogger("transformers").setLevel(logging.ERROR)

from concall_analyzer import ConcallAnalyzer

console = Console()

def split_into_sentences(text: str) -> list:
    """Basic regex sentence splitter."""
    # Replace newlines with spaces
    text = text.replace('\n', ' ')
    # Split on punctuation followed by space
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Filter out very short fragments (like "1.", "Q.", etc.)
    return [s.strip() for s in sentences if len(s.strip().split()) > 4]

def analyze_document_with_finbert(ticker: str, doc_type: str = "transcript"):
    doc_label = doc_type.replace('_', ' ').title()
    console.print(f"[bold cyan]🔍 Starting FinBERT Analysis for {ticker} ({doc_label})[/bold cyan]")
    
    # 1. Fetch Transcript/Document
    analyzer = ConcallAnalyzer()
    with console.status(f"[bold green]Downloading latest {doc_label} from BSE...[/bold green]"):
        pdf_bytes, ann = analyzer.fetch_latest_document_pdf(ticker, doc_type)
        
    if not pdf_bytes:
        console.print(f"[yellow]No {doc_label} found for {ticker} in recent filings.[/yellow]")
        return None
        
    with console.status("[bold green]Extracting text...[/bold green]"):
        text = analyzer.extract_text(pdf_bytes)
        sentences = split_into_sentences(text)
        
    if not sentences:
        console.print("[red]Could not extract sentences from the PDF.[/red]")
        return None
        
    if doc_type == "annual_report":
        console.print("[dim]Annual Report detected. Scanning the first ~20,000 words (Chairman's Speech & MD&A) to bypass statutory tables.[/dim]")
        sentences = sentences[:1000]
        
    console.print(f"[dim]Extracted {len(sentences)} sentences to analyze.[/dim]")

    # 2. Load Model
    with console.status("[bold magenta]Loading FinBERT Model into Memory (takes a few seconds)...[/bold magenta]"):
        from transformers import pipeline
        # device=-1 means CPU. Use device=0 if you have a GPU.
        pipe = pipeline("text-classification", model="ProsusAI/finbert", device=-1)

    # 3. Score Sentences
    positive = []
    negative = []
    neutral = 0
    
    console.print("[bold magenta]Reading and scoring document...[/bold magenta]")
    
    # Run through pipeline in batches for speed. Truncate long sentences to 512 tokens.
    results = []
    for i in track(range(0, len(sentences), 16), description="Scoring batches..."):
        batch = sentences[i:i+16]
        # HuggingFace pipeline automatically batches if we pass a list
        batch_results = pipe(batch, truncation=True, max_length=512)
        results.extend(batch_results)
        
    # 4. Aggregate Results
    for sentence, res in zip(sentences, results):
        label = res['label'].lower()
        score = res['score']
        
        if label == 'positive':
            positive.append((score, sentence))
        elif label == 'negative':
            negative.append((score, sentence))
        else:
            neutral += 1
            
    # Sort by confidence score
    positive.sort(reverse=True, key=lambda x: x[0])
    negative.sort(reverse=True, key=lambda x: x[0])
    
    # 5. Display Report
    total_scored = len(positive) + len(negative) + neutral
    net_sentiment = ((len(positive) - len(negative)) / total_scored) * 100 if total_scored > 0 else 0
    
    date = ann.get("NEWS_DT", "").split("T")[0]
    
    console.print("\n")
    console.print(Panel.fit(
        f"[bold cyan]🧠 FinBERT AI Analysis: {ticker} ({doc_label})[/bold cyan]\n"
        f"[dim]Date: {date} | Sentences Analyzed: {total_scored:,}[/dim]",
        border_style="cyan"
    ))
    
    # Overall Sentiment
    color = "green" if net_sentiment > 10 else "yellow" if net_sentiment > -10 else "red"
    console.print(f"\n[bold]Net Sentiment Score:[/bold] [bold {color}]{net_sentiment:+.1f}%[/bold {color}]")
    console.print(f"[dim]Breakdown: {len(positive)} Positive | {len(negative)} Negative | {neutral} Neutral[/dim]\n")

    top_pos_quotes = [sentence for score, sentence in positive[:5]]
    top_neg_quotes = [sentence for score, sentence in negative[:5]]

    # Top Positive Quotes
    if positive:
        pos_table = Table(title="[bold green]🟢 Top Positive Statements[/bold green]", box=box.SIMPLE, show_lines=True)
        pos_table.add_column("Confidence", justify="right", style="green")
        pos_table.add_column("Quote")
        for score, sentence in positive[:5]:  # Show top 5
            pos_table.add_row(f"{score*100:.1f}%", f'"{sentence}"')
        console.print(pos_table)
        
    # Top Negative Quotes
    if negative:
        neg_table = Table(title="[bold red]🔴 Top Negative Statements / Risks[/bold red]", box=box.SIMPLE, show_lines=True)
        neg_table.add_column("Confidence", justify="right", style="red")
        neg_table.add_column("Quote")
        for score, sentence in negative[:5]:  # Show top 5
            neg_table.add_row(f"{score*100:.1f}%", f'"{sentence}"')
        console.print(neg_table)
        
    return {
        "net_sentiment": round(net_sentiment, 1),
        "positive_top": top_pos_quotes,
        "negative_top": top_neg_quotes
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinBERT Financial Document Analyzer")
    parser.add_argument("ticker", help="NSE Ticker (e.g., ZENTEC.NS)")
    parser.add_argument("--type", choices=["transcript", "presentation", "annual_report", "press_release"],
                        default="transcript", help="Type of document to analyze")
    args = parser.parse_args()
    
    analyze_document_with_finbert(args.ticker, args.type)
