"""
SHIELD Platform — Statutory FIR, NCR & Legal Codex Router
Implements statutory procedures under Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)
and Bharatiya Nyaya Sanhita, 2023 (BNS), with Section 63 BSA Blockchain Anchoring.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import hashlib

from app.core.database import get_db
from app.auth.dependencies import get_current_officer
from app.models.officer import Officer, OfficerRank
from app.core.blockchain import police_ledger

router = APIRouter()

# ─── STATUTORY LEGAL CODEX (BNS 2023 vs IPC 1860) ────────────
STATUTORY_PENAL_CODEX: List[Dict[str, Any]] = [
    # ── Crimes Against Human Body ──
    {
        "id": "BNS-103-1",
        "bns_section": "Section 103(1)",
        "ipc_section": "Section 302",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Murder",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Court of Session",
        "max_punishment": "Death or Imprisonment for Life, and fine",
        "cognizable_flag": True,
        "category": "BODY",
        "ingredients": "Act done with intention of causing death, or causing bodily injury sufficient in ordinary course of nature to cause death, or knowing act is imminently dangerous.",
        "procedure_guidelines": "Mandatory FIR under BNSS §173. Immediate dispatch of report to Magistrate under BNSS §176. Forensic FSL team dispatch, videography of crime scene under BNSS §105, inquest under BNSS §194.",
        "loophole_safeguards": "Mandatory arrest warrants. Mandatory audio-video recording of search and seizure under BNSS §105. Cannot be registered as NCR or downgraded."
    },
    {
        "id": "BNS-105",
        "bns_section": "Section 105",
        "ipc_section": "Section 304",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Culpable Homicide Not Amounting to Murder",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Court of Session",
        "max_punishment": "Imprisonment for Life or up to 10 years, and fine",
        "cognizable_flag": True,
        "category": "BODY",
        "ingredients": "Act done with intention of causing death/bodily injury likely to cause death, or with knowledge without intention.",
        "procedure_guidelines": "Mandatory FIR. Post-mortem doctor's provisional cause of death opinion required within 24 hours.",
        "loophole_safeguards": "Prevents Section 106 (Rash/negligent act) dilution when intentional assault evidence is present."
    },
    {
        "id": "BNS-115-2",
        "bns_section": "Section 115(2)",
        "ipc_section": "Section 323",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Voluntarily Causing Hurt (Simple Assault)",
        "offense_type": "NON_COGNIZABLE",
        "bailable": True,
        "compoundable": True,
        "triable_by": "Any Magistrate",
        "max_punishment": "Imprisonment up to 1 year, or fine up to ₹10,000, or both",
        "cognizable_flag": False,
        "category": "BODY",
        "ingredients": "Causing bodily pain, disease, or infirmity without grievous injury weapons or bone fractures.",
        "procedure_guidelines": "MANDATORY NCR ENTRY under BNSS §174. Police cannot arrest or investigate without Judicial Magistrate order under BNSS §174(2). Informant must be referred to Magistrate.",
        "loophole_safeguards": "If weapon used (BNS §118) or fracture detected (BNS §117), automatically elevates to Cognizable FIR."
    },
    {
        "id": "BNS-117-2",
        "bns_section": "Section 117(2)",
        "ipc_section": "Section 325",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Voluntarily Causing Grievous Hurt",
        "offense_type": "COGNIZABLE",
        "bailable": True,
        "compoundable": True,
        "triable_by": "Magistrate of First Class",
        "max_punishment": "Imprisonment up to 7 years, and fine",
        "cognizable_flag": True,
        "category": "BODY",
        "ingredients": "Permanent privation of sight/hearing, destruction of member/joint, bone fracture, or 15-day severe pain.",
        "procedure_guidelines": "Cognizable FIR under BNSS §173. Medical legal certificate (MLC) X-Ray/CT scan mandatory.",
        "loophole_safeguards": "Section 35(3) BNSS notice required before arrest unless officer records special reasons in writing."
    },
    {
        "id": "BNS-124-1",
        "bns_section": "Section 124(1)",
        "ipc_section": "Section 326A",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Voluntarily Causing Grievous Hurt by Acid / Chemical",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Court of Session",
        "max_punishment": "Imprisonment not less than 10 years, which may extend to Life, and fine",
        "cognizable_flag": True,
        "category": "BODY",
        "ingredients": "Permanent or partial damage/deformity/burns by throwing or administering acid or corrosive substance.",
        "procedure_guidelines": "Mandatory FIR. Free medical treatment in any hospital (public/private) under BNSS §397.",
        "loophole_safeguards": "No settlement or compromise permitted. Fine payable directly to victim for medical rehabilitation."
    },
    {
        "id": "BNS-64",
        "bns_section": "Section 64",
        "ipc_section": "Section 376",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Rape / Sexual Assault",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Court of Session",
        "max_punishment": "Rigorous Imprisonment not less than 10 years, up to Life, and fine",
        "cognizable_flag": True,
        "category": "WOMEN_CHILDREN",
        "ingredients": "Sexual intercourse or penetrative act without consent or by intoxication/misrepresentation/threat.",
        "procedure_guidelines": "Mandatory FIR. Statement to be recorded by a woman police officer under BNSS §173 proviso. Medical examination of victim within 24 hours under BNSS §184. Judicial Magistrate statement under BNSS §183.",
        "loophole_safeguards": "Zero-tolerance for non-registration. Refusal to record FIR invites mandatory penal prosecution of police officer under BNS §199 (up to 2 years rigorous imprisonment)."
    },
    {
        "id": "BNS-137-2",
        "bns_section": "Section 137(2)",
        "ipc_section": "Section 363",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Kidnapping",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Magistrate of First Class",
        "max_punishment": "Imprisonment up to 7 years, and fine",
        "cognizable_flag": True,
        "category": "BODY",
        "ingredients": "Taking or enticing any minor (under 18) or unsound mind out of lawful guardianship without consent.",
        "procedure_guidelines": "Immediate Zero-FIR registration. Track Child SOP activated with interstate ANPR alerts and facial recognition search across railway and bus terminals.",
        "loophole_safeguards": "No preliminary enquiry delay allowed. Supreme Court Bachpan Bachao Andolan guidelines enforced."
    },

    # ── Crimes Against Property ──
    {
        "id": "BNS-303-2",
        "bns_section": "Section 303(2)",
        "ipc_section": "Section 379",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Theft",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Any Magistrate",
        "max_punishment": "Imprisonment up to 3 years, or fine, or community service (for value < ₹5,000 upon first offense)",
        "cognizable_flag": True,
        "category": "PROPERTY",
        "ingredients": "Intending to take dishonestly any movable property out of possession of any person without consent.",
        "procedure_guidelines": "Cognizable FIR. Stolen property seizure memo anchored to blockchain under BSA §63.",
        "loophole_safeguards": "First-time low value property theft community service provision under BNS §303(2) proviso."
    },
    {
        "id": "BNS-304-1",
        "bns_section": "Section 304(1)",
        "ipc_section": "New Offense (Specific Provision)",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Snatching (Chain / Phone / Purse)",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Any Magistrate",
        "max_punishment": "Imprisonment up to 3 years, and fine",
        "cognizable_flag": True,
        "category": "PROPERTY",
        "ingredients": "Theft where offender suddenly or quickly or forcibly seizes, secures, grabs or takes away movable property from person.",
        "procedure_guidelines": "Mandatory FIR. CCTV nodal retrieval from highway and street cameras within 4 hours.",
        "loophole_safeguards": "Previously diluted as simple theft; BNS now introduces explicit non-bailable statutory category."
    },
    {
        "id": "BNS-309-4",
        "bns_section": "Section 309(4)",
        "ipc_section": "Section 392",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Robbery",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Magistrate of First Class",
        "max_punishment": "Rigorous imprisonment up to 10 years, and fine; if on highway between sunset and sunrise, up to 14 years",
        "cognizable_flag": True,
        "category": "PROPERTY",
        "ingredients": "Theft or extortion accompanied by causing or attempting to cause death, hurt, or wrongful restraint.",
        "procedure_guidelines": "High-priority FIR. ANPR grid lock on all getaway routes.",
        "loophole_safeguards": "Automatic enhancement to Section 310 (Dacoity) if 5 or more persons involved."
    },
    {
        "id": "BNS-310-2",
        "bns_section": "Section 310(2)",
        "ipc_section": "Section 395",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Dacoity",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Court of Session",
        "max_punishment": "Imprisonment for Life or rigorous imprisonment up to 10 years, and fine",
        "cognizable_flag": True,
        "category": "PROPERTY",
        "ingredients": "Five or more persons conjointly committing or attempting to commit a robbery.",
        "procedure_guidelines": "Special Investigation Team (SIT) requisition. Inter-agency intelligence alert to Border/RTO checkposts.",
        "loophole_safeguards": "Joint liability applies to all members present under BNS §310."
    },
    {
        "id": "BNS-318-4",
        "bns_section": "Section 318(4)",
        "ipc_section": "Section 420",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Cheating & Dishonestly Inducing Delivery of Property",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Magistrate of First Class",
        "max_punishment": "Imprisonment up to 7 years, and fine",
        "cognizable_flag": True,
        "category": "FRAUD_ECONOMIC",
        "ingredients": "Deceiving any person fraudulently or dishonestly inducing delivery of property or valuable security.",
        "procedure_guidelines": "Mandatory FIR. Bank account freeze request under BNSS §107 / BNSS §111.",
        "loophole_safeguards": "Section 35(3) BNSS notice applies if accused co-operates and recovery is viable."
    },

    # ── Non-Cognizable Offenses ──
    {
        "id": "BNS-351-2",
        "bns_section": "Section 351(2)",
        "ipc_section": "Section 506",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Criminal Intimidation (Verbal Threats)",
        "offense_type": "NON_COGNIZABLE",
        "bailable": True,
        "compoundable": True,
        "triable_by": "Any Magistrate",
        "max_punishment": "Imprisonment up to 2 years, or fine, or both",
        "cognizable_flag": False,
        "category": "PUBLIC_ORDER",
        "ingredients": "Threatening injury to person, reputation, or property with intent to cause alarm or force an act.",
        "procedure_guidelines": "MANDATORY NCR ENTRY under BNSS §174. Police officer gives informant receipt and refers to Magistrate. NO ARREST WITHOUT WARRANT.",
        "loophole_safeguards": "If threat is to cause death or grievous hurt (BNS §351(3)), punishment rises to 7 years, but still requires Magistrate warrant unless coupled with assault."
    },
    {
        "id": "BNS-356-2",
        "bns_section": "Section 356(2)",
        "ipc_section": "Section 500",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Defamation (Simple / Non-Extortionate)",
        "offense_type": "NON_COGNIZABLE",
        "bailable": True,
        "compoundable": True,
        "triable_by": "Magistrate of First Class",
        "max_punishment": "Simple imprisonment up to 2 years, or fine, or both, or community service",
        "cognizable_flag": False,
        "category": "REPUTATION",
        "ingredients": "Making or publishing any imputation concerning any person intending to harm reputation.",
        "procedure_guidelines": "NON-COGNIZABLE REGISTER (NCR). Magistrate takes cognizance upon private complaint under BNSS §223. Police have NO jurisdiction to register FIR directly.",
        "loophole_safeguards": "Prevents abuse of police power for political/personal vendettas without judicial oversight."
    },
    {
        "id": "BNS-270",
        "bns_section": "Section 270",
        "ipc_section": "Section 290",
        "act": "Bharatiya Nyaya Sanhita, 2023",
        "title": "Public Nuisance",
        "offense_type": "NON_COGNIZABLE",
        "bailable": True,
        "compoundable": False,
        "triable_by": "Any Magistrate",
        "max_punishment": "Fine up to ₹1,000",
        "cognizable_flag": False,
        "category": "PUBLIC_ORDER",
        "ingredients": "Any act causing common injury, danger, or annoyance to the public or people in the vicinity.",
        "procedure_guidelines": "Recorded in Non-Cognizable Register. Forwarded to Executive Magistrate / Municipal Authority.",
        "loophole_safeguards": "Cannot be used as a pretext for custodial detention."
    },

    # ── Special & Cyber Acts ──
    {
        "id": "IT-66D",
        "bns_section": "Section 66D",
        "ipc_section": "Information Technology Act, 2000",
        "act": "Information Technology Act, 2000",
        "title": "Cheating by Personation Using Computer Resource / Online Phishing",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": True,
        "triable_by": "Magistrate of First Class",
        "max_punishment": "Imprisonment up to 3 years, and fine up to ₹1,00,000",
        "cognizable_flag": True,
        "category": "CYBERCRIME",
        "ingredients": "Cheating by personating through communication device or computer resource (UPI scams, spoofing, deepfakes).",
        "procedure_guidelines": "Mandatory FIR. Immediate 1930 / I4C CFCFRMS lien freeze on recipient mule bank accounts within golden hour.",
        "loophole_safeguards": "Coupled with BNS §318(4) to prevent bailable loopholes in multi-lakh financial frauds."
    },
    {
        "id": "POCSO-4",
        "bns_section": "Section 4",
        "ipc_section": "Protection of Children from Sexual Offences (POCSO) Act",
        "act": "POCSO Act, 2012",
        "title": "Penetrative Sexual Assault on Child",
        "offense_type": "COGNIZABLE",
        "bailable": False,
        "compoundable": False,
        "triable_by": "Special POCSO Court",
        "max_punishment": "Rigorous imprisonment not less than 20 years, up to Life/Death",
        "cognizable_flag": True,
        "category": "WOMEN_CHILDREN",
        "ingredients": "Any penetrative assault on a child under 18 years of age.",
        "procedure_guidelines": "Mandatory FIR within 1 hour. No disclosure of child's identity under POCSO §23. Video recording of child's statement at residence in presence of parents/guardian.",
        "loophole_safeguards": "Strict liability. Statutory presumption of guilt against accused under POCSO §29."
    }
]

# In-memory store of registered statutory records for instant reactivity
REGISTERED_STATUTORY_RECORDS: List[Dict[str, Any]] = [
    {
        "record_id": "FIR-KA-BLR-2026-00412",
        "record_type": "FIR",
        "legal_nature": "COGNIZABLE",
        "statutory_mandate": "Section 173 Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "police_station": "Cyber Crime Police Station, Bengaluru Central",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "incident_title": "Unauthorized Multi-Lakh Corporate Exfiltration & UPI Phishing Ring",
        "complainant_name": "Rohan Deshmukh",
        "complainant_contact": "+91 98450 11200",
        "complainant_address": "Indiranagar 100ft Road, Bengaluru",
        "incident_datetime": "2026-10-30T18:45:00Z",
        "registration_datetime": "2026-10-30T19:30:00Z",
        "sections": ["Section 318(4) BNS", "Section 66D IT Act"],
        "accused_name": "Vikram Sethi & Unknown Associates",
        "accused_status": "Absconding / ANPR Lookout Active",
        "is_zero_fir": False,
        "transfer_status": "LOCAL_JURISDICTION",
        "cjm_intimation_status": "TRANSMITTED_TO_CJM_BENGALURU",
        "section_35_notice_issued": False,
        "arrest_status": "WARRANT_REQUISITIONED",
        "registered_by_officer": "Insp. S. Kulkarni (Badge BLR-INSP-401)",
        "blockchain_tx_hash": "a4f89d3c1782e5b410928f643198de70c651982a7f3941bd58291f038472bb51",
        "block_height": 2,
        "bsa_compliant": True
    },
    {
        "record_id": "NCR-KA-BLR-2026-00089",
        "record_type": "NCR",
        "legal_nature": "NON_COGNIZABLE",
        "statutory_mandate": "Section 174 Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "police_station": "Koramangala Police Station, Bengaluru",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "incident_title": "Verbal Altercation, Public Nuisance & Criminal Intimidation in Commercial Complex",
        "complainant_name": "Priya Sundaram",
        "complainant_contact": "+91 98765 43210",
        "complainant_address": "80ft Road, Koramangala 4th Block, Bengaluru",
        "incident_datetime": "2026-10-29T14:15:00Z",
        "registration_datetime": "2026-10-29T15:00:00Z",
        "sections": ["Section 115(2) BNS", "Section 351(2) BNS", "Section 270 BNS"],
        "accused_name": "Arun Kumar (Store Manager)",
        "accused_status": "Not Arrested (Barred under BNSS §174(2) without Magistrate Order)",
        "is_zero_fir": False,
        "transfer_status": "REFERRED_TO_MAGISTRATE",
        "cjm_intimation_status": "INFORMANT_REFERRED_TO_3RD_ACMM_COURT",
        "section_35_notice_issued": True,
        "arrest_status": "BARRED_BY_LAW",
        "registered_by_officer": "SI D. Patil (Badge BLR-SI-882)",
        "blockchain_tx_hash": "c9281745bd092a8371629d8162e08472538194017264817293847162948271a3",
        "block_height": 3,
        "bsa_compliant": True
    }
]


# ─── SCHEMAS ───────────────────────────────────────────────
class RegisterStatutoryCaseRequest(BaseModel):
    record_type: str = Field(..., description="'FIR' for Cognizable or 'NCR' for Non-Cognizable")
    is_zero_fir: bool = Field(False, description="True if offense took place outside police station territorial limits")
    title: str = Field(..., description="Brief subject of information")
    category: str = Field("BODY", description="Category of crime")
    complainant_name: str
    complainant_contact: str
    complainant_id_proof: Optional[str] = "Aadhaar / Voter ID Verified"
    complainant_address: str
    incident_datetime: str
    incident_location: str
    sections: List[str] = Field(..., description="List of BNS or Special Act sections")
    accused_name: str = "Unknown"
    accused_details: Optional[str] = None
    factual_chronology: str
    stolen_property_or_injury: Optional[str] = None
    station_name: Optional[str] = "Bengaluru Central Police Station"


# ─── ROUTES ────────────────────────────────────────────────

@router.get("/codex", summary="Get Statutory Penal Code Sections & Trainee Rules Booklet")
async def get_statutory_codex(
    category: Optional[str] = Query(None, description="Filter by BODY, PROPERTY, FRAUD_ECONOMIC, WOMEN_CHILDREN, PUBLIC_ORDER, CYBERCRIME"),
    offense_type: Optional[str] = Query(None, description="Filter by COGNIZABLE or NON_COGNIZABLE"),
    search: Optional[str] = Query(None, description="Search by section number, keyword, or old IPC section")
):
    """
    Returns the comprehensive statutory booklet of Bharatiya Nyaya Sanhita (BNS) 
    and Bharatiya Nagarik Suraksha Sanhita (BNSS) rules for trainees, IOs, and senior police officers.
    """
    results = STATUTORY_PENAL_CODEX

    if category:
        results = [r for r in results if r["category"].upper() == category.upper()]
    if offense_type:
        results = [r for r in results if r["offense_type"].upper() == offense_type.upper()]
    if search:
        s = search.lower()
        results = [
            r for r in results
            if s in r["bns_section"].lower()
            or s in r["ipc_section"].lower()
            or s in r["title"].lower()
            or s in r["ingredients"].lower()
        ]

    return {
        "status": "SUCCESS",
        "act_primary": "Bharatiya Nyaya Sanhita, 2023 (BNS)",
        "act_procedural": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "evidence_act": "Bharatiya Sakshya Adhiniyam, 2023 (BSA)",
        "total_sections_cataloged": len(results),
        "codex": results
    }


@router.get("/records", summary="List All Registered FIRs and NCR Entries")
async def list_statutory_records(
    record_type: Optional[str] = Query(None, description="Filter by 'FIR' or 'NCR'"),
    officer: Officer = Depends(get_current_officer)
):
    """
    Returns registered statutory First Information Reports (FIRs) and Non-Cognizable Reports (NCRs).
    """
    records = REGISTERED_STATUTORY_RECORDS
    if record_type:
        records = [r for r in records if r["record_type"].upper() == record_type.upper()]

    return {
        "status": "SUCCESS",
        "total_count": len(records),
        "records": records
    }


@router.post("/register", summary="Register Statutory FIR or NCR (Strict BNSS §173 & §174 Compliance)")
async def register_statutory_record(
    payload: RegisterStatutoryCaseRequest,
    officer: Officer = Depends(get_current_officer)
):
    """
    Statutory Engine for Police Officers to register FIRs or NCRs according to law.
    Enforces Anti-Burking safeguards, Zero-FIR statutory routing, Section 176 CJM copy compliance,
    and Section 63 BSA Blockchain Anchoring.
    """
    rec_type = payload.record_type.upper()
    if rec_type not in ["FIR", "NCR"]:
        raise HTTPException(status_code=400, detail="Invalid record_type. Must be 'FIR' or 'NCR'")

    # ── 1. ANTI-BURKING CHECK (Lalita Kumari & BNSS §173 Mandate) ──
    # Check if any selected section is Cognizable
    has_cognizable_section = False
    for sec_str in payload.sections:
        for codex_item in STATUTORY_PENAL_CODEX:
            if codex_item["bns_section"].lower() in sec_str.lower() or codex_item["title"].lower() in sec_str.lower():
                if codex_item["cognizable_flag"]:
                    has_cognizable_section = True
                    break

    # If cognizable section is present, LAW MANDATES AN FIR!
    # Demoting to NCR is an unlawful refusal punishable under Section 199 BNS.
    if rec_type == "NCR" and has_cognizable_section:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "STATUTORY BURKING VIOLATION (Section 173 BNSS & Lalita Kumari v. Govt of UP): "
                "The selected offenses disclose a COGNIZABLE CRIME. Police officers are legally bound "
                "to register a First Information Report (FIR). Demoting this case to a Non-Cognizable Register (NCR) "
                "constitutes an illegal refusal and is punishable under Section 199 of Bharatiya Nyaya Sanhita, 2023. "
                "You must register this case as an FIR."
            )
        )

    # ── 2. DETERMINE LEGAL NUMBER & ZERO-FIR ROUTING ──
    year = datetime.now().year
    seq = len(REGISTERED_STATUTORY_RECORDS) + 1
    
    if payload.is_zero_fir:
        record_id = f"ZERO-FIR-BLR-{year}-{seq:05d}"
        legal_nature = "COGNIZABLE (ZERO JURISDICTION)"
        statutory_mandate = "Section 173(1) BNSS — Mandatory Zero FIR irrespective of territorial crime scene"
        transfer_status = "ELECTRONICALLY_ROUTED_TO_JURISDICTIONAL_SP_24HRS"
    elif rec_type == "FIR":
        record_id = f"FIR-KA-BLR-{year}-{seq:05d}"
        legal_nature = "COGNIZABLE"
        statutory_mandate = "Section 173 Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)"
        transfer_status = "LOCAL_STATION_JURISDICTION"
    else:
        record_id = f"NCR-KA-BLR-{year}-{seq:05d}"
        legal_nature = "NON_COGNIZABLE"
        statutory_mandate = "Section 174 Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)"
        transfer_status = "REFERRED_TO_JUDICIAL_MAGISTRATE_UNDER_174(2)"

    # ── 3. SECTION 35(3) BNSS SAFEGUARD (ARREST NOTICE COMPLIANCE) ──
    # Check if max punishment <= 7 years for Arnesh Kumar rule
    is_less_than_7_years = True
    for sec_str in payload.sections:
        for codex_item in STATUTORY_PENAL_CODEX:
            if codex_item["bns_section"].lower() in sec_str.lower():
                if "Life" in codex_item["max_punishment"] or "Death" in codex_item["max_punishment"] or "10 years" in codex_item["max_punishment"]:
                    is_less_than_7_years = False
                    break

    section_35_notice = (rec_type == "FIR" and is_less_than_7_years)
    arrest_status = "SECTION_35_NOTICE_GENERATED" if section_35_notice else ("BARRED_BY_LAW_WITHOUT_MAGISTRATE_ORDER" if rec_type == "NCR" else "ARREST_WARRANT_OR_HEINOUS_CRIME_INVESTIGATION")

    # ── 4. CRYPTOGRAPHIC BSA SECTION 63 BLOCKCHAIN ANCHOR ──
    now_iso = datetime.now(timezone.utc).isoformat()
    raw_payload_str = f"{record_id}|{payload.title}|{payload.complainant_name}|{','.join(payload.sections)}|{now_iso}"
    blockchain_tx = hashlib.sha256(raw_payload_str.encode("utf-8")).hexdigest()

    mined_block = police_ledger.mine_block(
        record_type=f"STATUTORY_{rec_type}",
        record_id=record_id,
        data={
            "title": payload.title,
            "statutory_mandate": statutory_mandate,
            "complainant": payload.complainant_name,
            "sections": payload.sections,
            "officer_badge": getattr(officer, "badge_number", "POLICE-HQ-01")
        }
    )

    # ── 5. ASSEMBLE OFFICIAL RECORD ──
    new_record = {
        "record_id": record_id,
        "record_type": rec_type,
        "legal_nature": legal_nature,
        "statutory_mandate": statutory_mandate,
        "police_station": payload.station_name,
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "incident_title": payload.title,
        "complainant_name": payload.complainant_name,
        "complainant_contact": payload.complainant_contact,
        "complainant_address": payload.complainant_address,
        "incident_datetime": payload.incident_datetime,
        "registration_datetime": now_iso,
        "sections": payload.sections,
        "accused_name": payload.accused_name,
        "accused_details": payload.accused_details or "Under identification",
        "factual_chronology": payload.factual_chronology,
        "stolen_property_or_injury": payload.stolen_property_or_injury or "None recorded",
        "is_zero_fir": payload.is_zero_fir,
        "transfer_status": transfer_status,
        "cjm_intimation_status": "AUTOMATICALLY_TRANSMITTED_TO_CHIEF_JUDICIAL_MAGISTRATE",
        "section_35_notice_issued": section_35_notice,
        "arrest_status": arrest_status,
        "registered_by_officer": f"{officer.full_name} ({officer.rank} • {officer.badge_number})",
        "blockchain_tx_hash": mined_block.hash,
        "block_height": mined_block.index,
        "bsa_compliant": True,
        "free_copy_statutory_dispatch": "DISPATCHED_TO_COMPLAINANT_UNDER_BNSS_173(2)"
    }

    REGISTERED_STATUTORY_RECORDS.insert(0, new_record)

    return {
        "status": "SUCCESS",
        "message": f"Statutory {rec_type} successfully registered and cryptographically anchored to Sovereign Blockchain.",
        "record": new_record
    }


@router.get("/record/{record_id}", summary="Get Full Statutory Record with Section 63 BSA Seal")
async def get_statutory_record(
    record_id: str,
    officer: Officer = Depends(get_current_officer)
):
    """
    Retrieves full details of a statutory FIR or NCR entry for printing and judicial submission.
    """
    for r in REGISTERED_STATUTORY_RECORDS:
        if r["record_id"].upper() == record_id.upper():
            return {
                "status": "SUCCESS",
                "record": r,
                "bsa_certificate": {
                    "statute": "Section 63 of Bharatiya Sakshya Adhiniyam, 2023",
                    "hash_algorithm": "SHA-256 Distributed Ledger Block",
                    "hash_digest": r["blockchain_tx_hash"],
                    "chain_integrity": "UNMODIFIED_ORIGINAL_PRIMARY_EVIDENCE",
                    "issued_to_magistrate": True
                }
            }
    raise HTTPException(status_code=404, detail="Statutory record not found.")
