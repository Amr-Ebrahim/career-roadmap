from boilerplate import strip_boilerplate, boiler_kind, must_keep
from skill_matcher import extract_skills

text = (
    "Medical/Dental/Vision Insurance"
    "Retirement Plan w/ 3% match"
    "2 weeks PTO"
    "Paid Training & Certifications"
)

removed = []

print("Recognized skills:", extract_skills(text))
print("Boilerplate category:", boiler_kind(text))
print("Safety rule keeps it:", must_keep(text))
print("Cleaned text:", repr(strip_boilerplate(text, removed)))
print("Removed pieces:", removed)