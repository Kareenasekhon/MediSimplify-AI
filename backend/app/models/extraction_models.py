from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class PatientInformation(BaseModel):
    name: Optional[str] = Field(default=None, description="Name of the patient")
    age: Optional[str] = Field(default=None, description="Age of the patient (e.g., '45', '45 years')")
    gender: Optional[str] = Field(default=None, description="Gender/Sex of the patient (e.g., 'Male', 'Female')")
    date: Optional[str] = Field(default=None, description="Date of the medical report or test")

class BloodTestItem(BaseModel):
    label: str = Field(description="Name/label of the test (e.g., 'Haemoglobin')")
    value: str = Field(description="Extracted value of the test (e.g., '10.2', '140')")
    unit: str = Field(description="Extracted unit of the test (e.g., 'g/dL', 'mg/dL')")
    reference_range: Optional[str] = Field(default=None, description="Normal reference range printed in the report (e.g., '12-15')")
    status_printed: Optional[str] = Field(default=None, description="Abnormal status indication printed in the report (e.g., 'High', 'Low', 'Abnormal', '*', 'H', 'L')")
    source_page: Optional[int] = Field(default=1, description="Page number where the test was found")

class BloodReportSection(BaseModel):
    section_name: str = Field(description="Name of the section (e.g., 'Complete Blood Count', 'Kidney Function Test')")
    items: List[BloodTestItem] = Field(default_factory=list, description="List of blood test results in this section")

class MedicineItem(BaseModel):
    name: str = Field(description="Name of the medicine/drug")
    dosage: Optional[str] = Field(default=None, description="Dosage instruction (e.g., '500 mg', '1 tablet')")
    frequency: Optional[str] = Field(default=None, description="Frequency (e.g., 'twice daily', 'BD', 'once a day')")
    timing: Optional[str] = Field(default=None, description="Timing relative to meals (e.g., 'after food', 'before food', 'empty stomach')")
    duration: Optional[str] = Field(default=None, description="Duration of treatment (e.g., '5 days', '1 month')")
    source_page: Optional[int] = Field(default=1, description="Page number where the medicine was found")

class RadiologyFinding(BaseModel):
    scan_type: str = Field(description="Type of radiology scan (e.g., 'MRI', 'X-ray', 'Ultrasound')")
    body_part: str = Field(description="Body part scanned (e.g., 'Lumbar Spine', 'Chest')")
    finding: str = Field(description="Detailed findings text")
    impression: Optional[str] = Field(default=None, description="Radiologist's overall impression or conclusion")
    source_page: Optional[int] = Field(default=1, description="Page number where the finding was found")

class ExtractionResult(BaseModel):
    document_type_hint: str = Field(
        description="Category classification hint: 'blood_report', 'prescription', 'radiology_report', or 'unknown'"
    )
    extracted_text: str = Field(default="", description="The full raw text extracted/transcribed from the document/image")
    patient_information: PatientInformation = Field(default_factory=PatientInformation)
    sections: List[BloodReportSection] = Field(default_factory=list, description="List of blood test sections (for blood reports)")
    medicine_items: List[MedicineItem] = Field(default_factory=list, description="List of medicine items (for prescriptions)")
    radiology_findings: List[RadiologyFinding] = Field(default_factory=list, description="List of radiology findings (for radiology reports)")
    unreadable_text: List[str] = Field(default_factory=list, description="List of phrases or regions marked as unreadable")
    warnings: List[str] = Field(default_factory=list, description="List of minor warnings encountered during extraction")

class ReportExtractionResponse(BaseModel):
    report_id: str = Field(description="Unique UUID string identifying the uploaded report session")
    input_type: str = Field(description="The ingestion medium: 'document' or 'image'")
    extracted_text: str = Field(description="Full plain text content of the report")
    structured_data: ExtractionResult = Field(description="Structured extraction representation")
    quality_warnings: List[str] = Field(default_factory=list, description="Quality validation alerts (e.g., blurry, dark)")
    unreadable_text: List[str] = Field(default_factory=list, description="Unreadable sections flagged")
    requires_confirmation: bool = Field(default=True, description="Always true in Phase 2 for mandatory user review")

class ExtractionConfirmRequest(BaseModel):
    confirmed_text: str = Field(description="User-edited and confirmed plain text")
    corrected_structured_data: Dict[str, Any] = Field(description="User-corrected structured data matching ExtractionResult layout")
    language: str = Field(default="en", description="Target explanation language preference ('en', 'hi', 'pa')")
    provider: str = Field(default="gemini", description="AI provider selected ('gemini', 'groq', 'ollama')")
