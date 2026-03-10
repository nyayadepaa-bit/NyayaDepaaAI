"""
data/generate_legal_cases.py
-----------------------------
Generates a comprehensive structured legal case dataset (500+ cases).
Run: python data/generate_legal_cases.py
"""
import json, random, sys
from pathlib import Path

OUTPUT = Path(__file__).parent / "legal_cases.json"

COURTS = {
    "Supreme Court of India": 1.0,
    "Delhi High Court": 0.7,
    "Bombay High Court": 0.7,
    "Madras High Court": 0.7,
    "Calcutta High Court": 0.7,
    "Karnataka High Court": 0.7,
    "Allahabad High Court": 0.7,
    "Kerala High Court": 0.7,
    "Gujarat High Court": 0.7,
    "Punjab & Haryana High Court": 0.7,
    "Delhi District Court": 0.4,
    "Mumbai Sessions Court": 0.4,
    "Chennai Court of Sessions": 0.4,
    "National Company Law Tribunal": 0.6,
    "Income Tax Appellate Tribunal": 0.5,
    "National Consumer Disputes Redressal Commission": 0.5,
    "Central Administrative Tribunal": 0.5,
    "Debt Recovery Tribunal": 0.4,
    "Family Court Mumbai": 0.4,
    "Family Court Delhi": 0.4,
}

OUTCOMES = [
    "Petition Allowed", "Petition Dismissed", "Petition Partly Allowed",
    "Compensation Granted", "Settlement Ordered", "Case Remanded",
    "Interim Relief Granted", "Acquittal", "Conviction",
    "Bail Granted", "Bail Rejected", "Stay Granted",
]

TEMPLATES = {
    "Constitutional Law": [
        {
            "situation": "Petitioner challenged {action} as violating Article {article} of the Constitution regarding {right}.",
            "summary": "The petitioner filed a writ petition under Article 32 challenging {action} on grounds of violation of {right}.",
            "judgement": "Court held that {action} indeed violated Article {article}. The state was directed to ensure {remedy}.",
            "laws": ["Constitution of India", "Article {article}", "Code of Civil Procedure"],
            "keywords": ["fundamental rights", "writ petition", "constitutional validity", "{right}"],
        },
    ],
    "Criminal Law": [
        {
            "situation": "Accused charged with {offence} under IPC Section {ipc_sec}. FIR registered at {state} police station.",
            "summary": "Case involving {offence}. Prosecution presented {evidence_count} witnesses. Defence argued {defence_arg}.",
            "judgement": "Court found {finding}. Evidence was {evidence_quality}. Sentenced to {sentence}.",
            "laws": ["Indian Penal Code 1860", "Code of Criminal Procedure 1973", "IPC Section {ipc_sec}"],
            "keywords": ["{offence}", "FIR", "criminal trial", "bail", "conviction"],
        },
    ],
    "Property Law": [
        {
            "situation": "Dispute over {property_type} property. Plaintiff claimed {claim} under {act}.",
            "summary": "Property dispute involving {property_type}. Plaintiff claimed {claim}. Defendant countered with {counter}.",
            "judgement": "Court ruled in favour of {winner}. Title deed established. Possession ordered within {days} days.",
            "laws": ["Transfer of Property Act 1882", "Registration Act 1908", "{act}"],
            "keywords": ["{property_type}", "title deed", "possession", "property dispute"],
        },
    ],
    "Corporate Law": [
        {
            "situation": "Company facing {corp_issue}. Board resolution challenged by minority shareholders under Companies Act.",
            "summary": "Oppression and mismanagement petition filed. {corp_issue} alleged by {petitioner_count} shareholders.",
            "judgement": "NCLT found {corp_finding}. Board directed to {corp_remedy}. Statutory auditor appointed.",
            "laws": ["Companies Act 2013", "SEBI Act 1992", "Insolvency and Bankruptcy Code 2016"],
            "keywords": ["{corp_issue}", "corporate governance", "NCLT", "shareholders", "Companies Act"],
        },
    ],
    "Cyber Law": [
        {
            "situation": "Victim reported {cyber_offence} via online platform. {cyber_mode} used to commit the act.",
            "summary": "Cybercrime case involving {cyber_offence}. Complaint registered with Cyber Crime Cell. IP traced to {location}.",
            "judgement": "Accused convicted under IT Act Section {it_sec}. Fine of Rs. {fine} imposed. Data restored.",
            "laws": ["Information Technology Act 2000", "IT Amendment Act 2008", "IPC Section 420"],
            "keywords": ["{cyber_offence}", "cybercrime", "IT Act", "digital evidence", "online fraud"],
        },
    ],
    "Family Law": [
        {
            "situation": "{family_issue} dispute between {parties}. Marriage {marriage_type}. {children_info}.",
            "summary": "Family law matter involving {family_issue}. Filed under {family_act}. Mediation attempted.",
            "judgement": "Court granted {family_remedy}. Maintenance fixed at Rs. {maintenance}/month. {custody_order}.",
            "laws": ["{family_act}", "Guardians and Wards Act 1890", "Hindu Succession Act 1956"],
            "keywords": ["{family_issue}", "maintenance", "custody", "divorce", "matrimonial"],
        },
    ],
    "Tax Law": [
        {
            "situation": "Income tax dispute over {tax_issue}. Assessment year {ay}. Demand of Rs. {demand} crore raised.",
            "summary": "Tax assessment dispute. Department alleged {tax_allegation}. Assessee claimed {tax_defence}.",
            "judgement": "ITAT ruled {tax_ruling}. Penalty of Rs. {penalty} lakhs {penalty_status}. Appeal {appeal_status}.",
            "laws": ["Income Tax Act 1961", "Finance Act {year}", "CGST Act 2017"],
            "keywords": ["{tax_issue}", "income tax", "assessment", "ITAT", "tax evasion", "penalty"],
        },
    ],
}

FILL = {
    "article": ["14", "19", "21", "21A", "32", "226", "300A", "16", "15", "25"],
    "right": ["right to equality", "right to life", "freedom of speech", "right to education",
              "right to property", "right to religion", "right against discrimination"],
    "action": ["state notification", "municipal demolition order", "transfer order", "detention",
               "school closure", "hospital policy", "land acquisition"],
    "remedy": ["due process", "compensation", "reinstatement", "restoration of rights"],
    "offence": ["murder", "culpable homicide", "robbery", "cheating", "assault",
                "kidnapping", "rape", "corruption", "forgery", "extortion", "drug trafficking"],
    "ipc_sec": ["302", "304", "392", "420", "307", "363", "376", "406", "120B", "498A"],
    "state": ["Delhi", "Mumbai", "Chennai", "Kolkata", "Bangalore", "Hyderabad", "Pune"],
    "evidence_count": ["3", "5", "7", "9", "12", "15"],
    "defence_arg": ["mistaken identity", "alibi", "self-defence", "lack of intent", "insufficient evidence"],
    "finding": ["accused guilty beyond reasonable doubt", "prosecution failed to prove guilt",
                "partial guilt established", "accused acquitted"],
    "evidence_quality": ["strong and corroborated", "circumstantial but sufficient",
                         "weak and uncorroborated", "documentary and cogent"],
    "sentence": ["5 years rigorous imprisonment", "3 years imprisonment with fine",
                 "life imprisonment", "acquittal", "2 years with probation"],
    "property_type": ["residential", "agricultural", "commercial", "ancestral", "leasehold"],
    "claim": ["ownership by inheritance", "adverse possession", "purchase agreement",
              "gift deed", "partition of joint family property"],
    "counter": ["forged documents", "earlier settlement deed", "prior possession", "government acquisition"],
    "act": ["Transfer of Property Act 1882", "Hindu Succession Act 1956",
            "Land Acquisition Act 2013", "Rent Control Act"],
    "winner": ["plaintiff", "defendant", "neither party partially"],
    "days": ["30", "60", "90", "120"],
    "corp_issue": ["oppression and mismanagement", "fraudulent transfer of assets",
                   "non-payment of dividends", "illegal board resolution",
                   "financial irregularities", "corporate insolvency"],
    "petitioner_count": ["2", "5", "10", "3", "7"],
    "corp_finding": ["oppression proved", "mismanagement established", "fraud detected",
                     "accounts misrepresented"],
    "corp_remedy": ["reconstitute board", "repay diverted funds", "hold fresh AGM", "appoint independent director"],
    "cyber_offence": ["online financial fraud", "identity theft", "cyberstalking",
                      "data breach", "phishing", "morphed image defamation", "hacking"],
    "cyber_mode": ["fake website", "social media", "email phishing", "mobile app",
                   "WhatsApp", "dark web platform"],
    "location": ["the accused's residence", "an internet cafe", "a foreign server", "VPN traced back"],
    "it_sec": ["66", "66C", "67", "43A", "72", "66D"],
    "fine": ["50,000", "1,00,000", "2,00,000", "5,00,000"],
    "family_issue": ["divorce", "maintenance", "child custody", "domestic violence", "dowry recovery",
                     "restitution of conjugal rights"],
    "parties": ["husband and wife", "estranged spouses", "separated partners"],
    "marriage_type": ["Hindu", "Muslim Nikah", "Christian church", "civil/court", "live-in"],
    "children_info": ["Two minor children involved", "No children", "One child aged 5",
                      "Twins aged 7 years"],
    "family_act": ["Hindu Marriage Act 1955", "Special Marriage Act 1954",
                   "Protection of Women from Domestic Violence Act 2005",
                   "Muslim Personal Law (Shariat) Application Act 1937"],
    "family_remedy": ["divorce decree", "judicial separation", "maintenance", "protection order",
                      "custody to mother", "visitation rights"],
    "maintenance": ["5,000", "10,000", "15,000", "25,000", "8,000"],
    "custody_order": ["Custody awarded to mother", "Shared custody ordered",
                      "Custody to father with visitation rights", "Child's welfare paramount"],
    "tax_issue": ["unexplained cash deposits", "bogus capital gains", "transfer pricing",
                  "LTCG exemption claim", "undisclosed foreign assets", "shell company transactions"],
    "ay": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23"],
    "demand": ["5", "12", "3.5", "8", "20", "1.2"],
    "tax_allegation": ["undisclosed income", "inflated deductions", "bogus expenses",
                       "tax evasion through shell companies"],
    "tax_defence": ["valid business expenses", "exempt agricultural income", "legitimate investments",
                    "losses carried forward"],
    "tax_ruling": ["in favour of assessee", "in favour of department", "partly for assessee"],
    "penalty": ["10", "25", "50", "5", "100"],
    "penalty_status": ["confirmed", "deleted", "reduced by 50%", "waived"],
    "appeal_status": ["allowed", "dismissed", "remanded for fresh assessment"],
    "year": ["2019", "2020", "2021", "2022", "2023"],
}

AMENDMENTS = {
    "Constitutional Law": ["42nd Constitutional Amendment 1976", "44th Amendment 1978",
                           "86th Amendment 2002", "Right to Education Act 2009"],
    "Criminal Law": ["Criminal Law Amendment Act 2013", "BNS 2023", "BNSS 2023",
                     "POCSO Act 2012", "Narcotic Drugs and Psychotropic Substances Act 1985"],
    "Property Law": ["Land Acquisition Amendment 2013", "Benami Transactions Act 1988",
                     "Real Estate Regulation Act 2016"],
    "Corporate Law": ["Companies Amendment Act 2017", "IBC Amendment 2020",
                      "SEBI (LODR) Regulations 2015"],
    "Cyber Law": ["IT Amendment Act 2008", "Data Protection Bill 2023",
                  "Cyber Security Policy 2013"],
    "Family Law": ["Hindu Marriage Amendment 1976", "Domestic Violence Amendment 2005",
                   "Muslim Women Protection Act 2019"],
    "Tax Law": ["Finance Act 2021", "Finance Act 2022", "CGST Amendment 2023",
                "Black Money Act 2015"],
}

def pick(key):
    return random.choice(FILL[key])

def make_case(idx, area, tpl):
    fmt = {}
    for k in FILL:
        fmt[k] = pick(k)

    situation = tpl["situation"].format(**fmt)
    summary = tpl["summary"].format(**fmt)
    judgement = tpl["judgement"].format(**fmt)
    laws = [l.format(**fmt) for l in tpl["laws"]]
    keywords = [k.format(**fmt) for k in tpl["keywords"]]

    court = random.choice(list(COURTS.keys()))
    year_filed = random.randint(2010, 2022)
    duration = random.randint(1, 8)
    outcome = random.choice(OUTCOMES)
    amendments = random.sample(AMENDMENTS[area], k=min(2, len(AMENDMENTS[area])))

    prefixes = {
        "Constitutional Law": "CL", "Criminal Law": "CR",
        "Property Law": "PL", "Corporate Law": "CO",
        "Cyber Law": "CY", "Family Law": "FL", "Tax Law": "TX",
    }
    prefix = prefixes.get(area, "GN")
    case_id = f"{prefix}_{year_filed}_{idx:04d}"

    # Generate realistic names
    first_names = ["Sharma", "Kumar", "Singh", "Gupta", "Verma", "Patel",
                   "Iyer", "Reddy", "Nair", "Joshi", "Mehta", "Bose", "Das"]
    second_names = ["State of Maharashtra", "Union of India", "Municipal Corporation",
                    "Income Tax Department", "SEBI", "State Bank of India",
                    "National Highway Authority", "BPCL", "Reliance Industries"]
    name1 = f"{random.choice(first_names)} {random.choice(['Rajesh','Priya','Amol','Sanjay','Kavita','Rahul','Deepika','Vijay'])}"
    name2 = random.choice(second_names)
    case_name = f"{name1} vs {name2}"

    return {
        "case_id": case_id,
        "case_name": case_name,
        "legal_area": area,
        "court": court,
        "year": year_filed + duration,
        "case_summary": summary,
        "situation": situation,
        "case_laws": laws,
        "amendment_number": amendments,
        "duration": {
            "case_filed": str(year_filed),
            "judgement_date": str(year_filed + duration),
            "duration_years": duration,
        },
        "case_result": outcome,
        "judgement_summary": judgement,
        "keywords": keywords,
    }


def generate():
    areas = list(TEMPLATES.keys())
    cases = []
    idx = 1
    per_area = 80  # 7 areas * 80 = 560 cases

    for area in areas:
        tpl = TEMPLATES[area][0]
        for _ in range(per_area):
            cases.append(make_case(idx, area, tpl))
            idx += 1

    random.shuffle(cases)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(cases)} cases -> {OUTPUT}")
    return len(cases)


if __name__ == "__main__":
    count = generate()
    print(f"Done. Total cases: {count}")
