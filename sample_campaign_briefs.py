"""
BASIC SETUP STEP 3: fictional campaign briefs, used to test D2/D3/merge
all day. Written as messy free text on purpose -- that's what the brief
parser actually has to handle, not clean JSON.
"""

SAMPLE_BRIEFS = [
    {
        "id": "BRIEF_01_full_spec",
        "text": (
            "We're launching a new mid-range sneaker line targeting young "
            "professionals, 18-34, commuters. Budget around $40,000. Want "
            "coverage in Las Hackland, ideally the downtown/financial "
            "corridor. Campaign should run for about 3 weeks, evening "
            "rush hour is a priority. Objective is awareness."
        ),
    },
    {
        "id": "BRIEF_02_no_budget",
        "text": (
            "Local healthcare clinic wants to advertise a new clinic "
            "opening in DA Town. Target: families, older adults 35+. "
            "No fixed budget yet, exploring options. Would like broad "
            "coverage, not tied to one corridor. Objective: conversions "
            "(book an appointment)."
        ),
    },
    {
        "id": "BRIEF_03_vague",
        "text": (
            "Something for a music festival happening soon in "
            "Accordionshire. Want people to know about it, young crowd, "
            "nightlife vibe. Whatever screens make sense near where "
            "people go out in the evening."
        ),
    },
]

if __name__ == "__main__":
    for b in SAMPLE_BRIEFS:
        print(f"--- {b['id']} ---\n{b['text']}\n")