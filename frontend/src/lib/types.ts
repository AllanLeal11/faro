export type RiskLevel = "low" | "medium" | "high";
export type Lang = "es" | "en";

export interface EvidenceItem {
  id: string;
  kind: string;
  type: string;
  result: string;
  detail: string;
  source_url: string | null;
  severe: boolean;
}

export interface Reason {
  text: string;
  evidence_ids: string[];
}

export interface AnalysisResult {
  risk_level: RiskLevel;
  confidence: number;
  reasons: Reason[];
  explanation: string;
  recommended_action: string;
  verification_question: string;
  evidence: EvidenceItem[];
  partial: boolean;
}

export type TrustedKind = "bank" | "company" | "contact";

export interface TrustedEntity {
  id: string;
  kind: TrustedKind;
  name: string;
  domains: string[];
  phones: string[];
  emails: string[];
}

export interface FamilyContact {
  id: string;
  name: string;
  email: string;
  relationship_label: string;
}

export interface User {
  id: string;
  email: string;
  language: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}
