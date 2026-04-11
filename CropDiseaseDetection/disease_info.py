DISEASE_INFO = {
    # Apple
    "Apple___Apple_scab": {
        "description": (
            "Apple scab is a fungal disease caused by Venturia inaequalis. "
            "It produces olive-green to brown lesions on leaves and fruit."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply fungicides (captan, mancozeb) at bud break",
            "Remove and destroy fallen infected leaves",
            "Prune to improve air circulation",
        ],
        "prevention": [
            "Plant scab-resistant varieties",
            "Rake and remove leaf debris in autumn",
            "Avoid overhead irrigation",
        ],
    },
    "Apple___Black_rot": {
        "description": (
            "Black rot (Botryosphaeria obtusa) causes circular lesions on fruit "
            "and frog-eye leaf spots. Infected fruit mummifies on the tree."
        ),
        "severity": "Severe",
        "treatment": [
            "Remove mummified fruit and infected wood",
            "Apply captan or thiophanate-methyl fungicide",
            "Prune cankers at least 15 cm below visible infection",
        ],
        "prevention": [
            "Maintain tree vigour with balanced fertilisation",
            "Inspect and remove dead wood annually",
            "Avoid bark injuries",
        ],
    },
    "Apple___Cedar_apple_rust": {
        "description": (
            "Cedar-apple rust (Gymnosporangium juniperi-virginianae) requires "
            "both apple/crabapple and eastern red cedar to complete its life cycle."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply myclobutanil or propiconazole fungicide at pink-bud stage",
            "Remove nearby juniper/cedar galls if feasible",
        ],
        "prevention": [
            "Plant rust-resistant apple cultivars",
            "Avoid planting apples near eastern red cedars",
        ],
    },
    "Apple___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": [
            "Continue regular monitoring",
            "Maintain proper nutrition and irrigation",
        ],
    },

    # Blueberry 
    "Blueberry___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Maintain soil pH 4.5–5.5", "Prune annually for air flow"],
    },

    # Cherry
    "Cherry_(including_sour)___Powdery_mildew": {
        "description": (
            "Powdery mildew (Podosphaera clandestina) forms white powdery "
            "colonies on leaves, shoots, and fruit."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply sulphur-based or potassium bicarbonate fungicide",
            "Remove heavily infected shoots",
        ],
        "prevention": [
            "Improve air circulation by pruning",
            "Avoid excess nitrogen fertilisation",
            "Plant resistant varieties",
        ],
    },
    "Cherry_(including_sour)___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Monitor regularly", "Maintain balanced nutrition"],
    },

    # Corn 
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": {
        "description": (
            "Gray leaf spot (Cercospora zeae-maydis) causes rectangular, "
            "tan-to-grey lesions parallel to leaf veins."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply strobilurin or triazole fungicides at tasselling",
            "Incorporate infected residue after harvest",
        ],
        "prevention": [
            "Rotate crops — avoid continuous maize",
            "Use resistant hybrids",
            "Reduce surface residue by tillage",
        ],
    },
    "Corn_(maize)___Common_rust_": {
        "description": (
            "Common rust (Puccinia sorghi) produces brick-red pustules on "
            "both leaf surfaces."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply triazole fungicide (propiconazole) early",
            "Scout regularly and act at first sign",
        ],
        "prevention": [
            "Plant rust-resistant hybrids",
            "Early planting to avoid peak spore dispersal",
        ],
    },
    "Corn_(maize)___Northern_Leaf_Blight": {
        "description": (
            "Northern leaf blight (Exserohilum turcicum) causes large, "
            "cigar-shaped tan lesions up to 15 cm long."
        ),
        "severity": "Severe",
        "treatment": [
            "Apply strobilurin + triazole fungicide at V8 or tasselling",
            "Remove severely infected leaves",
        ],
        "prevention": [
            "Rotate to non-host crops",
            "Use resistant hybrids",
            "Reduce surface residue",
        ],
    },
    "Corn_(maize)___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Continue scouting", "Maintain balanced fertilisation"],
    },

    # Grape 
    "Grape___Black_rot": {
        "description": (
            "Grape black rot (Guignardia bidwellii) causes brown leaf lesions "
            "with black pycnidia and mummified berries."
        ),
        "severity": "Severe",
        "treatment": [
            "Apply myclobutanil or mancozeb from bud break to fruit set",
            "Remove mummified berries and infected shoots",
        ],
        "prevention": [
            "Ensure good canopy air flow by training/pruning",
            "Avoid overhead irrigation",
            "Remove all mummies before bud break",
        ],
    },
    "Grape___Esca_(Black_Measles)": {
        "description": (
            "Esca is a complex vascular disease caused by multiple fungi "
            "including Phaeomoniella chlamydospora. It causes tiger-stripe "
            "leaf symptoms and internal wood decay."
        ),
        "severity": "Severe",
        "treatment": [
            "No curative fungicide; remove severely affected canes",
            "Protect pruning wounds with fungicidal paint (thiophanate-methyl)",
        ],
        "prevention": [
            "Prune in dry weather to avoid wound infection",
            "Use double-pruning technique",
            "Remove and burn infected wood",
        ],
    },
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": {
        "description": (
            "Caused by Pseudocercospora vitis, producing angular dark-brown "
            "spots mainly on older leaves."
        ),
        "severity": "Mild",
        "treatment": [
            "Apply copper-based fungicide at early sign",
            "Remove infected leaves from the canopy",
        ],
        "prevention": [
            "Improve air circulation",
            "Avoid overhead watering",
        ],
    },
    "Grape___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Monitor weekly", "Maintain balanced vine nutrition"],
    },

    # Orange
    "Orange___Haunglongbing_(Citrus_greening)": {
        "description": (
            "Huanglongbing (HLB) is caused by the bacterium Candidatus "
            "Liberibacter asiaticus, spread by the Asian citrus psyllid. "
            "There is currently no cure."
        ),
        "severity": "Severe",
        "treatment": [
            "Remove and destroy infected trees to slow spread",
            "Control psyllid vector with imidacloprid or spirotetramat",
        ],
        "prevention": [
            "Use certified disease-free nursery stock",
            "Monitor and manage psyllid populations",
            "Quarantine affected areas",
        ],
    },

    # Peach 
    "Peach___Bacterial_spot": {
        "description": (
            "Bacterial spot (Xanthomonas arboricola pv. pruni) causes water-soaked "
            "lesions on leaves and fruit that turn brown and may drop out."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply copper bactericide at petal fall and every 10–14 days",
            "Remove severely infected shoots",
        ],
        "prevention": [
            "Plant resistant cultivars",
            "Avoid overhead irrigation",
            "Prune to open canopy",
        ],
    },
    "Peach___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Continue monitoring", "Thin fruit for better air flow"],
    },

    # Pepper
    "Pepper,_bell___Bacterial_spot": {
        "description": (
            "Bacterial spot (Xanthomonas euvesicatoria) causes water-soaked "
            "lesions on leaves and sunken scabby spots on fruit."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply copper + mancozeb bactericide spray",
            "Remove heavily infected plant material",
        ],
        "prevention": [
            "Use certified disease-free seed",
            "Rotate crops for at least 2 years",
            "Avoid overhead irrigation",
        ],
    },
    "Pepper,_bell___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Scout regularly", "Maintain irrigation consistency"],
    },

    # Potato
    "Potato___Early_blight": {
        "description": (
            "Early blight (Alternaria solani) produces dark concentric rings "
            "on older leaves, reducing photosynthetic area."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply chlorothalonil or mancozeb fungicide",
            "Remove and destroy infected leaves",
        ],
        "prevention": [
            "Rotate crops — avoid solanaceous plants for 2–3 years",
            "Use certified disease-free seed tubers",
            "Maintain adequate potassium nutrition",
        ],
    },
    "Potato___Late_blight": {
        "description": (
            "Late blight (Phytophthora infestans) is the disease that caused "
            "the Irish famine. It spreads rapidly in cool, wet conditions."
        ),
        "severity": "Severe",
        "treatment": [
            "Apply systemic fungicide (metalaxyl + mancozeb) immediately",
            "Remove and bag infected haulm — do not compost",
            "Hill up soil to protect tubers",
        ],
        "prevention": [
            "Plant certified seed potatoes",
            "Use resistant varieties",
            "Scout fields twice weekly in wet weather",
            "Destroy volunteer potato plants",
        ],
    },
    "Potato___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Monitor weekly", "Ensure good drainage"],
    },

    # Raspberry 
    "Raspberry___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Prune out old canes after harvest", "Maintain air flow"],
    },

    # Soybean
    "Soybean___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Rotate with non-legume crops", "Scout regularly"],
    },

    # Squash 
    "Squash___Powdery_mildew": {
        "description": (
            "Powdery mildew on squash (Podosphaera xanthii / Erysiphe cichoracearum) "
            "forms white powdery patches on leaves."
        ),
        "severity": "Mild",
        "treatment": [
            "Apply potassium bicarbonate, neem oil, or sulphur spray",
            "Remove heavily infected leaves",
        ],
        "prevention": [
            "Plant resistant varieties",
            "Avoid overhead watering",
            "Space plants for good air flow",
        ],
    },

    # Strawberry 
    "Strawberry___Leaf_scorch": {
        "description": (
            "Leaf scorch (Diplocarpon earlianum) causes small, irregular purple "
            "spots that enlarge and cause leaf margins to appear scorched."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply captan or myclobutanil fungicide",
            "Remove and destroy infected foliage after harvest",
        ],
        "prevention": [
            "Use resistant varieties",
            "Renovate beds after harvest",
            "Avoid overhead irrigation",
        ],
    },
    "Strawberry___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": ["Renovate beds annually", "Use straw mulch"],
    },

    # Tomato
    "Tomato___Bacterial_spot": {
        "description": (
            "Bacterial spot (Xanthomonas vesicatoria) causes small water-soaked "
            "lesions on leaves, stems, and fruit."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply copper bactericide at first symptom",
            "Remove infected plant material",
        ],
        "prevention": [
            "Use certified disease-free seed",
            "Avoid overhead irrigation",
            "Rotate crops for 2+ years",
        ],
    },
    "Tomato___Early_blight": {
        "description": (
            "Early blight (Alternaria solani) causes concentric ring lesions "
            "on older leaves, starting from the bottom of the plant."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply chlorothalonil or mancozeb fungicide",
            "Remove infected lower leaves",
            "Mulch to reduce soil splash",
        ],
        "prevention": [
            "Rotate crops",
            "Stake plants to improve air flow",
            "Avoid working in wet conditions",
        ],
    },
    "Tomato___Late_blight": {
        "description": (
            "Late blight (Phytophthora infestans) spreads rapidly in cool, "
            "moist weather and can destroy a crop within days."
        ),
        "severity": "Severe",
        "treatment": [
            "Apply metalaxyl + mancozeb immediately",
            "Remove and bag all infected material",
            "Avoid compost of infected material",
        ],
        "prevention": [
            "Plant resistant varieties",
            "Avoid overhead irrigation",
            "Scout twice weekly in rainy seasons",
        ],
    },
    "Tomato___Leaf_Mold": {
        "description": (
            "Tomato leaf mould (Passalora fulva) forms pale green-yellow "
            "patches on the upper leaf and olive-brown mould on the underside."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply chlorothalonil or mancozeb fungicide",
            "Reduce humidity in greenhouse settings",
        ],
        "prevention": [
            "Ensure good ventilation",
            "Avoid high humidity (>85%)",
            "Use resistant cultivars",
        ],
    },
    "Tomato___Septoria_leaf_spot": {
        "description": (
            "Septoria leaf spot (Septoria lycopersici) causes circular spots "
            "with dark borders and light centres, beginning on lower leaves."
        ),
        "severity": "Moderate",
        "treatment": [
            "Remove and destroy infected leaves",
            "Apply chlorothalonil or copper fungicide",
        ],
        "prevention": [
            "Rotate crops for 2 years",
            "Mulch to reduce soil splash",
            "Stake plants for air circulation",
        ],
    },
    "Tomato___Spider_mites Two-spotted_spider_mite": {
        "description": (
            "Two-spotted spider mites (Tetranychus urticae) cause fine "
            "stippling on leaves; heavy infestations produce webbing."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply miticide (abamectin or bifenazate)",
            "Spray with water to dislodge mites",
            "Introduce predatory mites (Phytoseiulus persimilis)",
        ],
        "prevention": [
            "Maintain adequate irrigation — stressed plants are more susceptible",
            "Avoid excess nitrogen",
            "Monitor undersides of leaves weekly",
        ],
    },
    "Tomato___Target_Spot": {
        "description": (
            "Target spot (Corynespora cassiicola) causes dark concentric "
            "ring lesions on leaves, stems, and fruit."
        ),
        "severity": "Moderate",
        "treatment": [
            "Apply azoxystrobin or difenoconazole fungicide",
            "Remove infected debris",
        ],
        "prevention": [
            "Rotate crops",
            "Avoid dense planting",
            "Control weeds that may harbour the pathogen",
        ],
    },
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {
        "description": (
            "TYLCV is transmitted by the silverleaf whitefly (Bemisia tabaci). "
            "Infected plants show upward leaf curling, yellowing, and stunting."
        ),
        "severity": "Severe",
        "treatment": [
            "No cure — remove and destroy infected plants promptly",
            "Control whitefly with imidacloprid or reflective mulch",
        ],
        "prevention": [
            "Use virus-resistant tomato varieties",
            "Install yellow sticky traps to monitor whiteflies",
            "Use insect-proof netting in nurseries",
        ],
    },
    "Tomato___Tomato_mosaic_virus": {
        "description": (
            "Tomato mosaic virus (ToMV) causes mosaic mottling, leaf distortion, "
            "and can reduce fruit yield by up to 25%."
        ),
        "severity": "Moderate",
        "treatment": [
            "No chemical cure — remove infected plants",
            "Disinfect tools with 10% bleach solution",
        ],
        "prevention": [
            "Use certified virus-free seed",
            "Wash hands before handling plants",
            "Avoid tobacco use near tomatoes",
        ],
    },
    "Tomato___healthy": {
        "description": "The plant appears healthy with no signs of disease.",
        "severity": "None",
        "treatment": [],
        "prevention": [
            "Continue regular scouting",
            "Maintain balanced NPK fertilisation",
        ],
    },
}

def get_disease_info(raw_label: str) -> dict:
    """
    Return treatment/prevention dict for a given class label.
    Falls back to generic info if label not found.
    """
    return DISEASE_INFO.get(
        raw_label,
        {
            "description": "Disease information not available for this class.",
            "severity": "Unknown",
            "treatment": ["Consult a local agricultural extension officer"],
            "prevention": ["Monitor regularly", "Follow good agricultural practices"],
        },
    )