CANCER_COLOR_MAP = {
    "Non-Small Cell Lung Cancer": "#4C78A8",
    "Breast Cancer": "#E45756",
    "Pancreatic Cancer": "#2CBF9B",
    "Colorectal Cancer": "#9D6CFF",
    "Prostate Cancer": "#F28E2B",
    "Other": "#9AA0A6",
}

# Prima vengono usati questi colori molto diversi tra loro.
# Quindi con poche istologie avrai contrasto forte.
HISTOLOGY_BASE_COLORS = [
    "#005F73",  # deep teal
    "#0DEE0D",  # brick red
    "#79B7B8",  # teal
    "#9B2226",  # dark red
    "#5F0F40",  # plum
    "#0CE2D0",  # rust
    "#3A0CA3",  # deep violet
    "#4361EE",  # vivid blue
    "#2D6A4F",  # dark green
    "#6D6875",  # muted mauve
]

# Dal nono elemento in poi vengono create sfumature dei colori base.
# SHADE_STEPS = [0.00, 0.24, -0.18, 0.42, -0.32, 0.58, -0.46]
SHADE_STEPS = [0.00, 0.18, -0.16, 0.34, -0.28, 0.50, -0.40]

def _hex_to_rgb_tuple(hex_color):
    hex_color = str(hex_color).strip().lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_tuple_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(
        *[max(0, min(255, int(round(v)))) for v in rgb]
    )


def _mix_rgb(rgb_a, rgb_b, amount):
    return tuple(a * (1 - amount) + b * amount for a, b in zip(rgb_a, rgb_b))


def _shade_color(hex_color, shade_level):
    step = SHADE_STEPS[shade_level % len(SHADE_STEPS)]
    rgb = _hex_to_rgb_tuple(hex_color)

    if step == 0:
        return hex_color

    if step > 0:
        return _rgb_tuple_to_hex(_mix_rgb(rgb, (255, 255, 255), step))

    return _rgb_tuple_to_hex(_mix_rgb(rgb, (0, 0, 0), abs(step)))


def _adaptive_histology_color(index):
    base_index = index % len(HISTOLOGY_BASE_COLORS)
    shade_level = index // len(HISTOLOGY_BASE_COLORS)
    return _shade_color(HISTOLOGY_BASE_COLORS[base_index], shade_level)


def make_color_map(labels):
    """
    Palette adattiva:
    - i cancer type principali mantengono i colori fissi;
    - le istologie/OncoTree code prendono prima colori molto diversi;
    - se aumentano, le successive diventano sfumature dei colori già usati.
    """
    cleaned_labels = []
    seen = set()

    for label in labels or []:
        label = str(label).strip()
        if not label or label in seen:
            continue
        cleaned_labels.append(label)
        seen.add(label)

    result = {}
    histology_labels = []

    for label in cleaned_labels:
        if label in CANCER_COLOR_MAP:
            result[label] = CANCER_COLOR_MAP[label]
        else:
            histology_labels.append(label)

    for i, label in enumerate(histology_labels):
        result[label] = _adaptive_histology_color(i)

    return result


def get_group_color(label, color_map=None):
    label = str(label).strip()

    if color_map and label in color_map:
        return color_map[label]

    if label in CANCER_COLOR_MAP:
        return CANCER_COLOR_MAP[label]

    return HISTOLOGY_BASE_COLORS[0]


def hex_to_rgba(hex_color, alpha=1.0):
    hex_color = str(hex_color).strip().lstrip("#")
    if len(hex_color) != 6:
        return f"rgba(154,160,166,{alpha})"

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return f"rgba({r},{g},{b},{alpha})"