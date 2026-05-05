// 공통 타입 (Phase별로 추가)

export type UserRole = "staff" | "admin";

export type BidStatus = "new" | "collecting" | "collected" | "converting" | "analyzing" | "analyzed" | "completed" | "no_file" | "failed" | "analysis_failed";

export type TargetStatus = "검토필요" | "검토중" | "진행중" | "완료";

export type RiskLevel = "safe" | "caution" | "warning" | "danger";
