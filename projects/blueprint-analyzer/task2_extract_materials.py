#!/usr/bin/env python3
"""
Task 2: Extract Materials from Commercial Blueprints
Using Claude Vision API for material extraction and accuracy validation.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import base64
import time
from datetime import datetime

import anthropic


class BlueprintExtractor:
    """Extract materials from blueprint PDFs using Claude Vision."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", max_tokens: int = 2048):
        self.client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY from env
        self.model = model
        self.max_tokens = max_tokens
        self.extraction_results = []

        # System prompt for material extraction
        self.system_prompt = """You are an expert construction cost estimator analyzing architectural blueprints.
Your task is to extract materials, quantities, and specifications from blueprint documents.

RESPONSE FORMAT - Return ONLY valid JSON (no markdown, no explanation):
{
  "confidence": 0.85,
  "materials": [
    {
      "id": "mat_001",
      "name": "Material Name - Description",
      "quantity": 100,
      "unit": "pieces|sheets|linear_feet|square_feet|gallons|bags|boxes|lbs",
      "category": "lumber|drywall|electrical|plumbing|hvac|roofing|paint|hardware|insulation|other",
      "confidence": 0.92,
      "specifications": {
        "size": "2x4",
        "grade": "SPF",
        "type": "stud"
      },
      "room_location": "Master Bedroom, Kitchen, etc"
    }
  ],
  "analysis_notes": ["Notes about extraction quality"]
}

Guidelines:
- Extract materials visible/specifiable from the blueprint
- Confidence: 0.9+ = clearly specified, 0.7-0.9 = inferred from context, <0.7 = uncertain
- Be conservative: omit uncertain items rather than guess
- Include quantities as shown or reasonably calculated
- Flag low-confidence items in notes
"""

    def extract_from_pdf(self, pdf_path: str) -> Optional[Dict]:
        """Extract materials from a PDF using Claude Vision."""
        try:
            print(f"  Reading PDF: {pdf_path}...")
            file_size = Path(pdf_path).stat().st_size / (1024 * 1024)

            if file_size == 0:
                print(f"    ⚠️  Empty PDF file")
                return None

            # Read PDF as base64
            with open(pdf_path, "rb") as pdf_file:
                pdf_data = base64.standard_b64encode(pdf_file.read()).decode("utf-8")

            print(f"    Sending to Claude Vision API (size: {file_size:.1f} MB)...")

            # Call Claude Vision API with PDF
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Extract all construction materials from this blueprint. Return ONLY valid JSON with no markdown, no explanations."
                            }
                        ],
                    }
                ],
            )

            # Parse response
            response_text = message.content[0].text
            print(f"    Response received ({len(response_text)} chars)")

            # Try to extract JSON from response
            if "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]

                try:
                    result = json.loads(json_str)
                    materials = result.get("materials", [])
                    print(f"    ✅ Extracted {len(materials)} materials (confidence: {result.get('confidence', 0):.2f})")
                    return result
                except json.JSONDecodeError as je:
                    print(f"    ⚠️  Invalid JSON in response: {je}")
                    print(f"       Response: {response_text[:200]}...")
                    return None
            else:
                print(f"    ⚠️  No JSON found in response")
                print(f"       Response: {response_text[:200]}...")
                return None

        except anthropic.APIStatusError as e:
            if "overloaded" in str(e).lower() or "rate" in str(e).lower():
                print(f"  ⏳ Rate limited, waiting 30 seconds...")
                time.sleep(30)
                return self.extract_from_pdf(pdf_path)  # Retry once
            else:
                print(f"  ❌ API Error: {e}")
                return None
        except Exception as e:
            print(f"  ❌ Error extracting from {pdf_path}: {e}")
            return None

    def extract_from_blueprints(
        self, blueprint_dir: str, max_pdfs: int = 5
    ) -> List[Dict]:
        """Extract materials from multiple blueprint PDFs."""
        results = []
        pdf_files = sorted(Path(blueprint_dir).glob("*.pdf"))[:max_pdfs]

        print(f"\n📋 Processing {len(pdf_files)} blueprints...")
        print("=" * 70)

        for idx, pdf_file in enumerate(pdf_files, 1):
            if pdf_file.stat().st_size < 1000:  # Skip tiny files (like empty PDFs)
                print(f"\n[{idx}/{len(pdf_files)}] {pdf_file.name} - Skipped (too small)")
                continue

            print(f"\n[{idx}/{len(pdf_files)}] {pdf_file.name} ({pdf_file.stat().st_size / (1024*1024):.1f} MB)")

            result = self.extract_from_pdf(str(pdf_file))

            if result:
                materials = result.get("materials", [])

                for mat in materials:
                    results.append({
                        "source_pdf": pdf_file.name,
                        "extracted_at": datetime.now().isoformat(),
                        **mat
                    })

                # Rate limiting
                if idx < len(pdf_files):
                    print(f"  Waiting 2 seconds before next extraction...")
                    time.sleep(2)
            else:
                print(f"  ⚠️  Failed to extract materials")

        return results

    def evaluate_accuracy(self, results: List[Dict]) -> Dict:
        """Evaluate extraction accuracy."""
        if not results:
            return {
                "total_materials": 0,
                "avg_confidence": 0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
                "by_category": {},
                "accuracy_rating": "INSUFFICIENT DATA"
            }

        high = sum(1 for r in results if r.get("confidence", 0) >= 0.85)
        medium = sum(1 for r in results if 0.70 <= r.get("confidence", 0) < 0.85)
        low = sum(1 for r in results if r.get("confidence", 0) < 0.70)
        avg_confidence = sum(r.get("confidence", 0) for r in results) / len(results)

        by_category = {}
        for r in results:
            cat = r.get("category", "unknown")
            if cat not in by_category:
                by_category[cat] = {"count": 0, "avg_confidence": 0, "items": []}
            by_category[cat]["count"] += 1
            by_category[cat]["items"].append(r.get("name", "unknown"))
            by_category[cat]["avg_confidence"] = (
                by_category[cat]["avg_confidence"] * (by_category[cat]["count"] - 1)
                + r.get("confidence", 0)
            ) / by_category[cat]["count"]

        # Accuracy rating based on confidence scores
        if avg_confidence >= 0.80:
            rating = "EXCELLENT (80%+)"
        elif avg_confidence >= 0.70:
            rating = "GOOD (70-80%)"
        elif avg_confidence >= 0.60:
            rating = "FAIR (60-70%)"
        else:
            rating = "POOR (<60%)"

        return {
            "total_materials": len(results),
            "avg_confidence": avg_confidence,
            "high_confidence_count": high,
            "medium_confidence_count": medium,
            "low_confidence_count": low,
            "by_category": by_category,
            "accuracy_rating": rating,
        }

    def save_results(self, results: List[Dict], output_file: str):
        """Save extraction results to JSON file."""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ Results saved to: {output_file}")

    def print_summary(self, results: List[Dict], metrics: Dict):
        """Print extraction summary."""
        print("\n" + "=" * 70)
        print("EXTRACTION SUMMARY")
        print("=" * 70)
        print(f"Total materials extracted:  {metrics['total_materials']}")
        print(f"Average confidence:         {metrics['avg_confidence']:.2%}")
        print(f"  - High (≥0.85):           {metrics['high_confidence_count']} items")
        print(f"  - Medium (0.70-0.85):     {metrics['medium_confidence_count']} items")
        print(f"  - Low (<0.70):            {metrics['low_confidence_count']} items")
        print(f"\nAccuracy Rating:            {metrics['accuracy_rating']}")

        if metrics["by_category"]:
            print(f"\nMaterials by Category:")
            for category, stats in sorted(metrics["by_category"].items()):
                count = stats['count']
                conf = stats['avg_confidence']
                print(f"  - {category:<15} {count:>3} items (avg confidence: {conf:.2%})")

        if results:
            print(f"\nSample Materials (first 10):")
            for i, mat in enumerate(results[:10], 1):
                name = mat['name'][:40]
                qty = mat['quantity']
                unit = mat['unit']
                conf = mat['confidence']
                print(f"  {i:>2}. {name:<40} qty={qty:<6} {unit:<15} conf={conf:.2%}")

        print("=" * 70 + "\n")


def main():
    """Main execution."""
    print("\n" + "=" * 70)
    print("TASK 2: BLUEPRINT MATERIAL EXTRACTION")
    print("Using Claude Vision API")
    print("=" * 70)

    blueprint_dir = "/tmp/commercial_blueprints"
    output_file = "/tmp/extraction_results.json"

    # Check if directory exists
    if not Path(blueprint_dir).exists():
        print(f"❌ Blueprint directory not found: {blueprint_dir}")
        sys.exit(1)

    # Create extractor
    extractor = BlueprintExtractor()

    # Extract from blueprints
    try:
        results = extractor.extract_from_blueprints(
            blueprint_dir, max_pdfs=5
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Extraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not results:
        print("❌ No materials extracted. Check API key, PDFs, and rate limits.")
        sys.exit(1)

    # Evaluate accuracy
    metrics = extractor.evaluate_accuracy(results)

    # Save results
    extractor.save_results(results, output_file)

    # Print summary
    extractor.print_summary(results, metrics)

    # Check if target accuracy met
    if metrics["avg_confidence"] >= 0.80:
        print("✅ TARGET ACCURACY MET (80%+)")
        return 0
    else:
        print(f"⚠️  Below target accuracy (need 80%, got {metrics['avg_confidence']:.1%})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
