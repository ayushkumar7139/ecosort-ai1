"""
EcoSort AI — Image Classifier

Supports multiple AI backends:
  1. Hugging Face Inference API (free tier, real classification)
  2. Amazon Bedrock (Claude claude-3-haiku with vision)
  3. Demo mode (simulated results, clearly labelled)

The classifier maps raw model output labels to EcoSort waste categories
using keyword heuristics. This mapping is imperfect and is clearly
communicated as approximate guidance.
"""

import httpx
import base64
import json
import re
import uuid
from datetime import datetime
from typing import Optional
from PIL import Image
import io

from .config import settings
from .models import ClassificationResult, DisposalInstruction

# ---------------------------------------------------------------------------
# Waste category metadata
# ---------------------------------------------------------------------------

DISPOSAL_DATA = {
    "organic": {
        "label": "Organic / Compostable Waste",
        "recyclable": False,
        "checkLocal": False,
        "explanation": "This appears to be organic or food waste. Organic materials are compostable and can be diverted from landfill through composting or municipal green-waste collection.",
        "instructions": [
            DisposalInstruction(step=1, action="Separate from packaging", detail="Remove any non-organic wrapping, labels, or rubber bands."),
            DisposalInstruction(step=2, action="Place in organic / green bin", detail="Use your local organic waste bin or bring to a composting facility."),
            DisposalInstruction(step=3, action="Home composting option", detail="Suitable for home compost. Avoid meat, dairy, and oily food in open home compost piles."),
        ],
        "precautions": [],
    },
    "paper": {
        "label": "Paper & Cardboard",
        "recyclable": True,
        "checkLocal": True,
        "explanation": "This appears to be paper or cardboard. Most clean, dry paper and cardboard is recyclable. Contaminated or wax-coated paper may not be accepted.",
        "instructions": [
            DisposalInstruction(step=1, action="Ensure it is clean and dry", detail="Remove food residue. Greasy or wet paper cannot usually be recycled."),
            DisposalInstruction(step=2, action="Flatten cardboard boxes", detail="Flattening saves space and makes collection more efficient."),
            DisposalInstruction(step=3, action="Place in paper recycling bin", detail="Use the designated paper/cardboard recycling bin."),
        ],
        "precautions": [],
    },
    "plastic": {
        "label": "Plastic",
        "recyclable": True,
        "checkLocal": True,
        "explanation": "This appears to be plastic. Recyclability depends on the plastic type (resin code) and your local facility. PET (#1) and HDPE (#2) are most widely accepted.",
        "instructions": [
            DisposalInstruction(step=1, action="Check the recycling symbol", detail="Look for the resin code number (1-7) on the bottom of the item."),
            DisposalInstruction(step=2, action="Empty and rinse", detail="Remove all content and give a quick rinse to reduce contamination."),
            DisposalInstruction(step=3, action="Check local acceptance", detail="Confirm your local facility accepts this plastic type before placing in recycling."),
            DisposalInstruction(step=4, action="Place in recycling bin", detail="If accepted locally, place in the plastic recycling or mixed recycling bin."),
        ],
        "precautions": [],
    },
    "glass": {
        "label": "Glass",
        "recyclable": True,
        "checkLocal": True,
        "explanation": "This appears to be glass. Glass is infinitely recyclable, but some curbside schemes require glass to be taken to a bottle bank rather than placed in a kerbside bin.",
        "instructions": [
            DisposalInstruction(step=1, action="Empty and rinse", detail="Remove all liquid and rinse the container."),
            DisposalInstruction(step=2, action="Remove lids if required", detail="Metal lids can often be recycled separately. Check local guidance."),
            DisposalInstruction(step=3, action="Use bottle bank or kerbside bin", detail="Check whether your council accepts glass in the kerbside bin or requires a drop-off point."),
        ],
        "precautions": ["Handle broken glass carefully to avoid injury. Place in a sealed, labelled box if broken."],
    },
    "metal": {
        "label": "Metal",
        "recyclable": True,
        "checkLocal": True,
        "explanation": "This appears to be metal (aluminium or steel). Metal cans and packaging are highly recyclable and have significant environmental value when recycled correctly.",
        "instructions": [
            DisposalInstruction(step=1, action="Empty and rinse", detail="Remove all food or liquid and give a quick rinse."),
            DisposalInstruction(step=2, action="Crush if appropriate", detail="Aluminium cans can be crushed to save space, if your facility accepts crushed cans."),
            DisposalInstruction(step=3, action="Place in metal or mixed recycling bin", detail="Metal is typically accepted in mixed recycling or separated metal bins."),
        ],
        "precautions": ["Take care with sharp edges on open cans."],
    },
    "ewaste": {
        "label": "Electronic Waste (E-Waste)",
        "recyclable": True,
        "checkLocal": True,
        "explanation": "This appears to be electronic waste. E-waste contains valuable recoverable materials but also hazardous substances. Do not place in general waste.",
        "instructions": [
            DisposalInstruction(step=1, action="Back up and wipe data", detail="Back up any data and perform a factory reset or secure data wipe before disposal."),
            DisposalInstruction(step=2, action="Locate an e-waste collection point", detail="Find a certified e-waste recycler, retailer take-back scheme, or municipal collection event."),
            DisposalInstruction(step=3, action="Do not place in general waste", detail="E-waste in landfill releases toxic materials into the environment."),
        ],
        "precautions": [
            "Do not attempt to dismantle electronics at home.",
            "Do not incinerate electronics or batteries.",
            "Batteries should be removed carefully and recycled separately if possible.",
        ],
    },
    "general": {
        "label": "General / Residual Waste",
        "recyclable": False,
        "checkLocal": False,
        "explanation": "This appears to be general or residual waste that cannot be easily recycled or composted. It should go in the general waste bin for landfill or energy recovery.",
        "instructions": [
            DisposalInstruction(step=1, action="Place in general waste bin", detail="Use the residual/general waste bin."),
            DisposalInstruction(step=2, action="Consider reduction first", detail="Before discarding, consider whether the item could be repaired, donated, or replaced with a reusable alternative."),
        ],
        "precautions": [],
    },
    "hazardous": {
        "label": "Hazardous / Special Handling Waste",
        "recyclable": False,
        "checkLocal": True,
        "explanation": "This item may require special handling due to hazardous properties. Do not place in general waste or recycling bins.",
        "instructions": [
            DisposalInstruction(step=1, action="Do not place in regular bins", detail="Hazardous waste requires specialist disposal."),
            DisposalInstruction(step=2, action="Contact your local hazardous waste facility", detail="Find your nearest hazardous waste collection point or municipal collection event."),
            DisposalInstruction(step=3, action="Keep in original container if possible", detail="Store safely in the original labelled container until disposal."),
        ],
        "precautions": [
            "Do not handle unknown chemicals without appropriate protection.",
            "Keep away from children.",
            "Do not mix different chemicals.",
            "Never pour chemicals down the drain or into the ground.",
        ],
    },
    "unclassified": {
        "label": "Unable to Classify Confidently",
        "recyclable": False,
        "checkLocal": True,
        "explanation": "The classifier could not determine the waste category with sufficient confidence. Please try a clearer image, or consult your local waste management authority for guidance.",
        "instructions": [
            DisposalInstruction(step=1, action="Try a clearer image", detail="Use a well-lit, close-up photo of the item against a plain background."),
            DisposalInstruction(step=2, action="Check local guidance", detail="Contact your local council or check their website for disposal guidance."),
        ],
        "precautions": [],
    },
}

# ---------------------------------------------------------------------------
# Label → category mapping
# ---------------------------------------------------------------------------

LABEL_TO_CATEGORY_KEYWORDS = {
    "organic": [
        "banana", "apple", "orange", "food", "vegetable", "fruit", "leaf", "leaves",
        "plant", "flower", "bread", "meat", "fish", "egg", "compost", "organic",
        "broccoli", "carrot", "potato", "lemon", "grape", "pear",
    ],
    "paper": [
        "book", "paper", "newspaper", "magazine", "cardboard", "box", "carton",
        "envelope", "document", "notebook",
    ],
    "plastic": [
        "bottle", "plastic", "container", "jug", "bucket", "cup", "straw",
        "packaging", "bag", "wrapper", "tube", "cap",
    ],
    "glass": [
        "glass", "jar", "vase", "window", "mirror",
    ],
    "metal": [
        "can", "tin", "aluminium", "aluminum", "steel", "metal", "foil",
        "iron", "copper", "brass",
    ],
    "ewaste": [
        "phone", "mobile", "laptop", "computer", "keyboard", "mouse", "tablet",
        "monitor", "television", "tv", "battery", "charger", "cable", "electronic",
        "circuit", "remote", "printer", "camera",
    ],
    "hazardous": [
        "medicine", "chemical", "paint", "pesticide", "spray", "aerosol",
        "bleach", "acid", "solvent", "bulb", "fluorescent",
    ],
}

CONFIDENCE_THRESHOLD = 0.35


def map_label_to_category(label: str, score: float) -> tuple[str, float]:
    """Map a raw model label to an EcoSort waste category."""
    label_lower = label.lower()

    # Find the best matching category
    for category, keywords in LABEL_TO_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in label_lower:
                return category, score

    # If confidence is low, return unclassified
    if score < CONFIDENCE_THRESHOLD:
        return "unclassified", score

    # Default to general waste if no keyword matches
    return "general", score


def build_result(category: str, confidence: Optional[float], is_demo: bool = False) -> ClassificationResult:
    """Build a ClassificationResult from category metadata."""
    data = DISPOSAL_DATA.get(category, DISPOSAL_DATA["unclassified"])
    return ClassificationResult(
        id=str(uuid.uuid4()),
        category=category,
        confidence=confidence,
        label=data["label"],
        explanation=data["explanation"],
        disposalInstructions=data["instructions"],
        precautions=data["precautions"],
        recyclable=data["recyclable"],
        checkLocal=data["checkLocal"],
        isDemo=is_demo,
        timestamp=datetime.utcnow().isoformat(),
    )


# ---------------------------------------------------------------------------
# Hugging Face Inference API classifier
# ---------------------------------------------------------------------------

async def classify_with_huggingface(image_bytes: bytes) -> ClassificationResult:
    """Classify an image using the Hugging Face Inference API."""
    model = settings.huggingface_model
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {}
    if settings.huggingface_token:
        headers["Authorization"] = f"Bearer {settings.huggingface_token}"

    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(
            api_url,
            content=image_bytes,
            headers={**headers, "Content-Type": "application/octet-stream"},
        )

    if response.status_code == 503:
        # Model loading — retry is reasonable but for hackathon we surface demo
        raise RuntimeError("Hugging Face model is loading. Please try again in 30 seconds.")

    if response.status_code != 200:
        raise RuntimeError(f"Hugging Face API error {response.status_code}: {response.text[:200]}")

    predictions = response.json()
    if not isinstance(predictions, list) or len(predictions) == 0:
        return build_result("unclassified", None)

    # Take the top prediction
    top = predictions[0]
    raw_label: str = top.get("label", "")
    score: float = float(top.get("score", 0.0))

    category, mapped_confidence = map_label_to_category(raw_label, score)
    return build_result(category, mapped_confidence)


# ---------------------------------------------------------------------------
# Amazon Bedrock classifier (Claude claude-3-haiku with vision)
# ---------------------------------------------------------------------------

async def classify_with_bedrock(image_bytes: bytes, media_type: str = "image/jpeg") -> ClassificationResult:
    """Classify an image using Amazon Bedrock (Claude claude-3-haiku vision)."""
    import boto3

    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """You are a waste classification assistant. Analyze this image and classify the waste into exactly one of these categories: organic, paper, plastic, glass, metal, ewaste, general, hazardous, or unclassified.

Respond ONLY with a JSON object like:
{"category": "plastic", "confidence": 0.85, "description": "PET plastic bottle"}

Categories:
- organic: food waste, fruit peels, vegetable scraps, garden waste
- paper: paper, cardboard, newspapers, magazines, boxes
- plastic: plastic bottles, containers, packaging, bags
- glass: glass bottles, jars, glassware
- metal: aluminium/steel cans, metal packaging, foil
- ewaste: phones, laptops, batteries, cables, electronics
- general: mixed or non-recyclable waste
- hazardous: chemicals, medicines, paint, batteries (single-use), fluorescent bulbs
- unclassified: image too unclear or ambiguous to classify

Important: If you cannot identify a waste item with reasonable confidence, use unclassified."""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 256,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    })

    response = client.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    response_body = json.loads(response["body"].read())
    text = response_body["content"][0]["text"].strip()

    # Extract JSON from response
    match = re.search(r'\{[^}]+\}', text)
    if not match:
        return build_result("unclassified", None)

    parsed = json.loads(match.group())
    category = parsed.get("category", "unclassified")
    confidence = parsed.get("confidence", None)
    if category not in DISPOSAL_DATA:
        category = "unclassified"

    return build_result(category, float(confidence) if confidence else None)


# ---------------------------------------------------------------------------
# Demo classifier
# ---------------------------------------------------------------------------

IMPORT_INDEX = 0
DEMO_CATEGORIES = ["plastic", "organic", "paper", "metal", "ewaste", "glass"]

async def classify_demo(image_bytes: bytes) -> ClassificationResult:
    """Return a rotating demo result. Clearly marked as demo."""
    global IMPORT_INDEX
    category = DEMO_CATEGORIES[IMPORT_INDEX % len(DEMO_CATEGORIES)]
    IMPORT_INDEX += 1
    result = build_result(category, 0.75, is_demo=True)
    result.explanation = f"[DEMO MODE] {result.explanation}"
    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def classify_image(image_bytes: bytes, media_type: str = "image/jpeg") -> ClassificationResult:
    """Route to the correct classifier based on configuration."""
    provider = settings.ai_provider.lower()

    if settings.demo_mode or provider == "demo":
        return await classify_demo(image_bytes)

    if provider == "bedrock":
        return await classify_with_bedrock(image_bytes, media_type)

    if provider == "huggingface":
        return await classify_with_huggingface(image_bytes)

    # Fallback to demo
    return await classify_demo(image_bytes)
