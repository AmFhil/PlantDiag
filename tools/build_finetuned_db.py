#!/usr/bin/env python3
"""
Generate localized disease database and classes.json for the 9-class fine-tuned model.
"""

import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
APP_ROOT = WORKSPACE / "Agrinovva mobile app"

CLASSES = [
  "Cassava___Bacterial_Blight",
  "Cassava___Brown_Streak_Disease",
  "Cassava___Green_Mottle",
  "Cassava___Healthy",
  "Cassava___Mosaic_Disease",
  "Rice___Bacterial_Blight",
  "Rice___Blast",
  "Rice___Brown_Spot",
  "Rice___Healthy"
]

DISEASES = [
  {
    "model_class_id": 0,
    "id": "cassava_cbb",
    "crop": "Cassava",
    "disease_name": "Bacterial Blight (CBB)",
    "is_healthy": False,
    "symptoms": "Water-soaked angular spots on leaves, leaf wilting, and gum exudation on stems.",
    "treatment": "Use disease-free stem cuttings, rogue infected plants, and practice crop rotation.",
    "treatment_ha": "A yi amfani da guntun rogo marasa cuta, a cire shuke-shuken da suka kamu, a kuma canza amfanin gona.",
    "treatment_yo": "Lo ege ti ko ni aisan, fa awọn igi ti o ba ti ni aisan tu, ki o si yi iru ọgbin pada.",
    "treatment_ig": "Jiri osisi akpu na-enweghị ọrịa kụọ, gbupụ ndị nke butere ọrịa ma gbanwee ihe a na-akụ.",
    "treatment_pcm": "Use clean cassava stick plant, pull out sick plants and rotate your crops well.",
    "severity": "severe"
  },
  {
    "model_class_id": 1,
    "id": "cassava_cbsd",
    "crop": "Cassava",
    "disease_name": "Brown Streak Disease",
    "is_healthy": False,
    "symptoms": "Feathery yellow chlorosis along leaf veins and brown necrotic dry rot in storage roots.",
    "treatment": "Plant certified clean planting materials and control whitefly insect vectors with organic neem spray.",
    "treatment_ha": "A shuka tsaba masu inganci kuma a fesa maganin kashe kwari na neem don magance fararen kuda.",
    "treatment_yo": "Gbin irugbin to mọ gaara ki o si lo oogun ewe dogoyaro lati le awon kokoro funfun kuro.",
    "treatment_ig": "Kụọ akpu a kwadoro na ọ dị ọcha ma gbaa ọgwụ neem iji gbuo ijiji ọcha na-ebute ọrịa.",
    "treatment_pcm": "Plant clean cassava stick and use neem spray chase whitefly wey dey carry the sickness.",
    "severity": "severe"
  },
  {
    "model_class_id": 2,
    "id": "cassava_green_mottle",
    "crop": "Cassava",
    "disease_name": "Green Mottle",
    "is_healthy": False,
    "symptoms": "Severe green mottling, puckering, and leaf curling with stunted foliage growth.",
    "treatment": "Rogue out infected plants immediately and sanitize harvesting tools between plots.",
    "treatment_ha": "A cire shuke-shuken da suka kamu nan da nan kuma a tsaftace kayan aiki.",
    "treatment_yo": "Fa awọn ewe ti aisan ba kuro lẹsẹkẹsẹ ki o si fọ awọn irinṣẹ oko.",
    "treatment_ig": "Kwụpụ osisi ndị butere ọrịa ngwa ngwa ma hichaa ngwa ọrụ ugbo gị.",
    "treatment_pcm": "Comot any plant wey catch am quick quick and wash your farm tools well well.",
    "severity": "moderate"
  },
  {
    "model_class_id": 3,
    "id": "cassava_healthy",
    "crop": "Cassava",
    "disease_name": "Healthy Cassava",
    "is_healthy": True,
    "symptoms": "Normal vibrant green palm-shaped leaves with vigorous canopy growth.",
    "treatment": "No treatment needed. Continue good weeding and proper soil mounding.",
    "treatment_ha": "Babu bukatar magani. Ci gaba da noma da gyara ƙasa yadda ya dace.",
    "treatment_yo": "Ko nilo oogun kankan. Tẹsiwaju pẹlu itọju ilẹ ati fifa koriko.",
    "treatment_ig": "Ọ dịghị ọgwụ dị mkpa. Na-akọchapụ ata ma na-elekọta ya nke ọma.",
    "treatment_pcm": "Crop dey fine well well! No need medicine, just continue weeding and farming well.",
    "severity": "none"
  },
  {
    "model_class_id": 4,
    "id": "cassava_cmd",
    "crop": "Cassava",
    "disease_name": "Cassava Mosaic Disease (CMD)",
    "is_healthy": False,
    "symptoms": "Distorted, stunted, twisted leaves with distinct yellow and green mosaic patches.",
    "treatment": "Plant IITA-improved mosaic-resistant varieties (e.g. TME 419) and eliminate whitefly breeding grounds.",
    "treatment_ha": "A shuka nau'in rogo mai jure cuta na IITA (kamar TME 419) kuma a kiyaye fararen kuda.",
    "treatment_yo": "Gbin irúgbìn ege ti o le kọ aisan (bi TME 419) ki o si kapa awọn kokoro funfun.",
    "treatment_ig": "Kụọ ụdị akpu na-anaghị anabata ọrịa (dị ka TME 419) ma gbochie ijiji ọcha ịmụba.",
    "treatment_pcm": "Plant strong cassava stick like TME 419 wey get power to fight mosaic disease.",
    "severity": "severe"
  },
  {
    "model_class_id": 5,
    "id": "rice_bb",
    "crop": "Rice",
    "disease_name": "Bacterial Blight",
    "is_healthy": False,
    "symptoms": "Water-soaked lesions on leaf margins turning yellow to grayish-white stripes.",
    "treatment": "Avoid excessive nitrogen fertilizer application, drain field periodically, and use resistant varieties.",
    "treatment_ha": "A rage yawan takin zamani mai nitrogen, a riƙa fitar da ruwa daga gona akai-akai.",
    "treatment_yo": "Dinku lilo ajile nitrogen pupọju, ki o si maa fa omi kuro lori oko lẹẹkọọkan.",
    "treatment_ig": "Belata nri nitrogen na-aba ụba, dọpụ mmiri n'ubi ugboro ugboro ma kụọ ụdị osisi siri ike.",
    "treatment_pcm": "No put too much fertilizer, drain the water small small and use strong rice seed.",
    "severity": "severe"
  },
  {
    "model_class_id": 6,
    "id": "rice_blast",
    "crop": "Rice",
    "disease_name": "Rice Blast",
    "is_healthy": False,
    "symptoms": "Diamond/spindle-shaped lesions with gray-white centers and brownish borders on leaves and neck rot.",
    "treatment": "Apply systemic fungicide (e.g., tricyclazole) at early tillering and maintain consistent flood water.",
    "treatment_ha": "A fesa maganin fungal (kamar tricyclazole) tun da wuri kuma a kula da daidaiton ruwa.",
    "treatment_yo": "Fun oogun aisan (bi tricyclazole) lori oko ni kete ti aisan ba bẹrẹ ki o si toju omi.",
    "treatment_ig": "Gbaa ọgwụ fungal dị ka tricyclazole n'oge ma na-edebe mmiri n'ogo kwesịrị ekwesị.",
    "treatment_pcm": "Spray fungicide quick quick when you see the spot, and keep good water level for the paddy.",
    "severity": "severe"
  },
  {
    "model_class_id": 7,
    "id": "rice_brown_spot",
    "crop": "Rice",
    "disease_name": "Brown Spot",
    "is_healthy": False,
    "symptoms": "Small oval, dark brown spots on leaves with yellow halos, leading to leaf blighting.",
    "treatment": "Correct soil micronutrient deficiencies (potassium and silicon) and treat seed with fungicide prior to planting.",
    "treatment_ha": "A gyara sinadaran ƙasa da takin da ya dace kuma a magance tsaba kafin shukawa.",
    "treatment_yo": "Tọju eroja inu ilẹ ki o si tọju irugbin pẹlu oogun ki o to gbin in.",
    "treatment_ig": "Mee ka ala nri baa ụba ma gwọọ mkpụrụ osisi tupu a kụọ ya.",
    "treatment_pcm": "Feed the soil well with good fertilizer and treat the rice seed before planting.",
    "severity": "moderate"
  },
  {
    "model_class_id": 8,
    "id": "rice_healthy",
    "crop": "Rice",
    "disease_name": "Healthy Rice",
    "is_healthy": True,
    "symptoms": "Clean, bright green uniform paddy leaves with strong tillering.",
    "treatment": "No treatment needed. Maintain water management and standard agronomic fertilizer schedule.",
    "treatment_ha": "Babu bukatar magani. Ci gaba da kula da ruwa da takin zamani yadda ya dace.",
    "treatment_yo": "Ko nilo oogun kankan. Tẹsiwaju pẹlu mimojuto omi ati lilo ajile deedee.",
    "treatment_ig": "Ọ dịghị ọgwụ dị mkpa. Na-elekọta mmiri na nri ala dị ka a na-eme na mbụ.",
    "treatment_pcm": "Paddy dey fresh and green! No medicine needed, just maintain your water well.",
    "severity": "none"
  }
]

DB_DATA = {
  "meta": {
    "source": "PlantDiag Fine-Tuned African Regional Staples Model",
    "model": "plantdiag_finetuned.tflite (MobileNetV3 9-class)",
    "classes_order": "matches classes.json index 0-8",
    "languages": ["en", "ha", "yo", "ig", "pcm"],
    "version": "2.0",
    "note": "Optimized model with balanced Cassava and Rice regional varieties."
  },
  "diseases": DISEASES
}

# Destinations
targets_classes = [
  APP_ROOT / "models" / "classes.json",
  APP_ROOT / "src" / "assets" / "model" / "classes.json",
  APP_ROOT / "android" / "app" / "src" / "main" / "assets" / "public" / "assets" / "model" / "classes.json"
]

targets_db = [
  APP_ROOT / "models" / "disease_db.json",
  APP_ROOT / "src" / "assets" / "model" / "disease_db.json",
  APP_ROOT / "android" / "app" / "src" / "main" / "assets" / "public" / "assets" / "model" / "disease_db.json"
]

for p in targets_classes:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(CLASSES, f, indent=2, ensure_ascii=False)
    print(f"Updated classes: {p}")

for p in targets_db:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(DB_DATA, f, indent=2, ensure_ascii=False)
    print(f"Updated disease DB: {p}")

print("\nSuccessfully updated all 9-class database references.")
