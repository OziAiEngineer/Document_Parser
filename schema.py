"""Pydantic v2 models for legal document extraction schema."""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CaseInstructingParty(BaseModel):
    agency_ref: Optional[str] = None
    agency_name: Optional[str] = None
    instructor_reference: Optional[str] = None
    instructing_party: Optional[str] = None


class ClaimantDetails(BaseModel):
    title: Optional[str] = None
    forenames: Optional[str] = None
    surname: Optional[str] = None
    postcode: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    medco_reference_no: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    telephone_home: Optional[str] = None
    telephone_work: Optional[str] = None
    mobile: Optional[str] = None
    cnf_claim_submission_date: Optional[str] = None
    occupation: Optional[str] = None


class TrackingAndAdministration(BaseModel):
    urn: Optional[str] = None
    status: Optional[str] = None
    accident_date: Optional[str] = None
    expert_name: Optional[str] = None
    source: Optional[str] = None


class MedicalRecords(BaseModel):
    records_required: Optional[bool] = None
    records_arrived: Optional[bool] = None
    arrived_date: Optional[str] = None


class General(BaseModel):
    consulting_venue: Optional[bool] = None
    consulting_venue_location: Optional[str] = None
    medical_date: Optional[str] = None
    appointment_time: Optional[str] = None
    appointment_timeline_weeks: Optional[str] = None
    appointment_post_accident_date: Optional[str] = None
    appointment_type: Optional[str] = None
    scottish_instruction: Optional[bool] = None
    interpreter_required: Optional[bool] = None
    interpreter_name: Optional[str] = None
    interpreter_company: Optional[str] = None
    interpreter_telephone: Optional[str] = None
    claims_handler_name: Optional[str] = None
    claims_handler_telephone: Optional[str] = None
    case_handler_email: Optional[str] = None


class Accident(BaseModel):
    accident_time: Optional[str] = None
    type_of_accident: Optional[str] = None
    accident_location: Optional[str] = None
    accident_description: Optional[str] = None
    location_details: Optional[str] = None
    involvement: Optional[str] = None
    wearing_seatbelt: Optional[bool] = None
    claimant_vehicle_reg: Optional[str] = None


class ResponsibleParties(BaseModel):
    responsible_party_vehicle_reg: Optional[str] = None
    driver_first_name: Optional[str] = None
    driver_last_name: Optional[str] = None
    driver_phone: Optional[str] = None
    claimant_statement_of_responsibility: Optional[str] = None


class SpecialInstructions(BaseModel):
    injuries_symptoms: Optional[str] = None
    other_special_instructions: Optional[str] = None

    @field_validator('injuries_symptoms', mode='before')
    @classmethod
    def serialize_symptoms_list(cls, v):
        if isinstance(v, list):
            return ", ".join(str(i) for i in v)
        return v

    @field_validator('other_special_instructions', mode='before')
    @classmethod
    def serialize_instructions_list(cls, v):
        if isinstance(v, list):
            return "\n".join(str(i) for i in v)
        return v


class LegalDocumentExtraction(BaseModel):
    case_instructing_party: Optional[CaseInstructingParty] = Field(default_factory=CaseInstructingParty)
    claimant_details: Optional[ClaimantDetails] = Field(default_factory=ClaimantDetails)
    tracking_and_administration: Optional[TrackingAndAdministration] = Field(default_factory=TrackingAndAdministration)
    medical_records: Optional[MedicalRecords] = Field(default_factory=MedicalRecords)
    general: Optional[General] = Field(default_factory=General)
    accident: Optional[Accident] = Field(default_factory=Accident)
    responsible_parties: Optional[ResponsibleParties] = Field(default_factory=ResponsibleParties)
    special_instructions: Optional[SpecialInstructions] = Field(default_factory=SpecialInstructions)
    requires_human_review: bool = False
    missing_mandatory_fields: list[str] = Field(default_factory=list)
